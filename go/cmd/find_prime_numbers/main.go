package main

import "fmt"

func isPrime(n int) bool {
	if n < 2 {
		return false
	}
	for d := 2; d*d <= n; d++ {
		if n%d == 0 {
			return false
		}
	}
	return true
}

func main() {
	primes := []int{}
	for n := 2; n <= 100; n++ {
		if isPrime(n) {
			primes = append(primes, n)
		}
	}
	fmt.Println(primes)
}
