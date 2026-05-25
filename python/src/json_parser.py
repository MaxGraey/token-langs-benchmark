from typing import Any, NoReturn

ESCAPES = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}

def parse_json(source: str) -> Any:
    i = 0

    def fail(msg: str) -> NoReturn:
        raise ValueError(f"{msg} at {i}")

    def peek() -> str:
        return source[i] if i < len(source) else ""

    def eat(c: str) -> bool:
        nonlocal i
        if peek() == c:
            i += 1
            return True
        return False

    def expect(c: str) -> None:
        if not eat(c):
            fail(f"expected {c!r}")

    def ws() -> None:
        nonlocal i
        while peek() in " \t\n\r":
            i += 1

    def literal(word: str, val: Any) -> Any:
        nonlocal i
        if not source.startswith(word, i):
            fail(f"expected {word}")
        i += len(word)
        return val

    def string() -> str:
        nonlocal i
        expect('"')
        out: list[str] = []
        while i < len(source):
            c = source[i]
            i += 1
            if c == '"':
                return "".join(out)
            if c != "\\":
                out.append(c)
                continue
            if i >= len(source) or source[i] not in ESCAPES:
                fail("bad escape")
            out.append(ESCAPES[source[i]])
            i += 1
        fail("unterminated string")

    def number() -> float:
        nonlocal i
        start = i
        eat("-")
        while peek().isdigit():
            i += 1
        if eat("."):
            while peek().isdigit():
                i += 1
        if eat("e") or eat("E"):
            if not eat("+"):
                eat("-")
            while peek().isdigit():
                i += 1
        try:
            return float(source[start:i])
        except ValueError:
            fail("bad number")

    def array() -> list[Any]:
        expect("[")
        items: list[Any] = []
        while True:
            ws()
            if eat("]"):
                return items
            items.append(value())
            ws()
            if not eat(","):
                expect("]")
                return items

    def obj() -> dict[str, Any]:
        expect("{")
        fields: dict[str, Any] = {}
        while True:
            ws()
            if eat("}"):
                return fields
            key = string()
            ws()
            expect(":")
            fields[key] = value()
            ws()
            if not eat(","):
                expect("}")
                return fields

    def value() -> Any:
        ws()
        c = peek()
        if c == "n":
            return literal("null", None)
        if c == "t":
            return literal("true", True)
        if c == "f":
            return literal("false", False)
        if c == '"':
            return string()
        if c == "[":
            return array()
        if c == "{":
            return obj()
        if c == "-" or c.isdigit():
            return number()
        fail("expected value")

    result = value()
    ws()
    if i != len(source):
        fail("trailing input")
    return result


print(parse_json('{"name":"Ada","scores":[1,2,3],"ok":true}'))
