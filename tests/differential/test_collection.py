"""Collection integrity: sidecar validation, blob hashes, and cross-references, every run."""

from longfellow_vectors import LongfellowVectors


def test_check_reports_no_findings():
    LongfellowVectors().check()
