# Development

The google-cpp and lf-rust backends build from `vendor/longfellow-zk`; the isrg-rust backend
from `vendor/zk-cred-longfellow`.
[scikit-build-core](https://scikit-build-core.readthedocs.io/) drives the CMake build and
packages the result. The google-cpp backend binds through
[cffi](https://cffi.readthedocs.io/); the isrg-rust and lf-rust backends through
[UniFFI](https://mozilla.github.io/uniffi-rs/).

```
$ git submodule update --init --recursive
$ uv sync                                   # builds google-cpp and isrg-rust, requires backend build dependencies
$ uv run pytest                             # fast suite
$ uv run pytest -m "slow or not slow" --cov # full suite incl. real circuit generation
$ uv run ruff check . && uv run ruff format --check .
$ uv run mypy
$ uv run mkdocs build --strict
```

## google-cpp backend

```
$ sudo apt install -y cmake libssl-dev libzstd-dev libstdc++-13-dev libgtest-dev libbenchmark-dev
$ git submodule update --init vendor/longfellow-zk
$ uv sync --reinstall-package pylongfellow -C cmake.define.PYLONGFELLOW_BUILD_ISRG=OFF
```

`uv sync` builds the `_longfellow` extension. `native/google-cpp/ffibuild.py` emits its C source,
and CMake compiles it and links it against upstream's `mdoc_static`.

## isrg-rust backend

```
$ curl https://sh.rustup.rs | sh
$ git submodule update --init vendor/zk-cred-longfellow
$ uv sync --reinstall-package pylongfellow -C cmake.define.PYLONGFELLOW_BUILD_GOOGLE=OFF
```

`uv sync` builds the `_zk_cred` module. `native/isrg-rust/build.py` drives cargo and
`uniffi-bindgen` against the submodule's unmodified working tree.

## lf-rust backend

```
$ curl https://sh.rustup.rs | sh
$ git submodule update --init vendor/longfellow-zk
$ uv sync --reinstall-package pylongfellow -C cmake.define.PYLONGFELLOW_BUILD_LF_RUST=ON
```

`PYLONGFELLOW_BUILD_LF_RUST` defaults to OFF: a plain `uv sync` and the published wheels omit
the backend. With the switch on, `native/lf-rust/build.py` builds the wrapper crate in
`native/lf-rust/` against the submodule's `rust/` tree and stages the generated
`longfellow_zk_uniffi.py` and the cdylib into `src/pylongfellow/backends/_lf_rust/`.
`lf_rust.materialize_circuit` reads the circuit archives from the submodule checkout at run
time, so the checkout stays on disk after the build.
