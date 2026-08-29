from pathlib import Path


def get_mock(name: str) -> str:
    with open(Path(__file__).parent / "mock" / name, "r") as f:
        return f.read()

BREAKING_BAD_MOCK = get_mock("breaking_bad.rss")
SNK_MOCK = get_mock("snk.rss")
CALL_OF_THE_NIGHT_MOCK = get_mock("call_of_the_night.rss")
THE_SUMMIT_OF_THE_GODS = get_mock("the_summit_of_the_gods.rss")