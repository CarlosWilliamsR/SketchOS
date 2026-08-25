"""Async subprocess client for the Go validator CLI.

``ValidatorClient`` owns binary resolution, argv composition, temp-file
staging, timeout enforcement, and exit-code mapping. It wraps the report-only
``validator-go`` binary as a subprocess — never a sidecar server — and never
passes argv through a shell (list-form argv only, so the boundary is
injection-safe).

The Go binary is read-only: it emits a deterministic JSON report and a process
exit code (0 pass / 1 violations / 2 parse error). This module maps that
contract into a :class:`ValidationResult` and raises typed errors for spawn and
timeout failures so the HTTP layer can map them to 503/504.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from asyncio import create_subprocess_exec
from dataclasses import dataclass
from typing import Any

#: Default binary name resolved from PATH when ``VALIDATOR_GO_BIN`` is unset.
DEFAULT_BINARY = "validator-go"

#: Default subprocess timeout (seconds).
DEFAULT_TIMEOUT = 30.0

#: Prefix for the dedicated temp directory used to stage uploaded .obj bytes.
_TEMP_DIR_PREFIX = "sketchos-validator-"

#: Message carried by :class:`ValidatorSpawnError` (surfaced as a 503).
_SPAWN_MESSAGE = "validator binary not found (set VALIDATOR_GO_BIN or run make install)"


class ValidatorError(Exception):
    """Base class for validator client failures."""


class ValidatorSpawnError(ValidatorError):
    """The validator binary could not be spawned (mapped to HTTP 503)."""


class ValidatorTimeoutError(ValidatorError):
    """The validator subprocess exceeded the timeout (mapped to HTTP 504)."""


@dataclass
class ValidationResult:
    """Outcome of a validation run, mapped from the subprocess exit code.

    ``status`` is ``pass`` (exit 0), ``violations`` (exit 1), or ``parse_error``
    (exit 2). ``report`` is the parsed Go JSON report (``None`` on parse error);
    ``stderr`` carries the diagnostic text.
    """

    status: str
    report: dict[str, Any] | None
    returncode: int
    stderr: str


def _num(value: Any) -> str:
    """Format a numeric threshold for argv without scientific notation."""
    return str(value)


class ValidatorClient:
    """Async wrapper around the ``validator-go`` CLI subprocess."""

    def __init__(self, binary: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._binary = binary
        self._timeout = timeout

    def resolve_binary(self) -> str:
        """Return the binary path: explicit arg → ``VALIDATOR_GO_BIN`` → PATH name."""
        if self._binary:
            return self._binary
        return os.environ.get("VALIDATOR_GO_BIN") or DEFAULT_BINARY

    async def extract_rules(self) -> dict[str, float]:
        """Run ``-print-defaults`` and return the thresholds parsed numerically."""
        argv = [self.resolve_binary(), "-print-defaults"]
        returncode, stdout, stderr = await self._run(argv)
        if returncode != 0:
            raise ValidatorError(
                f"validator-go -print-defaults exited {returncode}: {stderr.strip()}"
            )
        return json.loads(stdout)

    async def validate(self, obj_bytes: bytes, thresholds: dict[str, float]) -> ValidationResult:
        """Stage ``obj_bytes`` to a temp file, run the validator, and map the result.

        The temp file lives in a dedicated ``mkdtemp`` directory removed in a
        ``finally`` block, so it is cleaned up even when the subprocess fails to
        spawn or times out. Thresholds are passed explicitly (never defaulted
        client-side), sharing the ``-print-defaults`` source of truth.
        """
        binary = self.resolve_binary()
        tmp_dir = tempfile.mkdtemp(prefix=_TEMP_DIR_PREFIX)
        try:
            tmp_path = os.path.join(tmp_dir, "input.obj")
            with open(tmp_path, "wb") as fh:
                fh.write(obj_bytes)

            argv = [
                binary,
                "-input", tmp_path,
                "-min-height", _num(thresholds["min_height"]),
                "-max-height", _num(thresholds["max_height"]),
                "-min-thickness", _num(thresholds["min_thickness"]),
                "-max-thickness", _num(thresholds["max_thickness"]),
            ]
            returncode, stdout, stderr = await self._run(argv)
            return self._map_result(returncode, stdout, stderr)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def _run(self, argv: list[str]) -> tuple[int, str, str]:
        """Execute ``argv`` via an async subprocess and return exit/stdout/stderr.

        List-form argv only, ``shell`` never enabled. Raises
        :class:`ValidatorSpawnError` when the binary cannot be spawned and
        :class:`ValidatorTimeoutError` when the timeout elapses (the subprocess
        is killed first).
        """
        try:
            proc = await create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise ValidatorSpawnError(_SPAWN_MESSAGE) from exc

        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=self._timeout
            )
        except asyncio.TimeoutError as exc:
            proc.kill()
            await proc.wait()
            raise ValidatorTimeoutError(
                f"validator timed out after {self._timeout}s"
            ) from exc

        return proc.returncode, stdout_b.decode(), stderr_b.decode()

    @staticmethod
    def _map_result(returncode: int, stdout: str, stderr: str) -> ValidationResult:
        """Map the exit code to a :class:`ValidationResult`.

        0 → pass, 1 → violations (both carry a parsed JSON report), 2 → parse
        error (no JSON report, stderr holds the diagnostic).
        """
        if returncode in (0, 1):
            report = json.loads(stdout)
            status = "pass" if returncode == 0 else "violations"
            return ValidationResult(
                status=status, report=report, returncode=returncode, stderr=stderr
            )
        return ValidationResult(
            status="parse_error", report=None, returncode=returncode, stderr=stderr
        )
