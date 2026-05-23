def is_prime(n: int) -> bool:
    if n < 2:
        return False
    d = 2
    while d * d <= n:
        if n % d == 0:
            return False
        d += 1
    return True


primes: list[int] = [n for n in range(2, 101) if is_prime(n)]
print(primes)
