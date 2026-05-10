fn main() {
    let is_prime = |n| {
        if n < 2 {
            return false;
        }

        let mut d = 2;
        while d * d <= n {
            if n % d == 0 {
                return false;
            }
            d += 1;
        }
        true
    };

    let primes = (2..=100).filter(|&n| is_prime(n)).collect::<Vec<_>>();
    println!("{primes:?}");
}
