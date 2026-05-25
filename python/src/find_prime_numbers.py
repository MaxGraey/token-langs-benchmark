import math

def is_prime(n: int) -> bool:
    limit = math.isqrt(n)
    return all(n % d != 0 for d in range(2, limit + 1))

primes: list[int] = [n for n in range(2, 101) if is_prime(n)]
print(primes)
