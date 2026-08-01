# pylongfellow

`pylongfellow` provides a single Python interface to libraries that implement
[Longfellow](https://eprint.iacr.org/2024/2010) zero-knowledge proofs over ISO 18013-5 mdoc
credentials.

Two backends are supported:
[`google/longfellow-zk`](https://github.com/google/longfellow-zk) (C++, bound through
[cffi](https://cffi.readthedocs.io/)) and
[`abetterinternet/zk-cred-longfellow`](https://github.com/abetterinternet/zk-cred-longfellow)
(Rust, ISRG, bound through UniFFI). A client is bound to one at construction. Differential
tests exchange proofs over every (prover backend, verifier backend) pair.

The package is experimental and unstable.

[![CI](https://github.com/pipe23-org/pylongfellow/actions/workflows/ci.yml/badge.svg)](https://github.com/pipe23-org/pylongfellow/actions/workflows/ci.yml)
[![Docs](https://app.readthedocs.org/projects/pylongfellow/badge/?version=stable)](https://pylongfellow.readthedocs.io/en/stable/)
[![PyPI](https://img.shields.io/pypi/v/pylongfellow)](https://pypi.org/project/pylongfellow/)
[![Python](https://img.shields.io/pypi/pyversions/pylongfellow)](https://pypi.org/project/pylongfellow/)
[![License](https://img.shields.io/badge/License-Apache--2.0%20AND%20MPL--2.0-blue.svg)](#licensing)

## Installation

```
pip install pylongfellow
```

Wheels are published for **CPython 3.11–3.14 on Linux x86_64** (manylinux and musllinux). On
any other platform `pip` falls back to the source distribution, which builds the vendored C++
and Rust locally — see [Development](#development).

The wheel's runtime dependencies are **`cffi`**, **`cryptography`**, **`cbor2`**, and
**`zstandard`**. Every wheel ships both backends: the google/longfellow-zk cffi extension and
the abetterinternet/zk-cred-longfellow (ISRG) cdylib. Construction selects one by registry name
(see [Backends](#backends)); neither requires an extra or a separate install.

Each backend builds behind a CMake switch, default ON. A source install that omits one passes
the switch as a [config setting](https://scikit-build-core.readthedocs.io/en/latest/configuration/index.html):

```
pip install pylongfellow -C cmake.define.PYLONGFELLOW_BUILD_ISRG=OFF   # google-cpp only
pip install pylongfellow -C cmake.define.PYLONGFELLOW_BUILD_GOOGLE=OFF # isrg-rust only
```

The omitted backend raises `BackendUnavailableError` at first use; everything else works
unchanged. A `PYLONGFELLOW_BUILD_GOOGLE=OFF` build needs cargo and none of the apt packages in
[Development](#development). The CMake project enables C and C++, so a C++ compiler is still
required to configure.

## Usage

```python
from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends.google_cpp import find_zk_spec

client = Pylongfellow(backend="google-cpp")

spec = find_zk_spec("longfellow-libzk-v1", circuit_hash)
compressed = client.generate_circuit(spec)  # or Path(...).read_bytes()
handle = client.load_circuit(spec, compressed)

attrs = [mdoc.RequestedAttribute("org.iso.18013.5.1", "age_over_18", b"\xf5")]  # CBOR true

proof = client.prove(handle, credential, issuer_pk, transcript, attrs, now)
client.verify(handle, issuer_pk, transcript, attrs, now, proof, doctype)  # raises on failure
```

Migrating from 0.2.x: the module-level `mdoc` functions are gone; operations are methods on a
client bound to a named backend. `prove` and `verify` no longer take the circuit bytes and the
trailing `spec`. Load the circuit once and pass the handle.

```python
# 0.2.x
proof = mdoc.prove(circuit, credential, issuer_pk, transcript, attrs, now, spec)
# 0.3.0
client = Pylongfellow(backend="google-cpp")
handle = client.load_circuit(spec, circuit)
proof = client.prove(handle, credential, issuer_pk, transcript, attrs, now)
```

A complete, runnable version over a committed sample mdoc is in
[`examples/prove_and_verify.py`](examples/prove_and_verify.py): `find_zk_spec` →
`generate_circuit` → `circuit_id` → `load_circuit` → `prove` → `verify`. It needs nothing but the
package and the bundled fixture; circuit generation takes ~15s.

## Configuration

**`PYLONGFELLOW_LOG_LEVEL`** sets the stderr log level of google/longfellow-zk, read **once**
when the `_longfellow` extension loads, following the `TF_CPP_MIN_LOG_LEVEL` / `GRPC_VERBOSITY`
convention. Values (case-insensitive): `error`, `warning`, `info`, `silent`. The default is
`warning`, which hides upstream's per-call info output but keeps genuine errors and warnings.

google/longfellow-zk logs to stderr, not through Python `logging`, and exposes no callback to
bridge. There is no Python API and no runtime reconfiguration.

## Documentation

<https://pylongfellow.readthedocs.io/en/stable/>. The API reference is generated from the
docstrings and carries the exact types of every function.

## Development

The google-cpp backend needs the `vendor/longfellow-zk` submodule, a C++ compiler, and the
Debian packages `cmake libssl-dev libzstd-dev libstdc++-13-dev libgtest-dev libbenchmark-dev`.
The isrg-rust backend needs the `vendor/zk-cred-longfellow` submodule and cargo 1.85 or newer
([rustup](https://rustup.rs)). Build, test, lint, and type-check with
[uv](https://docs.astral.sh/uv/):

```
git submodule update --init --recursive
uv sync                                   # builds both backends + dev group, writes uv.lock
uv run pytest                             # fast suite
uv run pytest -m "slow or not slow" --cov # full suite incl. real circuit generation
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Per-backend build layout and the known build gotchas are on the
[development page](https://pylongfellow.readthedocs.io/en/stable/development/).

## API

`Pylongfellow` is the entry point: a client bound to one backend at construction. Data types and
errors are in the `pylongfellow.mdoc` submodule; the spec-table functions are in the
`pylongfellow.backends.google_cpp` module, which reads the google-cpp backend's compiled-in
table. Each client method dispatches to a backend, which marshals the inputs, copies the
results out, and turns a non-success return into a typed exception.

| Python | Role |
|---|---|
| `Pylongfellow(*, backend)` | bind a backend, by registry name (`"google-cpp"`, `"isrg-rust"`) or instance |
| `.generate_circuit(spec)` | produce the compressed circuit a spec names |
| `.load_circuit(spec, compressed)` | load a circuit into the bound backend, return a `CircuitHandle` |
| `.prove(handle, mdoc, issuer_pk, transcript, attrs, timestamp)` | holder side; produce a proof |
| `.verify(handle, issuer_pk, transcript, attrs, timestamp, proof, doctype, *, device_namespaces=None)` | verifier side; raises on a bad proof, returns on success |
| `google_cpp.circuit_id(circuit)` | recompute a circuit's canonical id (equals `CircuitSpec.circuit_hash`); google-cpp only |
| `google_cpp.find_zk_spec(system, circuit_hash)` | look up a built-in `CircuitSpec`, or `None`; google-cpp only |
| `google_cpp.zk_specs()` | every `CircuitSpec` compiled into the linked library, in table order; google-cpp only |

A compressed circuit is bytes: get them from `generate_circuit`, or read a committed blob from
disk. `prove` and `verify` do not take the bytes directly. Pass them once to `load_circuit`,
which returns a `CircuitHandle` bound to a backend, and pass the handle to every `prove` and
`verify` call. There is no default backend; construction names one. See [Backends](#backends).

Two C structs are exposed as frozen dataclasses:

- **`RequestedAttribute(namespace, id, cbor_value)`** — "attribute `(namespace, id)` holds this
  value." `cbor_value` is **raw CBOR bytes** (e.g. `b"\xf5"` is CBOR `true`); the binding does
  no encoding.
- **`CircuitSpec(system, circuit_hash, num_attributes, version, block_enc_hash, block_enc_sig)`** —
  a circuit's identity. The spec is the small descriptor prover and verifier agree on;
  `circuit_hash` (SHA-256 hex) pins which circuit it is. `len(attrs)` must equal
  `num_attributes`. Every backend reads `version` and `num_attributes`; the google-cpp backend
  additionally requires the whole record to match its compiled-in spec table.

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
google-cpp backend always does, the isrg-rust backend leaves it `None`. Do not branch on the
code. The code enums mirror C ints and overlap, so only the exception class says which enum a
code is from.

Four functions in `pylongfellow.mdoc` bind no C entry point: `create_credential` assembles
an ISO 18013-5 `DeviceResponse` test credential under locally held keys, with
caller-controlled issuer-signed claims and device namespaces; `create_certificate`,
`sign_device_authentication`, and `verify_device_authentication` are its trust-chain and
device-signature companions. They run on `cryptography` and `cbor2` alone; signatures are
in the [API reference](https://pylongfellow.readthedocs.io/en/stable/reference/).

## Backends

A client is bound to one backend at construction. `Pylongfellow(backend=...)` takes a registry
name or a `Backend` instance and raises `BackendUnavailableError` when the backend's native
dependency is not built. `prove` and `verify` dispatch through the backend a circuit was loaded
into: the `CircuitHandle` carries it, so a handle works on any client. Two backends ship in
every wheel.

**`google-cpp`** binds the vendored longfellow-zk C++ library.
`can_generate` is `True`. It populates `.code` on the exceptions it raises, ignores
`device_namespaces` on `verify`, and checks at load that `spec.circuit_hash` matches the
circuit bytes.

**`isrg-rust`** binds
[abetterinternet/zk-cred-longfellow](https://github.com/abetterinternet/zk-cred-longfellow)
(ISRG) through its UniFFI bindings. `can_generate` is `False`; it raises
`GenerationUnsupportedError` from `generate_circuit`, so circuits come from a `google-cpp`
client or from disk. `verify` requires `device_namespaces` (the inner bytes of the tag-24
`DeviceNameSpacesBytes`) and raises `ValueError` without it. It leaves `.code` as `None`.
Circuit identity checking is backend-native behaviour: this backend does not check
`spec.circuit_hash` at load, so a wrong circuit of the same version and attribute count is not
detected there; mismatched version or count surfaces as an error at `prove`/`verify`.

Select it by name:

```python
client = Pylongfellow(backend="isrg-rust")
handle = client.load_circuit(spec, compressed)
```

In a dev checkout the vendored submodule is initialized first; `uv sync` then builds the backend
as part of the CMake build:

```
git submodule update --init vendor/zk-cred-longfellow
uv sync
```

`scripts/build_isrg_rust_backend.py` runs `cargo build` (cargo 1.85 or newer) and
`uniffi-bindgen`, and stages the generated Python module and the cdylib into
`src/pylongfellow/backends/_zk_cred/` (gitignored). The CMake build runs it, so `uv sync`, wheel
builds, and sdist builds produce the same files. Running the script directly rebuilds the
backend without a full `uv sync`; the cold cargo build takes about 4 minutes. A backend whose
native piece is absent raises `BackendUnavailableError`.

Engine init on the isrg-rust backend takes about 18 seconds per role and about 740 MB resident for a
v6 1-attribute circuit. Init is lazy and cached on the handle. `prove` then takes about 1.3
seconds and `verify` about 0.8 seconds on the reference machine.

The differential tests exchange proofs over every (prover backend, verifier backend) pair,
across the committed v6 and v7 circuits at one to four attributes. Both backends verify the two
proofs imported from zk-cred-longfellow's test vectors, which google/longfellow-zk generated.
For the same statement the isrg-rust proof is larger than the google proof, about 562 kB against
about 324 kB.

zk-cred-longfellow is licensed MPL-2.0; see [Licensing](#licensing).

## Packaging

- **Wheels:** [cibuildwheel](https://cibuildwheel.pypa.io/) builds cp311–cp314 ×
  {manylinux, musllinux}, x86_64, with the test suite run inside each build container as the
  gate; `auditwheel` repairs them. Each wheel carries the cffi extension and the isrg-rust
  cdylib; the cargo build runs once per libc family (the container is shared across the
  CPython passes, so cargo's cache makes the repeats cheap). A source distribution bundling
  both pinned upstreams ships alongside.
- **Publish:** PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) (OIDC, no
  long-lived tokens), which emits [PEP 740](https://peps.python.org/pep-0740/) build
  attestations binding each wheel to its source commit.

## Upstream

`pylongfellow` vendors `google/longfellow-zk` (Apache-2.0) as a git submodule, hard-pinned to a
specific commit (currently **v0.9**, `fe83ec6`) and built from source into each wheel. It does
not float: the upstream ABI and circuits can change between releases, and the test fixtures are
pinned to a particular circuit and version.

The isrg-rust backend vendors `abetterinternet/zk-cred-longfellow` (ISRG, MPL-2.0) as a second
git submodule, hard-pinned to `4f3d1b3`, built from source into each wheel.

Not affiliated with Google or the European Commission — an independent binding to public
libraries.

## Status

You should not rely on this code.

- Upstream google/longfellow-zk is experimental. Its ABI and circuits can change between
  releases, so both vendored upstreams are hard-pinned and do not float.
- The public interface broke in 0.2.0 and again in 0.3.0. There is no stability guarantee
  before 1.0.
- Wheels cover CPython 3.11–3.14 on Linux x86_64 only. Every other platform builds from source.
- The isrg-rust backend does not check a loaded circuit against `spec.circuit_hash`, and leaves
  `.code` unset on the exceptions it raises.
- The backends disagree over a credential whose device signature covers a non-empty namespace
  map: isrg-rust proves and verifies it, google-cpp rejects it as prover and as verifier. The
  record is in [`tests/differential/README.md`](tests/differential/README.md).
- Engine init on the isrg-rust backend costs about 18 seconds per role and about 740 MB
  resident.

## Licensing

`pylongfellow`'s own code is Apache-2.0. The distribution's licence expression is
**`Apache-2.0 AND MPL-2.0`** because each artifact also carries compiled code from the two
vendored upstreams:

- `google/longfellow-zk` — Apache-2.0, compiled into the `_longfellow` extension.
- `abetterinternet/zk-cred-longfellow` (ISRG) — MPL-2.0, compiled into the
  `libzk_cred_longfellow` cdylib.

All three licence texts ship in the wheel and sdist metadata (`license-files`). MPL-2.0 is
file-level copyleft: its terms apply to the zk-cred-longfellow files only and place no
obligations on `pylongfellow`'s code or its users. The vendored files are unmodified; their
source is the pinned upstream commit named above and is included in full in the sdist.
