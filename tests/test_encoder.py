import pytest
from qr_code.encoder import QRMode, QREncoder, QREncoderError


@pytest.mark.parametrize(
    "data, expected_mode",
    [
        ("123", QRMode.NUMERIC),
        ("*HELLO123-+", QRMode.ALPHANUMERIC),
        ("hello123+", QRMode.BYTE),
        ("茗荷", QRMode.KANJI),
    ],
)
def test_mode_priority_success(data, expected_mode):
    assert QREncoder(data).mode == expected_mode


@pytest.mark.parametrize(
    "data, expected_error_msg",
    [
        ("", "No data to encode"),
        ("😓", "Cannot determine QR mode for this data"),
    ],
)
def test_mode_priority_errors(data, expected_error_msg):
    with pytest.raises(QREncoderError, match=expected_error_msg):
        QREncoder(data).mode


def test_invalid_ec_level():
    with pytest.raises(QREncoderError, match="Invalid EC Level: 'Z'"):
        QREncoder("HELLO", 4, "Z")


def test_unsupported_version():
    with pytest.raises(QREncoderError, match="Version 99 is not supported."):
        QREncoder("HELLO", 99, "L")


def test_data_too_long():
    long_data = "A" * 115
    with pytest.raises(QREncoderError, match="Data too long!"):
        QREncoder(long_data, 4, "L")


@pytest.mark.parametrize(
    "data, expected_bits",
    [
        ("123", "0001111011"),
        ("1234", "0001111011" + "0100"),
        ("12345", "0001111011" + "0101101"),
        ("AB", "00111001101"),
        ("ABC", "00111001101" + "001100"),
        ("a", "01100001"),
        ("ab", "01100001" + "01100010"),
    ],
)
def test_raw_data_encoding_edge_cases(data, expected_bits):
    encoder = QREncoder(data)
    assert encoder._get_raw_data() == expected_bits


@pytest.mark.parametrize(
    "data, expected_header",
    [
        ("12345", "0001" + "0000000101"),
        ("HELLO", "0010" + "000000101"),
        ("hello", "0100" + "00000101"),
        ("茗荷", "1000" + "00000010"),
    ],
)
def test_final_data_bits_assembly_and_padding(data, expected_header):
    encoder = QREncoder(data, 4, "L")
    bits = encoder.data_bits
    assert len(bits) == 640
    assert bits.startswith(expected_header)
    assert "1110110000010001" in bits
