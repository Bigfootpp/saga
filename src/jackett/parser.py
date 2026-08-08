import xml.etree.ElementTree as ET
from typing import Any

from jackett.jackett_indexer import JackettIndexer
from jackett.jackett_result import JackettResult


def parse_indexers(xml_content: str) -> list[JackettIndexer]:
    xml_root = ET.fromstring(xml_content)

    indexer_list = []
    for item in xml_root.findall(".//indexer"):
        indexer = JackettIndexer()

        indexer.title = item.findtext("title")
        indexer.id = item.attrib.get("id")
        indexer.link = item.findtext("link")
        indexer.type = item.findtext("type")
        language_text = item.findtext("language")
        if language_text and language_text.split("-")[0] in ["pt"]:
            indexer.language = language_text
        elif language_text:
            indexer.language = language_text.split("-")[0]

        movie_search = item.find('.//searching/movie-search[@available="yes"]')
        tv_search = item.find('.//searching/tv-search[@available="yes"]')

        if movie_search is not None:
            indexer.movie_search_capabilities = movie_search.attrib[
                "supportedParams"
            ].split(",")
        else:
            # logging handled by caller
            pass

        if tv_search is not None:
            indexer.tv_search_capabilities = tv_search.attrib["supportedParams"].split(
                ","
            )
        else:
            # logging handled by caller
            pass

        indexer_list.append(indexer)

    return indexer_list


def parse_results(xml_content: str) -> list[Any]:
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
