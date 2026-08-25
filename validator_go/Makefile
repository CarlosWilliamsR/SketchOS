# Makefile for the validator-go module.
#
# This is intentionally separate from the root Makefile, which drives the NASM
# kernel build. Build/test/bench the Go validator from inside validator_go/.

.PHONY: build test vet bench install

build:
	go build ./...

test:
	go test ./...

vet:
	go vet ./...

bench:
	go test -bench=. -benchmem ./...

# install builds the validator-go binary and copies it into $GOBIN (falling
# back to $(go env GOPATH)/bin when $GOBIN is unset), so the backend can resolve
# it on PATH. Re-run after any validator_go/ change.
install:
	go install .
