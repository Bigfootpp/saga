from utils.logger import setup_logger

logger = setup_logger(__name__)


def get_info_hash_from_magnet(magnet: str | None) -> str:
    if not magnet:
        return ""
    exact_topic_index = magnet.find("xt=")
    if exact_topic_index == -1:
        logger.debug(f"No exact topic in magnet: {magnet[:100]}...")
        return ""

    exact_topic_substring = magnet[exact_topic_index:]
    end_of_exact_topic = exact_topic_substring.find("&")
    if end_of_exact_topic != -1:
        exact_topic_substring = exact_topic_substring[:end_of_exact_topic]

    info_hash = exact_topic_substring[exact_topic_substring.rfind(":") + 1 :]

    return info_hash.lower() if info_hash else ""
