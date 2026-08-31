import xml.etree.ElementTree as ET

import pytest

from saga.utils.torznab import parse
from tests.samples.xml_sample import XML_NO_VALID_ITEM, XML_TWO_VALID_ITEM


def test_valid_items_xml():
    torrents = parse(XML_TWO_VALID_ITEM)
    assert len(torrents) == 2
    # first item has link == magnet, so torrent_link should be None
    assert torrents[0].info_hash == "ad07c84915b3e82834c1523fbc12ca03ea5548bc"
    assert torrents[0].torrent_link is None
    assert torrents[0].magnet.startswith("magnet:?xt=urn:btih:")


def test_no_valid_items_xml():
    torrents = parse(XML_NO_VALID_ITEM)
    assert len(torrents) == 0


def test_missing_infohash_filtered():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>Test</title><link>http://example.com/file.torrent</link>
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:abc" /></item>
</channel></rss>"""
    assert parse(xml) == []


def test_missing_magnet_filtered():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>Test</title><link>http://example.com/file.torrent</link>
<torznab:attr name="infohash" value="abc123" /></item>
</channel></rss>"""
    assert parse(xml) == []


def test_missing_title_filtered():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><link>http://example.com/file.torrent</link>
<torznab:attr name="infohash" value="abc123" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:abc" /></item>
</channel></rss>"""
    assert parse(xml) == []


def test_missing_link_filtered():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>Test</title>
<torznab:attr name="infohash" value="abc123" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:abc" /></item>
</channel></rss>"""
    assert parse(xml) == []


def test_infohash_lowercased():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>Test</title><link>http://example.com/file.torrent</link>
<torznab:attr name="infohash" value="ABCDEF1234567890ABCDEF1234567890ABCDEF12" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:ABCDEF1234567890ABCDEF1234567890ABCDEF12" /></item>
</channel></rss>"""
    torrents = parse(xml)
    assert len(torrents) == 1
    assert torrents[0].info_hash == "abcdef1234567890abcdef1234567890abcdef12"


def test_magnet_link_vs_http_link():
    # link starting with magnet: => torrent_link None
    # otherwise torrent_link == link
    xml_magnet = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>A</title><link>magnet:?xt=urn:btih:abc</link>
<torznab:attr name="infohash" value="abc" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:abc" /></item>
</channel></rss>"""
    assert parse(xml_magnet)[0].torrent_link is None

    xml_http = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>B</title><link>http://localhost:9117/dl/file.torrent</link>
<torznab:attr name="infohash" value="def" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:def" /></item>
</channel></rss>"""
    assert parse(xml_http)[0].torrent_link == "http://localhost:9117/dl/file.torrent"


def test_invalid_xml_raises():
    with pytest.raises(ET.ParseError):
        parse("not xml at all <")


def test_empty_attr_value_filtered():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed"><channel>
<item><title>Test</title><link>http://example.com/file.torrent</link>
<torznab:attr name="infohash" />
<torznab:attr name="magneturl" value="magnet:?xt=urn:btih:abc" /></item>
</channel></rss>"""
    assert parse(xml) == []
