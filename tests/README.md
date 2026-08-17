# Tests

This suite tests the backends in `pylongfellow.backends`, pairwise, against a set of test
fixtures. "Pairwise" is accurate for two backends and may change if a third is added.

## Directories

`api/` tests `pylongfellow`'s own API: input validation, error types, marshalling, and
each backend's operations in isolation. A failure here means `pylongfellow`'s own API
broke.

`differential/` tests two backends against each other and against a shared corpus of
circuits and presentations. A failure here means the two implementations stopped
agreeing.
