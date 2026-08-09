"""Build the abetterinternet/zk-cred-longfellow (ISRG) backend and stage its bindings.

Runs `cargo build` and `uniffi-bindgen` against the vendored submodule, then copies
the generated `zk_cred_longfellow.py` and `libzk_cred_longfellow.so` into
`src/pylongfellow/backends/_zk_cred/`. Idempotent.

Run: uv run python native/isrg-rust/build.py
"""

import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBMODULE = REPO / "vendor" / "zk-cred-longfellow"
PATCH = Path(__file__).resolve().parent / "zk-cred-longfellow-circuit-id.patch"
CARGO = shutil.which("cargo") or str(Path.home() / ".cargo" / "bin" / "cargo")
GIT = shutil.which("git") or "git"
LIB = "libzk_cred_longfellow.so"
BINDINGS = "zk_cred_longfellow.py"
TARGET_SO = SUBMODULE / "target" / "release" / LIB
OUT = SUBMODULE / "target" / "uniffi"
DEST = REPO / "src" / "pylongfellow" / "backends" / "_zk_cred"

_INIT = '"""Generated UniFFI bindings for abetterinternet/zk-cred-longfellow (ISRG)."""\n'


def _require(condition: bool, message: str) -> None:
    if not condition:
        sys.exit(f"error: {message}")


def _run(args: list[str]) -> None:
    print("+ " + " ".join(args))
    subprocess.run(args, cwd=SUBMODULE, check=True)


def _check(args: list[str]) -> bool:
    return subprocess.run(args, cwd=SUBMODULE, capture_output=True).returncode == 0


def _apply_circuit_id_patch() -> None:
    # To be removed when upstream exports a circuit id.
    # https://github.com/pipe23-org/pylongfellow/issues/51
    if _check([GIT, "apply", "--check", "--reverse", str(PATCH)]):
        return
    _require(
        _check([GIT, "apply", "--check", str(PATCH)]),
        f"{PATCH.name} does not apply to {SUBMODULE}; the vendored pin may have moved",
    )
    _run([GIT, "apply", str(PATCH)])


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
    _require(shutil.which(GIT) is not None, f"{GIT} not found; install git")

    _apply_circuit_id_patch()
    _run([CARGO, "build", "--release", "--features", "uniffi"])
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
