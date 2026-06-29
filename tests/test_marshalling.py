"""Marshalling done before the C call — the transforms we own and can break."""

from datetime import UTC, datetime, timedelta, timezone

import pytest

import pylongfellow as lf
from pylongfellow._native import _fmt_timestamp


def test_timestamp_canonical_20_bytes():
    out = _fmt_timestamp(datetime(2023, 11, 2, 9, 0, 0, tzinfo=UTC))
    assert out == b"2023-11-02T09:00:00Z"
    assert len(out) == 20


def test_timestamp_converts_to_utc():
    plus_one = timezone(timedelta(hours=1))
    assert (
        _fmt_timestamp(datetime(2023, 11, 2, 10, 0, 0, tzinfo=plus_one)) == b"2023-11-02T09:00:00Z"
    )


def test_timestamp_truncates_subsecond():
    out = _fmt_timestamp(datetime(2023, 11, 2, 9, 0, 0, 500_000, tzinfo=UTC))
    assert out == b"2023-11-02T09:00:00Z"


def test_timestamp_rejects_naive():
    with pytest.raises(ValueError, match="timezone-aware"):
        _fmt_timestamp(datetime(2023, 11, 2, 9, 0, 0))


@pytest.mark.parametrize(
    "attr",
    [
        lf.RequestedAttribute("a" * 65, "age_over_18", b"\xf5"),
        lf.RequestedAttribute("org.iso.18013.5.1", "a" * 33, b"\xf5"),
        lf.RequestedAttribute("org.iso.18013.5.1", "age_over_18", b"\x00" * 65),
    ],
    ids=["namespace", "id", "cbor_value"],
)
def test_fill_attrs_rejects_oversize(attr):
    from pylongfellow._longfellow import ffi
    from pylongfellow._native import _fill_attrs

    with pytest.raises(ValueError, match="too long"):
        _fill_attrs(ffi, [attr])


def test_fill_attrs_fills_each_entry():
    from pylongfellow._longfellow import ffi
    from pylongfellow._native import _fill_attrs

    attrs = [
        lf.RequestedAttribute("org.iso.18013.5.1", "age_over_18", b"\xf5"),
        lf.RequestedAttribute("eu.europa.ec.av.1", "age_over_21", b"\xf4"),
    ]
    c_attrs = _fill_attrs(ffi, attrs)
    for i, attr in enumerate(attrs):
        assert (
            bytes(ffi.buffer(c_attrs[i].namespace_id, c_attrs[i].namespace_len))
            == attr.namespace.encode()
        )
        assert bytes(ffi.buffer(c_attrs[i].id, c_attrs[i].id_len)) == attr.id.encode()
        assert (
            bytes(ffi.buffer(c_attrs[i].cbor_value, c_attrs[i].cbor_value_len)) == attr.cbor_value
        )
