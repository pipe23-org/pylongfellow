cmake_minimum_required(VERSION 3.15)
project(pylongfellow LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Each backend's native piece builds behind its own switch, default ON. A build
# with a backend off still yields a working package; that backend raises
# BackendUnavailableError at first use. Source installs opt out per backend:
#   pip install pylongfellow -C cmake.define.PYLONGFELLOW_BUILD_ISRG=OFF
option(PYLONGFELLOW_BUILD_GOOGLE "Build the google-cpp backend (cffi extension)" ON)
option(PYLONGFELLOW_BUILD_ISRG "Build the isrg-rust backend (uniffi cdylib)" ON)

find_package(Python REQUIRED COMPONENTS Interpreter)

if(PYLONGFELLOW_BUILD_GOOGLE)

# --- Vendored upstream (hard-pinned submodule at tag v0.9) ----------------
# Provides the `mdoc_static` target, which bundles the flatsha/ec/algebra/util
# object files; its only external link deps are zstd and crypto (OpenSSL).
#
# Upstream's lib/CMakeLists.txt find_package()s GTest and benchmark with
# REQUIRED at configure time (via CMake/proofs.cmake), so both must be installed
# to configure even though we only build the library target and never compile
# upstream's test executables. Debian: libgtest-dev libbenchmark-dev.
#
# EXCLUDE_FROM_ALL: mdoc_static still builds (the extension links it), but
# upstream's own install() rules are skipped — otherwise they leak the static
# lib and mdoc_zk.h into the wheel root.
add_subdirectory(vendor/longfellow-zk/lib EXCLUDE_FROM_ALL)

# --- Python extension: CMake-driven cffi ----------------------------------
# CMake owns the whole build. cffi only *emits* the extension C source
# (_ffibuild.py -> emit_c_code); CMake compiles it and links it against the
# static upstream library. One build system, one compiler.
#
# The cffi build script and the C-linkage log shim are build-input, so they live
# in src/_cffi_src/ — a sibling of the package, not inside it — to keep them out
# of the wheel (scikit-build-core copies every file in a package dir verbatim).
find_package(Python REQUIRED COMPONENTS Development.Module)

set(_cffi_src "${CMAKE_CURRENT_SOURCE_DIR}/src/_cffi_src")
set(_ffi_c "${CMAKE_CURRENT_BINARY_DIR}/_longfellow.c")
add_custom_command(
  OUTPUT "${_ffi_c}"
  COMMAND "${Python_EXECUTABLE}" "${_cffi_src}/_ffibuild.py" "${_ffi_c}"
  DEPENDS "${_cffi_src}/_ffibuild.py"
  VERBATIM
)

# log_init.cc sets upstream's log level at load; it #includes upstream's
# util/log.h, hence the lib/ include dir.
python_add_library(_longfellow MODULE WITH_SOABI
  "${_ffi_c}" "${_cffi_src}/log_init.cc")
target_include_directories(_longfellow PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/vendor/longfellow-zk/lib/circuits/mdoc"
  "${CMAKE_CURRENT_SOURCE_DIR}/vendor/longfellow-zk/lib")
target_link_libraries(_longfellow PRIVATE mdoc_static zstd crypto)

install(TARGETS _longfellow LIBRARY DESTINATION pylongfellow)

endif()

# --- isrg-rust backend: uniffi cdylib -------------------------------------
# scripts/build_isrg_rust_backend.py runs cargo build and uniffi-bindgen
# against the vendored submodule and stages libzk_cred_longfellow.so plus the
# generated bindings into src/pylongfellow/backends/_zk_cred/. That directory
# is gitignored and scikit-build-core's package copy skips gitignored files, so
# the install() rule below is what carries the staged files into the wheel —
# the same route the cffi extension takes. The target runs on every build;
# cargo's own freshness check makes the repeat cheap. The script locates cargo
# itself (PATH, then ~/.cargo/bin) and fails with an install pointer when the
# Rust toolchain is missing.
if(PYLONGFELLOW_BUILD_ISRG)
  add_custom_target(zk_cred_backend ALL
    COMMAND "${Python_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/scripts/build_isrg_rust_backend.py"
    WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
    VERBATIM
  )
  set(_zk_cred "${CMAKE_CURRENT_SOURCE_DIR}/src/pylongfellow/backends/_zk_cred")
  install(FILES
    "${_zk_cred}/__init__.py"
    "${_zk_cred}/zk_cred_longfellow.py"
    "${_zk_cred}/libzk_cred_longfellow.so"
    DESTINATION pylongfellow/backends/_zk_cred
  )
endif()
