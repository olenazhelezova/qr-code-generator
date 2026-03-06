from enum import Enum
from dataclasses import dataclass, field

TERMINATOR_LEN = 4
PAD_BYTES = ["11101100", "00010001"]
ALPHANUMERIC_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:"
ALPHANUMERIC_MAP = {ch: i for i, ch in enumerate(ALPHANUMERIC_CHARS)}


class QREncoderError(Exception):
    pass


class QRErrorCorrection(Enum):
    L = "L"


class QRMode(Enum):
    NUMERIC = "0001"
    ALPHANUMERIC = "0010"
    BYTE = "0100"
    KANJI = "1000"


@dataclass(frozen=True)
class QRVersionSpec:
    version: int
    char_count_bits: dict[QRMode, int]
    capacity_codewords: dict[QRErrorCorrection, int]
    max_allowed_chars: dict[QRErrorCorrection, dict[QRMode, int]]


VERSION_REGISTRY: dict[int, QRVersionSpec] = {
    4: QRVersionSpec(
        version=4,
        char_count_bits={
            QRMode.NUMERIC: 10,
            QRMode.ALPHANUMERIC: 9,
            QRMode.BYTE: 8,
            QRMode.KANJI: 8,
        },
        capacity_codewords={
            QRErrorCorrection.L: 80,
        },
        max_allowed_chars={
            QRErrorCorrection.L: {
                QRMode.NUMERIC: 187,
                QRMode.ALPHANUMERIC: 114,
                QRMode.BYTE: 78,
                QRMode.KANJI: 48,
            },
        },
    )
}


@dataclass
class QREncoder:
    data: str
    version: int = 4
    ec_level: QRErrorCorrection = QRErrorCorrection.L
    mode: QRMode = field(init=False)
    spec: QRVersionSpec = field(init=False)

    def __post_init__(self):
        if not self.data:
            self._error("No data to encode")

        self.spec = VERSION_REGISTRY.get(self.version)
        if not self.spec:
            self._error(f"Version {self.version} is not supported.")

        if isinstance(self.ec_level, str):
            try:
                self.ec_level = QRErrorCorrection(self.ec_level.upper())
            except ValueError:
                self._error(f"Invalid EC Level: '{self.ec_level}'")

        self.mode = self._determine_mode()
        self._validate_len()

    def _validate_len(self):
        max_allowed_chars = self.spec.max_allowed_chars[self.ec_level][self.mode]
        if len(self.data) > max_allowed_chars:
            self._error(
                f"Data too long! Max is {max_allowed_chars} characters for this mode/level."
            )

    def _error(self, message):
        raise QREncoderError(message) from None

    def _is_iso_8859_1(self):
        try:
            self.data.encode("iso-8859-1")
            return True
        except UnicodeEncodeError:
            return False

    def _is_double_byte_shift_jis(self) -> bool:
        try:
            encoded_data = [ch.encode("shift_jis") for ch in self.data]
            return all(len(val) == 2 for val in encoded_data)
        except UnicodeEncodeError:
            return False

    def _determine_mode(self) -> QRMode:
        checks = [
            (self.data.isdigit, QRMode.NUMERIC),
            (
                lambda: all(ch in ALPHANUMERIC_MAP for ch in self.data),
                QRMode.ALPHANUMERIC,
            ),
            (self._is_iso_8859_1, QRMode.BYTE),
            (self._is_double_byte_shift_jis, QRMode.KANJI),
        ]

        for condition, mode in checks:
            if condition():
                return mode

        self._error("Cannot determine QR mode for this data")

    def _encode_numeric(self) -> str:
        bitstream = []

        for i in range(0, len(self.data), 3):
            cur = self.data[i : i + 3]
            match len(cur):
                case 3:
                    bitstream.append(format(int(cur), "010b"))
                case 2:
                    bitstream.append(format(int(cur), "07b"))
                case 1:
                    bitstream.append(format(int(cur), "04b"))

        return "".join(bitstream)

    def _encode_alphanumeric(self) -> str:
        bitstream = []

        for i in range(0, len(self.data), 2):
            cur = self.data[i : i + 2]
            match len(cur):
                case 2:
                    val = (45 * ALPHANUMERIC_MAP[cur[0]]) + ALPHANUMERIC_MAP[cur[1]]
                    bitstream.append(format(int(val), "011b"))
                case 1:
                    val = ALPHANUMERIC_MAP[cur[0]]
                    bitstream.append(format(int(val), "06b"))
        return "".join(bitstream)

    def _encode_byte(self) -> str:
        byte_data = self.data.encode("iso-8859-1")
        bitstream = [format(val, "08b") for val in byte_data]
        return "".join(bitstream)

    def _encode_kanji(self) -> str:
        bitstream = []
        byte_data = self.data.encode("shift_jis")

        for i in range(0, len(byte_data), 2):
            b1, b2 = byte_data[i], byte_data[i + 1]
            val = (b1 << 8) | b2
            if 0x8140 <= val <= 0x9FFC:
                val -= 0x8140
            elif 0xE040 <= val <= 0xEBBF:
                val -= 0xC140
            else:
                self._error(f"Character out of Kanji mode bounds: {hex(val)}")

            high_byte = val >> 8
            low_byte = val & 0xFF

            new_val = (high_byte * 0xC0) + low_byte
            bitstream.append(format(new_val, "013b"))

        return "".join(bitstream)

    def _get_raw_data(self) -> str:
        match self.mode:
            case QRMode.NUMERIC:
                return self._encode_numeric()
            case QRMode.ALPHANUMERIC:
                return self._encode_alphanumeric()
            case QRMode.BYTE:
                return self._encode_byte()
            case QRMode.KANJI:
                return self._encode_kanji()

    @property
    def data_bits(self) -> str:

        mode_indicator = self.mode.value
        char_count = len(self.data)
        bit_len = self.spec.char_count_bits[self.mode]
        char_count_indicator = format(char_count, f"0{bit_len}b")

        bits = mode_indicator + char_count_indicator + self._get_raw_data()
        max_bits = self.spec.capacity_codewords[self.ec_level] * 8

        terminator_len = min(TERMINATOR_LEN, max_bits - len(bits))
        if terminator_len > 0:
            bits += "0" * terminator_len

        bit_padding = (8 - (len(bits) % 8)) % 8
        bits += "0" * bit_padding

        i = 0
        while len(bits) < max_bits:
            bits += PAD_BYTES[i % 2]
            i += 1
        return bits
