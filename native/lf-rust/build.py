"""Build the longfellow-zk (lf-rust) uniffi wrapper and stage its bindings.

Runs `cargo build` and `uniffi-bindgen` against the wrapper crate beside this script,
then copies the generated `longfellow_zk_uniffi.py` and `liblongfellow_zk_uniffi.so`
into `src/pylongfellow/backends/_lf_rust/`. Idempotent.

Run: uv run python native/lf-rust/build.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CRATE = REPO / "native" / "lf-rust"
SUBMODULE = REPO / "vendor" / "longfellow-zk"
CARGO = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
LIB = "liblongfellow_zk_uniffi.so"
BINDINGS = "longfellow_zk_uniffi.py"
TARGET_SO = CRATE / "target" / "release" / LIB
OUT = CRATE / "target" / "uniffi"
DEST = REPO / "src" / "pylongfellow" / "backends" / "_lf_rust"

_INIT = '"""Generated UniFFI bindings for longfellow-zk/longfellow-zk."""\n'


def _require(condition: bool, message: str) -> None:
    if not condition:
        sys.exit(f"error: {message}")


def _run(args: list[str]) -> None:
    print("+ " + " ".join(args))
    subprocess.run(args, cwd=CRATE, check=True)


def main() -> None:
    _require(
        (SUBMODULE / "rust" / "Cargo.toml").is_file(),
        f"no rust/ tree at {SUBMODULE}; run `git submodule update --init vendor/longfellow-zk`",
    )
    _require(
        Path(CARGO).is_file(),
        f"cargo not found at {CARGO}; install the Rust toolchain (https://rustup.rs)",
    )

    _run([CARGO, "build", "--release"])
    # A target with a static CRT (musl default) drops the cdylib crate type,
    # so cargo can succeed without producing the library.
    _require(
        TARGET_SO.is_file(),
        f"cargo build produced no {LIB}; on musl targets set "
        'RUSTFLAGS="-C target-feature=-crt-static"',
    )
    _run(
        [
            CARGO,
            "run",
            "--release",
            "--bin",
            "uniffi-bindgen",
            "generate",
            "--library",
            str(TARGET_SO),
            "--language",
            "python",
            "--out-dir",
            str(OUT),
        ]
    )

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "__init__.py").write_text(_INIT)
    shutil.copy2(OUT / BINDINGS, DEST / BINDINGS)
    shutil.copy2(TARGET_SO, DEST / LIB)
    print(f"staged {BINDINGS} and {LIB} into {DEST}")


if __name__ == "__main__":
    main()
