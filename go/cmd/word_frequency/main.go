package main

import (
	"fmt"
	"sort"
	"strings"
	"unicode"
)

func main() {
	text := "Go is small and fast. Go makes server code feel modern."
	counts := map[string]int{}
	for _, w := range strings.FieldsFunc(text, func(r rune) bool {
		return !unicode.IsLetter(r) && !unicode.IsDigit(r)
	}) {
		counts[strings.ToLower(w)]++
	}

	type kv struct {
		word  string
		count int
	}
	words := make([]kv, 0, len(counts))
	for w, c := range counts {
		words = append(words, kv{w, c})
	}
	sort.Slice(words, func(i, j int) bool {
		if words[i].count != words[j].count {
			return words[i].count > words[j].count
		}
		return words[i].word < words[j].word
	})

	for _, p := range words[:min(5, len(words))] {
		fmt.Printf("%s: %d\n", p.word, p.count)
	}
}
