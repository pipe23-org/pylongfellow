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
[![License](https://img.shields.io/badge/License-Apache--2.0%20AND%20MPL--2.0-blue.svg)](#licensing)

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
from pylongfellow import Pylongfellow, mdoc
from pylongfellow.backends.google_cpp import find_zk_spec

longfellow = Pylongfellow(backend="google-cpp")

spec = find_zk_spec("longfellow-libzk-v1", circuit_hash)
circuit = longfellow.generate_circuit(spec)  # or Path(...).read_bytes()
longfellow.load_circuit(spec, circuit)

claims = [mdoc.RequestedAttribute("org.iso.18013.5.1", "age_over_18", b"\xf5")]  # CBOR true
issuer_public_key = mdoc.PublicKey(x, y)

proof = longfellow.prove(credential, issuer_public_key, transcript, claims, now)
longfellow.verify(issuer_public_key, transcript, claims, now, proof, doctype)  # raises on failure
```

A `Pylongfellow` proves and verifies with the circuit it last loaded.

Examples are in [`examples/`](examples/).

## Documentation

<https://pylongfellow.readthedocs.io/en/stable/>. The API reference is generated from the
docstrings and carries the exact types of every function.

## Licensing

`pylongfellow` is licensed Apache-2.0.

The vendored backends are licensed as follows:

- `google/longfellow-zk` — Apache-2.0
- `abetterinternet/zk-cred-longfellow` — MPL-2.0

`pylongfellow` is not affiliated with Google, ISRG, or the European Commission.
