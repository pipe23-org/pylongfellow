# pylongfellow

A thin Python binding to [`google/longfellow-zk`](https://github.com/google/longfellow-zk),
the zero-knowledge library that ISO 18013-5 / EUDI mdoc wallets use to prove attributes of a
credential without revealing the credential.

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

The wheel's only runtime dependency is **`cffi`**: an API-mode extension imports
`_cffi_backend` at runtime, the same as `cryptography`, `bcrypt`, and `PyNaCl`.

## What it binds

Each function wraps one C entry point. The wrappers marshal inputs, copy results out, and turn
non-success return codes into typed exceptions.

| Python | C entry point | Role |
|---|---|---|
| `generate_circuit(spec)` | `generate_circuit` | produce the compressed circuit a spec names |
| `circuit_id(circuit)` | `circuit_id` | recompute a circuit's canonical id (equals `ZkSpec.circuit_hash`) |
| `find_zk_spec(system, circuit_hash)` | `find_zk_spec` | look up a built-in `ZkSpec`, or `None` |
| `prove(circuit, mdoc, issuer_pk, transcript, attrs, timestamp, spec)` | `run_mdoc_prover` | holder side — produce a proof |
| `verify(circuit, issuer_pk, transcript, attrs, timestamp, proof, doctype, spec)` | `run_mdoc_verifier` | verifier side — raises on a bad proof, returns on success |

A circuit is just bytes: get them from `generate_circuit`, or read a committed blob from disk.
There is no `load_circuit` — `pathlib.Path(...).read_bytes()` is the loader.

Two C structs surface as frozen dataclasses:

- **`RequestedAttribute(namespace, id, cbor_value)`** — "attribute `(namespace, id)` holds this
  value." `cbor_value` is **raw CBOR bytes** (e.g. `b"\xf5"` is CBOR `true`); the binding does
  no encoding.
- **`ZkSpec(system, circuit_hash, num_attributes, version, block_enc_hash, block_enc_sig)`** —
  a circuit's identity. The spec is the small descriptor prover and verifier agree on;
  `circuit_hash` (SHA-256 hex) pins which circuit it is. `len(attrs)` must equal
  `num_attributes`.

Non-success C return codes raise under a single base:

```
LongfellowError
├── ProverError      # .code is an MdocProverErrorCode
├── VerifierError    # .code is an MdocVerifierErrorCode
└── CircuitError     # .code is a CircuitGenerationErrorCode
```

Catch by class; read `.code` for the specific failure. The classes do not collapse to one: the
code enums mirror C ints and overlap, so only the exception class says which enum a code is
from.

## Usage

```python
import json
from datetime import datetime
from pathlib import Path

import pylongfellow as lf

spec = lf.find_zk_spec("longfellow-libzk-v1", circuit_hash)
circuit = lf.generate_circuit(spec)          # or Path(...).read_bytes()

attrs = [lf.RequestedAttribute("org.iso.18013.5.1", "age_over_18", b"\xf5")]  # CBOR true

proof = lf.prove(circuit, mdoc, issuer_pk, transcript, attrs, now, spec)
lf.verify(circuit, issuer_pk, transcript, attrs, now, proof, doctype, spec)   # raises on failure
```

A complete, runnable version over a committed sample mdoc is in
[`examples/prove_and_verify.py`](examples/prove_and_verify.py) — `find_zk_spec` →
`generate_circuit` → `circuit_id` → `prove` → `verify`. It needs nothing but the package and the
bundled fixture; circuit generation takes ~15s.

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

Not affiliated with Google or the European Commission — an independent binding to a public
Apache-2.0 library.

## License

Apache-2.0, matching upstream.
