use std::collections::BTreeMap;

#[derive(Debug, PartialEq)]
enum Json {
    Null,
    Bool(bool),
    Number(f64),
    String(String),
    Array(Vec<Json>),
    Object(BTreeMap<String, Json>),
}

struct Parser<'a> {
    input: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(input: &'a str) -> Self {
        Self { input: input.as_bytes(), pos: 0 }
    }

    fn parse(mut self) -> Result<Json, String> {
        let value = self.value()?;
        self.ws();
        if self.pos == self.input.len() { Ok(value) } else { Err("trailing input".into()) }
    }

    fn value(&mut self) -> Result<Json, String> {
        self.ws();
        match self.peek() {
            Some(b'n') => self.literal(b"null", Json::Null),
            Some(b't') => self.literal(b"true", Json::Bool(true)),
            Some(b'f') => self.literal(b"false", Json::Bool(false)),
            Some(b'"') => self.string().map(Json::String),
            Some(b'[') => self.array(),
            Some(b'{') => self.object(),
            Some(b'-' | b'0'..=b'9') => self.number().map(Json::Number),
            _ => Err("expected value".into()),
        }
    }

    fn literal(&mut self, word: &[u8], value: Json) -> Result<Json, String> {
        if self.input.get(self.pos..self.pos + word.len()) == Some(word) {
            self.pos += word.len();
            Ok(value)
        } else {
            Err("bad literal".into())
        }
    }

    fn string(&mut self) -> Result<String, String> {
        self.bump(b'"')?;
        let mut out = String::new();
        while let Some(ch) = self.next() {
            match ch {
                b'"' => return Ok(out),
                b'\\' => out.push(match self.next().ok_or("bad escape")? {
                    b'"' => '"',
                    b'\\' => '\\',
                    b'/' => '/',
                    b'b' => '\u{0008}',
                    b'f' => '\u{000c}',
                    b'n' => '\n',
                    b'r' => '\r',
                    b't' => '\t',
                    _ => return Err("unsupported escape".into()),
                }),
                _ => out.push(ch as char),
            }
        }
        Err("unterminated string".into())
    }

    fn number(&mut self) -> Result<f64, String> {
        let start = self.pos;
        self.eat(b'-');
        self.digits();
        if self.eat(b'.') { self.digits(); }
        if self.eat(b'e') || self.eat(b'E') {
            self.eat(b'+') || self.eat(b'-');
            self.digits();
        }
        std::str::from_utf8(&self.input[start..self.pos])
            .unwrap()
            .parse()
            .map_err(|_| "bad number".into())
    }

    fn array(&mut self) -> Result<Json, String> {
        self.bump(b'[')?;
        let mut items = Vec::new();
        loop {
            self.ws();
            if self.eat(b']') { return Ok(Json::Array(items)); }
            items.push(self.value()?);
            self.ws();
            if !self.eat(b',') { self.bump(b']')?; return Ok(Json::Array(items)); }
        }
    }

    fn object(&mut self) -> Result<Json, String> {
        self.bump(b'{')?;
        let mut fields = BTreeMap::new();
        loop {
            self.ws();
            if self.eat(b'}') { return Ok(Json::Object(fields)); }
            let key = self.string()?;
            self.ws();
            self.bump(b':')?;
            fields.insert(key, self.value()?);
            self.ws();
            if !self.eat(b',') { self.bump(b'}')?; return Ok(Json::Object(fields)); }
        }
    }

    fn ws(&mut self) {
        while matches!(self.peek(), Some(b' ' | b'\n' | b'\r' | b'\t')) { self.pos += 1; }
    }

    fn digits(&mut self) {
        while matches!(self.peek(), Some(b'0'..=b'9')) { self.pos += 1; }
    }

    fn bump(&mut self, expected: u8) -> Result<(), String> {
        if self.eat(expected) { Ok(()) } else { Err(format!("expected {}", expected as char)) }
    }

    fn eat(&mut self, expected: u8) -> bool {
        if self.peek() == Some(expected) { self.pos += 1; true } else { false }
    }

    fn next(&mut self) -> Option<u8> {
        let ch = self.peek()?;
        self.pos += 1;
        Some(ch)
    }

    fn peek(&self) -> Option<u8> {
        self.input.get(self.pos).copied()
    }
}

fn main() {
    let json = Parser::new(r#"{"name":"Ada","scores":[1,2,3],"ok":true}"#).parse().unwrap();
    println!("{json:#?}");
}
