fn is_prime(n: i32) -> bool {
    let limit = (n as f64).sqrt() as i32;
    (2..=limit).all(|d| n % d != 0)
}

fn main() {
    let primes: Vec<i32> = (2..=100).filter(|&n| is_prime(n)).collect();
    println!("{:?}", primes);
}
