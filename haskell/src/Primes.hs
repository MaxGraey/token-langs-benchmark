module Primes where

isPrime :: Int -> Bool
isPrime n = all (\d -> n `mod` d /= 0) [2 .. floor (sqrt (fromIntegral n :: Double))]

main :: IO ()
main = print (filter isPrime [2 .. 100])
