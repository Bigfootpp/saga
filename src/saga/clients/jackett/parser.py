import xml.etree.ElementTree as ET

from saga.clients.jackett.jackett_item import JackettItem


def parse_results(xml_content: str) -> list[JackettItem]:
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

        if raw_title is None or size is None or info_hash_val is None:
            raise ValueError("raw_title and size are required fields")

        result = JackettItem(
            raw_title=raw_title,
            size=int(size),
            link=link,
            indexer=indexer,
            magnet=magnet_val,
            info_hash=info_hash_val,
            privacy=privacy
        )

        result_list.append(result)

    return result_list
