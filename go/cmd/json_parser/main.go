package main

import (
	"fmt"
	"strconv"
)

type parser struct {
	src string
	pos int
}

func (p *parser) peek() byte {
	if p.pos < len(p.src) {
		return p.src[p.pos]
	}
	return 0
}

func (p *parser) eat(c byte) bool {
	if p.peek() == c {
		p.pos++
		return true
	}
	return false
}

func (p *parser) ws() {
	for c := p.peek(); c == ' ' || c == '\n' || c == '\r' || c == '\t'; c = p.peek() {
		p.pos++
	}
}

func (p *parser) value() any {
	p.ws()
	switch c := p.peek(); {
	case c == 'n':
		p.pos += 4
		return nil
	case c == 't':
		p.pos += 4
		return true
	case c == 'f':
		p.pos += 5
		return false
	case c == '"':
		return p.str()
	case c == '[':
		return p.arr()
	case c == '{':
		return p.obj()
	default:
		return p.num()
	}
}

func (p *parser) str() string {
	p.pos++
	start := p.pos
	for p.peek() != '"' {
		if p.peek() == '\\' {
			p.pos++
		}
		p.pos++
	}
	s := p.src[start:p.pos]
	p.pos++
	return s
}

func (p *parser) num() float64 {
	start := p.pos
	for c := p.peek(); c == '-' || c == '+' || c == '.' || c == 'e' || c == 'E' || (c >= '0' && c <= '9'); c = p.peek() {
		p.pos++
	}
	n, _ := strconv.ParseFloat(p.src[start:p.pos], 64)
	return n
}

func (p *parser) arr() []any {
	p.pos++
	items := []any{}
	for {
		p.ws()
		if p.eat(']') {
			return items
		}
		items = append(items, p.value())
		p.ws()
		if !p.eat(',') {
			p.eat(']')
			return items
		}
	}
}

func (p *parser) obj() map[string]any {
	p.pos++
	fields := map[string]any{}
	for {
		p.ws()
		if p.eat('}') {
			return fields
		}
		key := p.str()
		p.ws()
		p.eat(':')
		fields[key] = p.value()
		p.ws()
		if !p.eat(',') {
			p.eat('}')
			return fields
		}
	}
}

func main() {
	p := &parser{src: `{"name":"Ada","scores":[1,2,3],"ok":true}`}
	fmt.Printf("%#v\n", p.value())
}
