# pylongfellow

[![CI](https://github.com/pipe23-org/pylongfellow/actions/workflows/ci.yml/badge.svg)](https://github.com/pipe23-org/pylongfellow/actions/workflows/ci.yml)
[![Docs](https://app.readthedocs.org/projects/pylongfellow/badge/?version=latest)](https://pylongfellow.readthedocs.io/en/latest/)
[![PyPI](https://img.shields.io/pypi/v/pylongfellow)](https://pypi.org/project/pylongfellow/)
[![Python](https://img.shields.io/pypi/pyversions/pylongfellow)](https://pypi.org/project/pylongfellow/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## Overview

A thin Python binding to [`google/longfellow-zk`](https://github.com/google/longfellow-zk),
the zero-knowledge library that ISO 18013-5 / EUDI mdoc wallets use to prove attributes of a
credential without revealing the credential. The underlying scheme is described in
[*Anonymous credentials from ECDSA*](https://eprint.iacr.org/2024/2010).

`pylongfellow` is a [cffi](https://cffi.readthedocs.io/) wrapper over the library's
`extern "C"` mdoc ABI (`lib/circuits/mdoc/mdoc_zk.h`). It binds the prove and verify calls and
the few structs they take; it does not add a layer of its own. The binding is
attribute-agnostic — it proves and verifies `(namespace, id, cbor_value)` statements over an
mdoc and has no notion of what any attribute means. `age_over_18` is just the attribute the
examples and tests happen to use.

> **Status: pre-1.0.** Upstream is explicitly experimental and its ABI and circuits can change
> between releases. The vendored upstream is hard-pinned (see [Upstream](#upstream)); treat
> `pylongfellow`, like its upstream, as not production-ready.

For what each function does and the exact types, read the docstrings — they render to a docs
site (mkdocstrings + MkDocs-Material).

## Install

```
pip install pylongfellow
```

Wheels are published for **CPython 3.11–3.14 on Linux x86_64** (manylinux and musllinux). On
any other platform `pip` falls back to the source distribution, which builds the vendored C++
locally and needs a C++ toolchain — see [Build from source](#build-from-source).

The wheel's runtime dependencies are **`cffi`**, **`cryptography`**, and **`cbor2`**. It ships
the google/longfellow-zk backend. The abetterinternet/zk-cred-longfellow (ISRG) backend is not
in any wheel: it is source-build only (see [Backends](#backends)), and its `zstandard` runtime
dependency comes from the `isrg` extra:

```
pip install pylongfellow[isrg]
```

## What it binds

Everything is in the `pylongfellow.mdoc` submodule: `from pylongfellow import mdoc`, then
call `mdoc.verify(...)`. Each function wraps one C entry point. The wrappers marshal
inputs, copy results out, and turn non-success return codes into typed exceptions.

| Python | Role |
|---|---|
| `generate_circuit(spec, *, backend=None)` | produce the compressed circuit a spec names |
| `load_circuit(spec, compressed, *, backend=None)` | load a circuit into a backend, return a `CircuitHandle` |
| `circuit_id(circuit)` | recompute a circuit's canonical id (equals `ZkSpec.circuit_hash`) |
| `find_zk_spec(system, circuit_hash)` | look up a built-in `ZkSpec`, or `None` |
| `prove(handle, mdoc, issuer_pk, transcript, attrs, timestamp)` | holder side; produce a proof |
| `verify(handle, issuer_pk, transcript, attrs, timestamp, proof, doctype, *, device_namespaces=None)` | verifier side; raises on a bad proof, returns on success |

A compressed circuit is bytes: get them from `generate_circuit`, or read a committed blob from
disk. `prove` and `verify` do not take the bytes directly. Pass them once to `load_circuit`,
which returns a `CircuitHandle` bound to a backend, and pass the handle to every `prove` and
`verify` call. `backend` defaults to the google/longfellow-zk backend; see [Backends](#backends).

Two C structs are exposed as frozen dataclasses:

- **`RequestedAttribute(namespace, id, cbor_value)`** — "attribute `(namespace, id)` holds this
  value." `cbor_value` is **raw CBOR bytes** (e.g. `b"\xf5"` is CBOR `true`); the binding does
  no encoding.
- **`ZkSpec(system, circuit_hash, num_attributes, version, block_enc_hash, block_enc_sig)`** —
  a circuit's identity. The spec is the small descriptor prover and verifier agree on;
  `circuit_hash` (SHA-256 hex) pins which circuit it is. `len(attrs)` must equal
  `num_attributes`.

A non-success C return code raises `mdoc.ProverError`, `mdoc.VerifierError`, or
`mdoc.CircuitError`. All three are subclasses of `mdoc.Error`, which is a subclass of
`LongfellowError`:

```
LongfellowError
└── mdoc.Error
    ├── mdoc.ProverError      # .code: mdoc.ProverErrorCode or None
    ├── mdoc.VerifierError    # .code: mdoc.VerifierErrorCode or None
    └── mdoc.CircuitError     # .code: mdoc.CircuitGenerationErrorCode or None
```

Catch by class. `.code` carries the specific failure when the backend supplies one: the
google/longfellow-zk backend always does, the abetterinternet/zk-cred-longfellow (ISRG) backend
leaves it `None`. Do not branch on the code. The code
enums mirror C ints and overlap, so only the exception class says which enum a code is from.

Four functions in `pylongfellow.mdoc` bind no C entry point: `create_credential` assembles
an ISO 18013-5 `DeviceResponse` test credential under locally held keys, with
caller-controlled issuer-signed claims and device namespaces; `create_certificate`,
`sign_device_authentication`, and `verify_device_authentication` are its trust-chain and
device-signature companions. They run on `cryptography` and `cbor2` alone; signatures are
in the [API reference](https://pylongfellow.readthedocs.io/).

## Usage

```python
from pylongfellow import mdoc

spec = mdoc.find_zk_spec("longfellow-libzk-v1", circuit_hash)
compressed = mdoc.generate_circuit(spec)       # or Path(...).read_bytes()
handle = mdoc.load_circuit(spec, compressed)   # google backend by default

attrs = [mdoc.RequestedAttribute("org.iso.18013.5.1", "age_over_18", b"\xf5")]  # CBOR true

proof = mdoc.prove(handle, credential, issuer_pk, transcript, attrs, now)
mdoc.verify(handle, issuer_pk, transcript, attrs, now, proof, doctype)   # raises on failure
```

Migrating from 0.2.x: `prove` and `verify` no longer take the circuit bytes and the trailing
`spec`. Load the circuit once and pass the handle.

```python
# 0.2.x
proof = mdoc.prove(circuit, credential, issuer_pk, transcript, attrs, now, spec)
# 0.3.0
handle = mdoc.load_circuit(spec, circuit)
proof = mdoc.prove(handle, credential, issuer_pk, transcript, attrs, now)
```

A complete, runnable version over a committed sample mdoc is in
[`examples/prove_and_verify.py`](examples/prove_and_verify.py): `find_zk_spec` →
`generate_circuit` → `circuit_id` → `load_circuit` → `prove` → `verify`. It needs nothing but the
package and the bundled fixture; circuit generation takes ~15s.

## Backends

`prove` and `verify` dispatch through the backend a circuit was loaded into. `load_circuit` and
`generate_circuit` take a keyword-only `backend`; the returned `CircuitHandle` carries it, so
`prove` and `verify` need no backend argument. Two backends ship in the source tree.

**google/longfellow-zk** (`pylongfellow.backends.google.BACKEND`) is the default and is in every
wheel. It binds the vendored longfellow-zk C++ library. `can_generate` is `True`. It populates
`.code` on the exceptions it raises and ignores `device_namespaces` on `verify`.

**abetterinternet/zk-cred-longfellow (ISRG)** (`pylongfellow.backends.isrg.BACKEND`) binds
[abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
through its UniFFI bindings. `can_generate` is `False`; it raises `GenerationUnsupportedError`
from `generate_circuit`, so circuits come from `generate_circuit` on the google backend or from
disk. `verify` requires `device_namespaces` (the inner bytes of the tag-24
`DeviceNameSpacesBytes`) and raises `ValueError` without it. It leaves `.code` as `None`.

Select it by passing `backend=` to `load_circuit`:

```python
from pylongfellow.backends import isrg

handle = mdoc.load_circuit(spec, compressed, backend=isrg.BACKEND)
```

The isrg backend is not in any wheel. Build it from source:

```
git submodule update --init vendor/zk-cred-longfellow
uv run python scripts/build_isrg_backend.py     # needs cargo 1.85+; ~4 min cold build
pip install pylongfellow[isrg]                  # zstandard runtime dependency
```

`build_isrg_backend.py` stages the UniFFI-generated Python module and the cdylib into
`src/pylongfellow/backends/_zk_cred/` (gitignored). If the module is not built or `zstandard` is
not installed, the backend raises `BackendUnavailableError`.

Engine init on the isrg backend takes about 18 seconds per role and about 740 MB resident for a
v6 1-attribute circuit. Init is lazy and cached on the handle. `prove` then takes about 1.3
seconds and `verify` about 0.8 seconds on the reference machine.

The differential tests exchange proofs between the two backends in both directions over the
vendored v6 1-attribute circuit, and both backends verify zk-cred-longfellow's committed interop
proof, which google/longfellow-zk generated. For the same statement the isrg proof is larger than
the google proof (562228 versus 323868 bytes).

zk-cred-longfellow is licensed MPL-2.0. `pylongfellow` remains Apache-2.0.

## Logging

Upstream logs to stderr (not Python `logging`, and it exposes no callback to bridge). The one
control is the **`PYLONGFELLOW_LOG_LEVEL`** environment variable, read **once** when the
extension loads — there is no Python API and no runtime reconfiguration, following the
`TF_CPP_MIN_LOG_LEVEL` / `GRPC_VERBOSITY` convention.

Values (case-insensitive): `error`, `warning`, `info`, `silent`. The default is `warning`,
which hides upstream's per-call info output but keeps genuine errors and warnings.

## Build from source

The vendored upstream is a standard CMake project. Prerequisites (Debian/Ubuntu):

```
sudo apt install -y cmake libssl-dev libzstd-dev libstdc++-13-dev libgtest-dev libbenchmark-dev
git submodule update --init --recursive
```

The default `c++` (g++) works. Build and test with [uv](https://docs.astral.sh/uv/):

```
uv sync                                   # builds the extension + dev group, writes uv.lock
uv run pytest                             # fast suite
uv run pytest -m "slow or not slow" --cov # full suite incl. real circuit generation
```

[scikit-build-core](https://scikit-build-core.readthedocs.io/) drives the vendored CMake build
and packages the cffi extension. The internal upstream object libraries are built
position-independent and linked into a single shared object that cffi binds.

Two gotchas worth knowing:

- **`uv sync` won't rebuild on a C/C++-source-only change** — it keys off version and
  dependencies, not native source mtimes, so it silently leaves the old `.so` installed. Force
  it with `uv sync --reinstall-package pylongfellow`.
- **Use a current `uv`.** A stale one can serve a Python alpha (e.g. 3.14.0a4) whose GC
  segfaults at finalization after circuit generation; a shutdown `SIGSEGV` is the symptom.
  Update `uv` and check the interpreter version first.

## How wheels are built

- **Wheels:** [cibuildwheel](https://cibuildwheel.pypa.io/) builds cp311–cp314 ×
  {manylinux, musllinux}, x86_64, with the test suite run inside each build container as the
  gate; `auditwheel` repairs them. A source distribution bundling the pinned upstream ships
  alongside.
- **Publish:** PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no
  long-lived tokens), which emits [PEP 740](https://peps.python.org/pep-0740/) build
  attestations binding each wheel to its source commit.
- **Dev:** uv (envs, lock), ruff (lint + format), mypy (strict), pytest, mkdocs.

## Upstream

`pylongfellow` vendors `google/longfellow-zk` (Apache-2.0) as a git submodule, hard-pinned to a
specific commit (currently **v0.9**, `fe83ec6`) and built from source into each wheel. It does
not float: the upstream ABI and circuits can change between releases, and the test fixtures are
pinned to a particular circuit and version.

The isrg backend vendors `abetterinternet/zk-cred-longfellow` (ISRG, MPL-2.0) as a second git
submodule, hard-pinned to `4f3d1b3`. It is built on demand by `scripts/build_isrg_backend.py`
and is not built into any wheel. `pylongfellow` itself is Apache-2.0.

Not affiliated with Google or the European Commission — an independent binding to a public
Apache-2.0 library.

## License

Apache-2.0, matching upstream.
