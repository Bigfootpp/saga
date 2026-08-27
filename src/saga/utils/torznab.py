import xml.etree.ElementTree as ET

from saga.models.torrent import RawTorrent


def parse(content: str) -> list[RawTorrent]:
    xml_root = ET.fromstring(content)

    namespaces = {"torznab": "http://torznab.com/schemas/2015/feed"}

    results: list[RawTorrent] = []

    for item in xml_root.findall(".//item"):
        title = item.findtext("title")
        info_hash_item = item.find('.//torznab:attr[@name="infohash"]', namespaces=namespaces)
        magnet_item = item.find('.//torznab:attr[@name="magneturl"]', namespaces=namespaces)
        link = item.findtext("link")

        if (
            info_hash_item is None
            or magnet_item is None
            or title is None
            or link is None
        ):
            continue

        info_hash= info_hash_item.attrib.get("value")
        magnet = magnet_item.attrib.get("value")

        if info_hash is None or magnet is None:
            continue

        results.append(RawTorrent(
            title = title,
            info_hash=info_hash,
            magnet=magnet,
            torrent_link=link if not link.startswith("magnet:") else None
        ))

    return results