from pathlib import Path


def get_mock(name: str) -> str:
    with open(Path(__file__).parent / "tmdb_mock" / name, "r") as f:
        return f.read()

AOT_FIND_MOCK = get_mock("aot_find.json")
AOT_TRANSLATIONS_MOCK = get_mock("aot_translations.json")
TSOTG_FIND_MOCK = get_mock("tsotg_find.json")
TSOTG_TRANSLATIONS_MOCK = get_mock("tsotg_translations.json")