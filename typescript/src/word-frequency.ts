const text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."

const counts: Record<string, number> = {}
for (const word of text.toLowerCase().match(/\w+/g) ?? []) {
  counts[word] = (counts[word] ?? 0) + 1
}

const top = Object.entries(counts)
  .sort(([a, ac], [b, bc]) => bc - ac || a.localeCompare(b))
  .slice(0, 5)

for (const [word, count] of top) console.log(`${word}: ${count}`)
