const range = (start: number, end: number) =>
  Array.from({ length: end - start + 1 }, (_, i) => start + i)

const primes = range(2, 100).filter(n =>
  range(2, Math.floor(Math.sqrt(n))).every(d => n % d !== 0)
)

console.log(primes)
