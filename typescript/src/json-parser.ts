type Json = null | boolean | number | string | Json[] | { [key: string]: Json }

const parseJson = (source: string) => {
  let i = 0

  const peek = () => source[i]
  const eat = (ch: string) => peek() === ch && (i++, true)
  const fail = (message: string): never => {
    throw new SyntaxError(`${message} at ${i}`)
  }
  const ws = () => {
    while (/\s/.test(peek() ?? "")) i++
  }

  const literal = (word: string, value: Json) => {
    if (!source.startsWith(word, i)) fail(`expected ${word}`)
    i += word.length
    return value
  }

  const string = () => {
    if (!eat('"')) fail("expected string")
    let out = ""
    while (i < source.length) {
      const ch = source[i++]
      if (ch === '"') return out
      if (ch !== "\\") {
        out += ch
        continue
      }
      const esc = source[i++]
      out += ({
        '"': '"',
        "\\": "\\",
        "/": "/",
        b: "\b",
        f: "\f",
        n: "\n",
        r: "\r",
        t: "\t"
      } as Record<string, string>)[esc] ?? fail("bad escape")
    }
    throw new SyntaxError(`unterminated string at ${i}`)
  }

  const number = () => {
    const start = i
    while (/[-+.eE\d]/.test(peek() ?? "")) i++
    const value = Number(source.slice(start, i))
    return Number.isFinite(value) ? value : fail("bad number")
  }

  const array = () => {
    eat("[")
    const items: Json[] = []
    while (true) {
      ws()
      if (eat("]")) return items
      items.push(value()!)
      ws()
      if (!eat(",")) {
        if (eat("]")) return items
        fail("expected , or ]")
      }
    }
  }

  const object = () => {
    eat("{")
    const fields: Record<string, Json> = {}
    while (true) {
      ws()
      if (eat("}")) return fields
      const key = string()
      ws()
      if (!eat(":")) fail("expected :")
      fields[key] = value()
      ws()
      if (!eat(",")) {
        if (eat("}")) return fields
        fail("expected , or }")
      }
    }
  }

  const value = () => {
    ws()
    const ch = peek()
    if (ch === "n") return literal("null", null)
    if (ch === "t") return literal("true", true)
    if (ch === "f") return literal("false", false)
    if (ch === '"') return string()
    if (ch === "[") return array()
    if (ch === "{") return object()
    if (ch === "-" || /\d/.test(ch ?? "")) return number()
    throw new SyntaxError(`expected value at ${i}`)
  }

  const result = value()
  ws()
  if (i !== source.length) fail("trailing input")
  return result
}

console.log(parseJson('{"name":"Ada","scores":[1,2,3],"ok":true}'))
