from typing import Any


def parse_json(source: str) -> Any:
    i = 0

    def peek() -> str:
        return source[i] if i < len(source) else ""

    def eat(c: str) -> bool:
        nonlocal i
        if peek() == c:
            i += 1
            return True
        return False

    def ws() -> None:
        nonlocal i
        while peek() in " \t\n\r":
            i += 1

    def string() -> str:
        nonlocal i
        i += 1
        start = i
        while peek() != '"':
            if peek() == "\\":
                i += 1
            i += 1
        s = source[start:i]
        i += 1
        return s

    def number() -> float:
        nonlocal i
        start = i
        while peek() in "-+.eE0123456789":
            i += 1
        return float(source[start:i])

    def array() -> list[Any]:
        nonlocal i
        i += 1
        items: list[Any] = []
        while True:
            ws()
            if eat("]"):
                return items
            items.append(value())
            ws()
            if not eat(","):
                eat("]")
                return items

    def obj() -> dict[str, Any]:
        nonlocal i
        i += 1
        fields: dict[str, Any] = {}
        while True:
            ws()
            if eat("}"):
                return fields
            key = string()
            ws()
            eat(":")
            fields[key] = value()
            ws()
            if not eat(","):
                eat("}")
                return fields

    def value() -> Any:
        nonlocal i
        ws()
        c = peek()
        if c == "n":
            i += 4
            return None
        if c == "t":
            i += 4
            return True
        if c == "f":
            i += 5
            return False
        if c == '"':
            return string()
        if c == "[":
            return array()
        if c == "{":
            return obj()
        return number()

    return value()


print(parse_json('{"name":"Ada","scores":[1,2,3],"ok":true}'))
