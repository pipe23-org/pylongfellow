# Development

A dev checkout builds both backends from vendored sources. Each backend has its own toolchain
and its own git submodule, and each builds behind a CMake switch that defaults to ON.
[scikit-build-core](https://scikit-build-core.readthedocs.io/) drives the CMake build and
packages the result.

## google-cpp backend

The backend compiles `google/longfellow-zk` from the `vendor/longfellow-zk` submodule and binds
it through cffi. Prerequisites (Debian/Ubuntu):

```
sudo apt install -y cmake libssl-dev libzstd-dev libstdc++-13-dev libgtest-dev libbenchmark-dev
git submodule update --init vendor/longfellow-zk
```

The default `c++` (g++) works. OpenSSL and zstd are link dependencies of the upstream
`mdoc_static` target. GoogleTest and Benchmark are configure-time requirements: upstream's
`lib/CMakeLists.txt` calls `find_package` on both with `REQUIRED`, even though only the library
target is built and upstream's test executables never compile.

`src/_cffi_src/_ffibuild.py` emits the extension C source; CMake compiles it, links it against
`mdoc_static`, and installs the result as the `_longfellow` extension. The `cdef` in that file
transcribes the pinned upstream `lib/circuits/mdoc/mdoc_zk.h` by hand, so a submodule bump calls
for a re-check against the header. The upstream object libraries are not
position-independent by default, so the build sets `CMAKE_POSITION_INDEPENDENT_CODE` globally
and links them into one shared object.

`-C cmake.define.PYLONGFELLOW_BUILD_GOOGLE=OFF` omits the backend from a source install.

## isrg-rust backend

The backend compiles `abetterinternet/zk-cred-longfellow` from the `vendor/zk-cred-longfellow`
submodule and binds it through UniFFI. Prerequisites are cargo 1.85 or newer, from
[rustup](https://rustup.rs), and the submodule:

```
git submodule update --init vendor/zk-cred-longfellow
```

The vendored crate is edition 2024, which sets the cargo floor at 1.85.
`scripts/build_isrg_rust_backend.py` runs `cargo build --release --features uniffi` and
`uniffi-bindgen`, then stages `zk_cred_longfellow.py` and `libzk_cred_longfellow.so` into
`src/pylongfellow/backends/_zk_cred/`, which is gitignored. The script finds cargo on `PATH`,
then at `~/.cargo/bin`, and exits with an install pointer when it finds neither.

A CMake target runs the script on every build, so `uv sync`, wheel builds, and sdist builds
produce the same files; running the script directly rebuilds the backend on its own. The cold
cargo build takes about 4 minutes.

A target with a static CRT drops the `cdylib` crate type, and cargo then succeeds without
producing the library. musl targets need `RUSTFLAGS="-C target-feature=-crt-static"`; the build
script fails with a named error when cargo produces no cdylib.

`-C cmake.define.PYLONGFELLOW_BUILD_ISRG=OFF` omits the backend from a source install.

## uv workflow

[uv](https://docs.astral.sh/uv/) owns the environment and the lock:

```
uv sync                                   # builds both backends + dev group, writes uv.lock
uv run pytest                             # fast suite
uv run pytest -m "slow or not slow" --cov # full suite incl. real circuit generation
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run mkdocs build --strict
```

`uv sync` installs the project editable, so the staged backend files under `src/` are the ones
imported at run time. Coverage is gated at 100% branch coverage and is only reachable with the
full suite: `generate_circuit`'s path runs in a `slow`-marked test. The dev toolchain is uv
(envs, lock), ruff (lint + format), mypy (strict), pytest, and mkdocs.

## Build gotchas

- **`uv sync` won't rebuild on a C/C++-source-only change.** It keys off version and
  dependencies, not native source mtimes, so it leaves the old `.so` installed. Force it with
  `uv sync --reinstall-package pylongfellow`.
- **Use a current `uv`.** A stale one can serve a Python alpha (e.g. 3.14.0a4) whose GC
  segfaults at finalization after circuit generation; a shutdown `SIGSEGV` is the symptom.
  Update `uv` and check the interpreter version first.
