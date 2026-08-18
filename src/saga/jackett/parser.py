import xml.etree.ElementTree as ET

from saga.jackett.jackett_result import JackettResult


def parse_results(xml_content: str) -> list[JackettResult]:
    """Parse torrent results from Torznab XML."""
    xml_root = ET.fromstring(xml_content)

    result_list = []
    for item in xml_root.findall(".//item"):
        seeders_attr = item.find(
            './/torznab:attr[@name="seeders"]',
            namespaces={"torznab": "http://torznab.com/schemas/2015/feed"},
        )
        if seeders_attr is None:
            continue

        seeders = seeders_attr.attrib.get("value", "0")
        if int(seeders) <= 0:
            continue

        raw_title = item.findtext("title")
        size = item.findtext("size")
        link = item.findtext("link")
        indexer = item.findtext("jackettindexer")
        privacy = item.findtext("type")

        magnet = item.find(
            './/torznab:attr[@name="magneturl"]',
            namespaces={"torznab": "http://torznab.com/schemas/2015/feed"},
        )
        magnet_val = magnet.attrib["value"] if magnet is not None else None

        info_hash = item.find(
            './/torznab:attr[@name="infohash"]',
            namespaces={"torznab": "http://torznab.com/schemas/2015/feed"},
        )
        info_hash_val = info_hash.attrib["value"] if info_hash is not None else None

        result = JackettResult(
            rawTitle=raw_title,
            size=size,
            link=link,
            indexer=indexer,
            seeders=seeders,
            magnet=magnet_val,
            infoHash=info_hash_val,
            privacy=privacy,
            type=None,
        )

        result_list.append(result)

    return result_list
