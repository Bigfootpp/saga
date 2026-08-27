from pathlib import Path

with open(Path(__file__).parent / "xml" / "two_valid.rss", "r") as f:
    XML_TWO_VALID_ITEM = f.read()