from abc import ABC, abstractmethod

from saga.utils.guessit import GuessitResult


class Element(ABC):
    @abstractmethod
    def format(self, parsed_name: GuessitResult) -> str | None: ...


class TitleElement(Element):
    def format(self, parsed_name: GuessitResult) -> str | None:
        return parsed_name.title or ""


class NewLineElement(Element):
    def __init__(self, count: int = 1) -> None:
        self.count = count

    def format(self, parsed_name: GuessitResult) -> str | None:
        return "\n" * self.count


class DubsLanguagesElement(Element):
    def format(self, parsed_name: GuessitResult) -> str | None:
        return (
            "/".join(parsed_name.audio_languages)
            if parsed_name.audio_languages
            else None
        )


class Formatter:
    def __init__(self, *args: Element) -> None:
        self.elements = [*args]

    def format(self, parsed_name: GuessitResult) -> str:
        result = ""
        for element in self.elements:
            element_str = element.format(parsed_name=parsed_name)
            if element_str:
                result += f" {element_str}" if result else f"{element_str}"

        return result
