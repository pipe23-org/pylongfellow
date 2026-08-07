"""Build the abetterinternet/zk-cred-longfellow (ISRG) backend and stage its bindings.

Runs `cargo build` and `uniffi-bindgen` against the vendored submodule, then copies
the generated `zk_cred_longfellow.py` and `libzk_cred_longfellow.so` into
`src/pylongfellow/backends/_zk_cred/`. Idempotent.

Run: uv run python scripts/build_isrg_rust_backend.py
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
# Bindgen output goes under the submodule's target/, which upstream's .gitignore
# already covers, so a build leaves the vendored checkout clean.
OUT = SUBMODULE / "target" / "uniffi"
DEST = REPO / "src" / "pylongfellow" / "backends" / "_zk_cred"

_INIT = '"""Generated UniFFI bindings for abetterinternet/zk-cred-longfellow (ISRG)."""\n'

# To be removed when upstream bumps the uniffi version.
# https://github.com/pipe23-org/pylongfellow/issues/43
_SLOW_WRITE = """\
    def write(self, value):
        with self._reserve(len(value)):
            for i, byte in enumerate(value):
                self.rbuf.data[self.rbuf.len + i] = byte
"""

_FAST_WRITE = """\
    def write(self, value):
        length = len(value)
        with self._reserve(length):
            if length > 0:
                ctypes.memmove(ctypes.addressof(self.rbuf.data.contents) + self.rbuf.len, value, length)
"""


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
    bindings = (DEST / BINDINGS).read_text()
    _require(_SLOW_WRITE in bindings, "uniffi write() loop not found; drop the _SLOW_WRITE patch")
    (DEST / BINDINGS).write_text(bindings.replace(_SLOW_WRITE, _FAST_WRITE))
    print(f"staged {BINDINGS} (write() patched) and {LIB} into {DEST}")


if __name__ == "__main__":
    main()
