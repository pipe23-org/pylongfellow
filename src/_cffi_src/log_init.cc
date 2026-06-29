// Set upstream's stderr log level once, when the extension loads.
//
// Upstream logs to stderr through proofs::set_log_level (util/log.h), a C++
// symbol in `namespace proofs` (not part of the extern "C" mdoc_zk.h ABI). We
// don't expose a Python knob — instead, following the TF_CPP_MIN_LOG_LEVEL /
// GRPC_VERBOSITY convention, the level is read once from the PYLONGFELLOW_LOG_LEVEL
// environment variable when the extension's shared object loads. Set-once: there
// is no runtime reconfiguration.
//
// The attribute puts this function's address in .init_array; the dynamic loader
// calls it during dlopen (inside the binding's first extension import), before
// any prove/verify/generate call can run. This file is C++, so it calls the C++
// proofs::set_log_level directly — no extern "C" bridge needed.
//
// Default (unset): WARNING, which hides upstream's per-call INFO firehose but
// leaves genuine ERROR/WARNING on stderr. Recognised values (case-insensitive):
// error, warning, info, silent. Unrecognised values leave the default.

#include <cstdlib>
#include <strings.h>  // strcasecmp (POSIX; the wheels target Linux only)

#include "util/log.h"

__attribute__((constructor)) static void init_log_level(void) {
  const char* v = std::getenv("PYLONGFELLOW_LOG_LEVEL");
  if (v == nullptr || strcasecmp(v, "warning") == 0) {
    proofs::set_log_level(proofs::WARNING);
  } else if (strcasecmp(v, "error") == 0) {
    proofs::set_log_level(proofs::ERROR);
  } else if (strcasecmp(v, "info") == 0) {
    proofs::set_log_level(proofs::INFO);
  } else if (strcasecmp(v, "silent") == 0) {
    proofs::set_log_level(static_cast<proofs::LogLevel>(0));
  } else {
    proofs::set_log_level(proofs::WARNING);
  }
}
