"""Build the zk-cred-longfellow Rust backend and stage its bindings into the package.

Runs `cargo build` and `uniffi-bindgen` against the vendored submodule, then copies
the generated `zk_cred_longfellow.py` and `libzk_cred_longfellow.so` into
`src/pylongfellow/backends/_zk_cred/`. Idempotent.

Run: uv run python scripts/build_rust_backend.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SUBMODULE = REPO / "vendor" / "zk-cred-longfellow"
CARGO = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
LIB = "libzk_cred_longfellow.so"
BINDINGS = "zk_cred_longfellow.py"
TARGET_SO = SUBMODULE / "target" / "release" / LIB
OUT = SUBMODULE / "out"
DEST = REPO / "src" / "pylongfellow" / "backends" / "_zk_cred"

_INIT = '"""Generated UniFFI bindings for the zk-cred-longfellow Rust backend."""\n'


def _require(condition: bool, message: str) -> None:
    if not condition:
        sys.exit(f"error: {message}")


def _run(args: list[str]) -> None:
    print("+ " + " ".join(args))
    subprocess.run(args, cwd=SUBMODULE, check=True)


def main() -> None:
    _require(
        (SUBMODULE / "Cargo.toml").is_file(),
        f"submodule not initialized at {SUBMODULE}; "
        "run `git submodule update --init vendor/zk-cred-longfellow`",
    )
    _require(
        Path(CARGO).is_file(),
        f"cargo not found at {CARGO}; install the Rust toolchain (https://rustup.rs)",
    )

    _run([CARGO, "build", "--release", "--features", "uniffi"])
    _run(
        [
            CARGO,
            "run",
            "--features",
            "uniffi",
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
