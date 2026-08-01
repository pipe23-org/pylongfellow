# Development

Each backend builds from its own submodule under `vendor/`.
[scikit-build-core](https://scikit-build-core.readthedocs.io/) drives the CMake build and
packages the result. The google-cpp backend binds through
[cffi](https://cffi.readthedocs.io/); the isrg-rust backend through UniFFI.

```
$ git submodule update --init --recursive
$ uv sync                                   # builds both backends, requires backend build dependencies
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

`uv sync` builds the `_longfellow` extension: `src/_cffi_src/_ffibuild.py` emits its C source,
and CMake compiles it and links it against upstream's `mdoc_static`.

The `cdef` in `_ffibuild.py` transcribes the pinned `lib/circuits/mdoc/mdoc_zk.h` by hand, so a
submodule bump calls for a re-check against the header.

The upstream object libraries are not position-independent by default; the build sets
`CMAKE_POSITION_INDEPENDENT_CODE` globally and links them into one shared object.

## isrg-rust backend

```
$ curl https://sh.rustup.rs | sh
$ git submodule update --init vendor/zk-cred-longfellow
$ uv sync --reinstall-package pylongfellow -C cmake.define.PYLONGFELLOW_BUILD_GOOGLE=OFF
```

`uv sync` builds the `zk_cred_longfellow` cdylib and its UniFFI module:
`scripts/build_isrg_rust_backend.py` runs `cargo build --release --features uniffi` and
`uniffi-bindgen`, and stages both into `src/pylongfellow/backends/_zk_cred/` (gitignored).
Running the script directly rebuilds the backend on its own.
