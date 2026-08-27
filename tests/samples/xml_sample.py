from pathlib import Path


def get_xml(name: str) -> str:
    with open(Path(__file__).parent / "xml" / name, "r") as f:
        return f.read()

XML_TWO_VALID_ITEM = get_xml("two_valid.rss")
XML_NO_VALID_ITEM = get_xml("no_valid.rss")