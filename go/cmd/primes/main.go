package main

import (
	"fmt"
	"math"
)

func isPrime(n int) bool {
	limit := int(math.Sqrt(float64(n)))
	for d := 2; d <= limit; d++ {
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
