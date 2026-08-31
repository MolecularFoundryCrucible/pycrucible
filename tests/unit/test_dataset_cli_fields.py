"""Unit coverage for the supported dataset CLI mutation fields."""

from crucible.cli.dataset import _dataset_updatable_fields


def test_dataset_cli_excludes_frozen_instrument_assignment():
    fields = _dataset_updatable_fields()

    assert "data_format" in fields
    assert "instrument_id" not in fields
    assert "instrument_name" not in fields
