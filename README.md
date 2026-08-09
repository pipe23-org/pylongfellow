# pylongfellow

`pylongfellow` provides a Python interface to implementations of
[Longfellow](https://eprint.iacr.org/2024/2010) zero-knowledge proofs over ISO 18013-5 mdoc
credentials.

Two backends are supported:

- [`google/longfellow-zk`](https://github.com/google/longfellow-zk)
- [`abetterinternet/zk-cred-longfellow`](https://github.com/abetterinternet/zk-cred-longfellow)

The package is experimental and unstable.

[![CI](https://github.com/pipe23-org/pylongfellow/actions/workflows/ci.yml/badge.svg)](https://github.com/pipe23-org/pylongfellow/actions/workflows/ci.yml)
[![Docs](https://app.readthedocs.org/projects/pylongfellow/badge/?version=stable)](https://pylongfellow.readthedocs.io/en/stable/)
[![PyPI](https://img.shields.io/pypi/v/pylongfellow)](https://pypi.org/project/pylongfellow/)
[![Python](https://img.shields.io/pypi/pyversions/pylongfellow)](https://pypi.org/project/pylongfellow/)
[![License](https://img.shields.io/badge/License-Apache--2.0%20AND%20MPL--2.0-blue.svg)](#license)

## Installation

```
pip install pylongfellow
```

Wheels containing both backends are published for **CPython 3.11–3.14 on Linux x86_64**
(manylinux and musllinux). On any other platform `pip` falls back to the source distribution,
which builds both backends locally — see the
[development page](https://pylongfellow.readthedocs.io/en/stable/development/).

## Usage

```python
import cbor2

from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends.google_cpp import find_zk_spec

longfellow = Pylongfellow(backend="google-cpp")

# The circuit_hash is pre-shared between prover and verifier.
spec = find_zk_spec("longfellow-libzk-v1", circuit_hash)
circuit = longfellow.generate_circuit(spec)  # or Path(...).read_bytes()
longfellow.load_circuit(spec, circuit)

claims = [mdoc.RequestedAttribute("org.iso.18013.5.1", "age_over_18", cbor2.dumps(True))]
issuer_public_key = mdoc.PublicKey(x, y)

proof = longfellow.prove(credential, issuer_public_key, transcript, claims, now)
longfellow.verify(issuer_public_key, transcript, claims, now, proof, doctype)  # raises on failure
```

Examples are in [`examples/`](examples/).

## Documentation

<https://pylongfellow.readthedocs.io/en/stable/>. The API reference is generated from the
docstrings and carries the exact types of every function.

## Upstream

Both backends are vendored as git submodules and built from source into each wheel:

- [`google/longfellow-zk`](https://github.com/google/longfellow-zk) — pinned to **v0.9**
  (`fe83ec6`).
- [`abetterinternet/zk-cred-longfellow`](https://github.com/abetterinternet/zk-cred-longfellow)
  — pinned to `b22d84e`. Upstream publishes no tags. The build applies
  `native/isrg-rust/zk-cred-longfellow-circuit-id.patch` to the checkout, adding a `circuit_id`
  export that upstream does not provide.

The pins do not float: upstream ABIs and circuits can change between releases. A
[nightly canary](https://github.com/pipe23-org/pylongfellow/actions/workflows/canary.yml)
runs the differential suite against both upstream HEADs.

## Development

```
git submodule update --init --recursive
uv sync
uv run pytest
uv run ruff check . && uv run ruff format --check .
uv run mypy
```

Build prerequisites and single-backend builds are on the
[development page](https://pylongfellow.readthedocs.io/en/stable/development/).

## Status

You should not rely on this code.

- Wheels cover CPython 3.11–3.14 on Linux x86_64 only; other platforms build from source.
- The API changes between minor versions.

## License

`pylongfellow` is licensed Apache-2.0.

The vendored backends are licensed as follows:

- `google/longfellow-zk` — Apache-2.0
- `abetterinternet/zk-cred-longfellow` — MPL-2.0

`pylongfellow` is not affiliated with Google, ISRG, or the European Commission.
