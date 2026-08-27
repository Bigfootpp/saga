from saga.utils.torznab import parse
from tests.samples.xml_sample import XML_NO_VALID_ITEM, XML_TWO_VALID_ITEM


def test_valid_items_xml():
    torrents = parse(XML_TWO_VALID_ITEM)
    assert len(torrents) == 2

def test_no_valid_items_xml():
    torrents = parse(XML_NO_VALID_ITEM)
    assert len(torrents) == 0