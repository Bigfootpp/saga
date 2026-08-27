from saga.utils.torznab import parse
from tests.samples.xml_sample import XML_TWO_VALID_ITEM


def test_valid_xml():
    torrents = parse(XML_TWO_VALID_ITEM)
    assert len(torrents) == 2