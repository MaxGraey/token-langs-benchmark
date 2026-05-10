const range = function* (end: number) {
  for (let n = 2; n <= end; n++) yield n;
};

const isPrime = (n: number) => {
  for (let d = 2; d * d <= n; d++) {
    if (n % d === 0) return false;
  }
  return n >= 2;
};

const primes = Iterator.from(range(100)).filter(isPrime).toArray();
console.log(primes);
