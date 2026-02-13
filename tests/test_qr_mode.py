import pytest
from src.mode_selector import QRMode, ModeValidator


@pytest.mark.parametrize(
    "data, expected",
    [
        ("", ValueError),
        ("123", QRMode.NUMERIC),
        ("*HELLO123-+", QRMode.ALPHANUMERIC),
        ("hello123+", QRMode.BYTE),
        ("茗荷", QRMode.KANJI),
        ("😓", ValueError),
    ],
)
def test_mode_priority(data, expected):
    if expected == ValueError:
        with pytest.raises(ValueError):
            ModeValidator(data)._determine_mode()
    else:
        assert ModeValidator(data)._determine_mode() == expected
