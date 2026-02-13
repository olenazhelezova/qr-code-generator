from enum import Enum
from dataclasses import dataclass, field


class QRMode(Enum):
    NUMERIC = "numeric"
    ALPHANUMERIC = "alphanumeric"
    BYTE = "byte"
    KANJI = "kanji"


@dataclass
class ModeValidator:
    data: str
    mode: QRMode = field(init=False)

    ALPHANUMERIC_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ$%*+-./: ")

    def __post_init__(self):
        self.mode = self._determine_mode()

    def _is_numeric(self):
        return self.data.isdigit()

    def _is_alphanumeric(self):
        return all(ch in self.ALPHANUMERIC_CHARS for ch in self.data)

    def _is_byte(self):
        try:
            self.data.encode("iso-8859-1")
            return True
        except UnicodeEncodeError:
            return False

    def _is_kanji(self):
        try:
            encoded_data = [ch.encode("shift_jis") for ch in self.data]
            if not all(len(val) == 2 for val in encoded_data):
                return False
            return True
        except UnicodeEncodeError:
            return False

    def _determine_mode(self) -> QRMode:

        if not self.data:
            raise ValueError("No data to encode")

        match True:
            case _ if self._is_numeric():
                return QRMode.NUMERIC
            case _ if self._is_alphanumeric():
                return QRMode.ALPHANUMERIC
            case _ if self._is_byte():
                return QRMode.BYTE
            case _ if self._is_kanji():
                return QRMode.KANJI
            case _:
                raise ValueError("Cannot determine QR mode for this data")
