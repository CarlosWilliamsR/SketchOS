"""Process-integration tests for ``validator_client``.

Slice 2 (PR 2) RED tests covering the subprocess boundary: argv is always a
list (never a shell string, ``shell`` never enabled), the binary resolves from
``VALIDATOR_GO_BIN`` with a PATH fallback, exit codes 0/1/2 map to
pass/violations/parse-error, temp files are removed in ``finally``, and
spawn/timeout failures surface as ``ValidatorSpawnError`` (503) and
``ValidatorTimeoutError`` (504).
"""

from __future__ import annotations

import asyncio
import json
import os

import pytest

from sketchos_backend import validator_client as vc
from sketchos_backend.validator_client import (
    ValidatorClient,
    ValidatorSpawnError,
    ValidatorTimeoutError,
)


DEFAULT_THRESHOLDS = {
    "min_height": 2,
    "max_height": 0,
    "min_thickness": 0.1,
    "max_thickness": 0,
}

PASS_REPORT = {"aabb": {}, "objects": [], "violations": []}
VIOLATION_REPORT = {
    "aabb": {},
    "objects": [],
    "violations": [
        {
            "type": "wall_height_min",
            "object": "wall_w1",
            "measured": 1.5,
            "threshold": 2,
            "message": "wall_height_min: object \"wall_w1\" measured 1.500 m, limit 2.000 m",
        }
    ],
}


class FakeProcess:
    """A stand-in for ``asyncio.subprocess.Process``."""

    def __init__(self, returncode=0, stdout=b"", stderr=b"", timeout=False):
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr
        self._timeout = timeout
        self._communicate_calls = 0
        self.killed = False

    async def communicate(self):
        self._communicate_calls += 1
        if self._timeout and self._communicate_calls == 1:
            raise asyncio.TimeoutError()
        return self._stdout, self._stderr

    def kill(self):
        self.killed = True

    async def wait(self):
        return self.returncode


class FakeFactory:
    """Records subprocess invocations and returns a canned process."""

    def __init__(self, process):
        self._process = process
        self.calls = []

    async def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self._process


def make_client(monkeypatch, process, timeout=vc.DEFAULT_TIMEOUT):
    factory = FakeFactory(process)
    monkeypatch.setattr(vc, "create_subprocess_exec", factory)
    return ValidatorClient(timeout=timeout), factory


# --------------------------------------------------------------------------- #
# argv form + shell safety
# --------------------------------------------------------------------------- #


def test_argv_is_list_form_and_shell_never_enabled(monkeypatch):
    process = FakeProcess(returncode=0, stdout=json.dumps(PASS_REPORT).encode())
    client, factory = make_client(monkeypatch, process)

    result = asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    assert result.status == "pass"
    assert len(factory.calls) == 1
    args, kwargs = factory.calls[0]
    # argv is a list of tokens (never a single shell string); argv[0] is the binary.
    assert isinstance(args, tuple)
    assert args[0] == "validator-go"
    assert args[1] == "-input"
    assert args[2].endswith("input.obj")
    assert list(args[3:]) == [
        "-min-height", "2",
        "-max-height", "0",
        "-min-thickness", "0.1",
        "-max-thickness", "0",
    ]
    # shell must never be enabled.
    assert "shell" not in kwargs
    assert kwargs.get("shell") is not True


# --------------------------------------------------------------------------- #
# Binary resolution (env-var → PATH fallback)
# --------------------------------------------------------------------------- #


def test_env_var_resolves_binary(monkeypatch):
    monkeypatch.setenv("VALIDATOR_GO_BIN", "/opt/custom/validator-go")
    process = FakeProcess(returncode=0, stdout=json.dumps(PASS_REPORT).encode())
    client, factory = make_client(monkeypatch, process)

    asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    assert factory.calls[0][0][0] == "/opt/custom/validator-go"


def test_path_fallback_when_env_var_unset(monkeypatch):
    monkeypatch.delenv("VALIDATOR_GO_BIN", raising=False)

    assert ValidatorClient().resolve_binary() == "validator-go"


# --------------------------------------------------------------------------- #
# Exit-code mapping (0 pass / 1 violations / 2 parse error)
# --------------------------------------------------------------------------- #


def test_exit_0_maps_to_pass(monkeypatch):
    process = FakeProcess(returncode=0, stdout=json.dumps(PASS_REPORT).encode())
    client, _ = make_client(monkeypatch, process)

    result = asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    assert result.status == "pass"
    assert result.report == PASS_REPORT


def test_exit_1_maps_to_violations(monkeypatch):
    process = FakeProcess(returncode=1, stdout=json.dumps(VIOLATION_REPORT).encode())
    client, _ = make_client(monkeypatch, process)

    result = asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    assert result.status == "violations"
    assert result.report["violations"][0]["type"] == "wall_height_min"


def test_exit_2_maps_to_parse_error(monkeypatch):
    process = FakeProcess(returncode=2, stdout=b"", stderr=b"obj: bad vertex\n")
    client, _ = make_client(monkeypatch, process)

    result = asyncio.run(client.validate(b"not an obj\n", DEFAULT_THRESHOLDS))

    assert result.status == "parse_error"
    assert result.report is None
    assert "bad vertex" in result.stderr


# --------------------------------------------------------------------------- #
# Temp-file lifecycle (removed in finally)
# --------------------------------------------------------------------------- #


def test_temp_file_removed_in_finally(monkeypatch):
    process = FakeProcess(returncode=0, stdout=json.dumps(PASS_REPORT).encode())
    client, factory = make_client(monkeypatch, process)

    asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    tmp_path = factory.calls[0][0][2]
    assert not os.path.exists(tmp_path)
    assert not os.path.exists(os.path.dirname(tmp_path))


def test_temp_file_removed_on_spawn_failure(monkeypatch):
    def failing_factory(*args, **kwargs):
        failing_factory.calls.append((args, kwargs))
        raise FileNotFoundError("no such binary")

    failing_factory.calls = []
    monkeypatch.setattr(vc, "create_subprocess_exec", failing_factory)
    client = ValidatorClient()

    with pytest.raises(ValidatorSpawnError):
        asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    tmp_path = failing_factory.calls[0][0][2]
    assert not os.path.exists(os.path.dirname(tmp_path))


# --------------------------------------------------------------------------- #
# Spawn failure (503) + timeout (504)
# --------------------------------------------------------------------------- #


def test_spawn_failure_raises_spawn_error(monkeypatch):
    def failing_factory(*args, **kwargs):
        raise FileNotFoundError("no such binary")

    monkeypatch.setattr(vc, "create_subprocess_exec", failing_factory)
    client = ValidatorClient()

    with pytest.raises(ValidatorSpawnError) as excinfo:
        asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    assert "binary not found" in str(excinfo.value)


def test_timeout_raises_timeout_error_and_kills_process(monkeypatch):
    process = FakeProcess(timeout=True)
    client, _ = make_client(monkeypatch, process)

    with pytest.raises(ValidatorTimeoutError):
        asyncio.run(client.validate(b"v 0 0 0\n", DEFAULT_THRESHOLDS))

    assert process.killed is True


# --------------------------------------------------------------------------- #
# Rule extraction (parse NUMERICALLY — Go emits `2`, not `2.0`)
# --------------------------------------------------------------------------- #


def test_extract_rules_parses_numerically(monkeypatch):
    stdout = b'{"min_height":2,"max_height":0,"min_thickness":0.1,"max_thickness":0}'
    process = FakeProcess(returncode=0, stdout=stdout)
    client, factory = make_client(monkeypatch, process)

    thresholds = asyncio.run(client.extract_rules())

    assert factory.calls[0][0] == ("validator-go", "-print-defaults")
    assert thresholds == {
        "min_height": 2,
        "max_height": 0,
        "min_thickness": 0.1,
        "max_thickness": 0,
    }
