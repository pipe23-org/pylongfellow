cmake_minimum_required(VERSION 3.15)
project(pylongfellow LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
# Upstream's object libraries are not position-independent by default; PIC is
# required to link them into the extension's shared object.
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
find_package(Python REQUIRED COMPONENTS Development.Module)

set(_google_cpp "${CMAKE_CURRENT_SOURCE_DIR}/native/google-cpp")
set(_ffi_c "${CMAKE_CURRENT_BINARY_DIR}/_longfellow.c")
add_custom_command(
  OUTPUT "${_ffi_c}"
  COMMAND "${Python_EXECUTABLE}" "${_google_cpp}/ffibuild.py" "${_ffi_c}"
  DEPENDS "${_google_cpp}/ffibuild.py"
  VERBATIM
)

# log_init.cc sets upstream's log level at load; it #includes upstream's
# util/log.h, hence the lib/ include dir.
python_add_library(_longfellow MODULE WITH_SOABI
  "${_ffi_c}" "${_google_cpp}/log_init.cc")
target_include_directories(_longfellow PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}/vendor/longfellow-zk/lib/circuits/mdoc"
  "${CMAKE_CURRENT_SOURCE_DIR}/vendor/longfellow-zk/lib")
target_link_libraries(_longfellow PRIVATE mdoc_static zstd crypto)

install(TARGETS _longfellow LIBRARY DESTINATION pylongfellow)

endif()

# --- isrg-rust backend: uniffi cdylib -------------------------------------
if(PYLONGFELLOW_BUILD_ISRG)
  add_custom_target(zk_cred_backend ALL
    COMMAND "${Python_EXECUTABLE}"
            "${CMAKE_CURRENT_SOURCE_DIR}/native/isrg-rust/build.py"
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
