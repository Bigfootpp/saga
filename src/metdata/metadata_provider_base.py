from models.config import Config
from models.movie import Movie
from models.series import Series
from utils.logger import setup_logger


class MetadataProvider:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(__name__)

    def replace_weird_characters(self, string: str) -> str:
        corresp = {
            "ā": "a",
            "ă": "a",
            "ą": "a",
            "ć": "c",
            "č": "c",
            "ç": "c",
            "ĉ": "c",
            "ċ": "c",
            "ď": "d",
            "đ": "d",
            "è": "e",
            "é": "e",
            "ê": "e",
            "ë": "e",
            "ē": "e",
            "ĕ": "e",
            "ę": "e",
            "ě": "e",
            "ĝ": "g",
            "ğ": "g",
            "ġ": "g",
            "ģ": "g",
            "ĥ": "h",
            "î": "i",
            "ï": "i",
            "ì": "i",
            "í": "i",
            "ī": "i",
            "ĩ": "i",
            "ĭ": "i",
            "ı": "i",
            "ĵ": "j",
            "ķ": "k",
            "ĺ": "l",
            "ļ": "l",
            "ł": "l",
            "ń": "n",
            "ň": "n",
            "ñ": "n",
            "ņ": "n",
            "ŉ": "n",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ö": "o",
            "ø": "o",
            "ō": "o",
            "ő": "o",
            "œ": "oe",
            "ŕ": "r",
            "ř": "r",
            "ŗ": "r",
            "š": "s",
            "ş": "s",
            "ś": "s",
            "ș": "s",
            "ß": "ss",
            "ť": "t",
            "ţ": "t",
            "ū": "u",
            "ŭ": "u",
            "ũ": "u",
            "û": "u",
            "ü": "u",
            "ù": "u",
            "ú": "u",
            "ų": "u",
            "ű": "u",
            "ŵ": "w",
            "ý": "y",
            "ÿ": "y",
            "ŷ": "y",
            "ž": "z",
            "ż": "z",
            "ź": "z",
            "æ": "ae",
            "ǎ": "a",
            "ǧ": "g",
            "ə": "e",
            "ƒ": "f",
            "ǐ": "i",
            "ǒ": "o",
            "ǔ": "u",
            "ǚ": "u",
            "ǜ": "u",
            "ǹ": "n",
            "ǻ": "a",
            "ǽ": "ae",
            "ǿ": "o",
        }

        for weird_char, correct in corresp.items():
            string = string.replace(weird_char, correct)

        return string

    def get_metadata(self, id: str, type: str) -> Movie | Series | None:
        raise NotImplementedError
