const text = "TypeScript is terse and typed. TypeScript makes app code feel modern.";

const counts = Iterator.from(text.toLowerCase().matchAll(/[\p{L}\p{N}]+/gu))
  .map(([word]) => word)
  .reduce((map, word) => map.set(word, (map.get(word) ?? 0) + 1), new Map<string, number>());

const top = [...counts]
  .sort(([a, ac], [b, bc]) => bc - ac || a.localeCompare(b))
  .slice(0, 5);

console.log(top);
