"""Test ADE Mapper."""

import ade_mapper


def test_import() -> None:
    """Test that the app can be imported."""
    assert isinstance(ade_mapper.__name__, str)
