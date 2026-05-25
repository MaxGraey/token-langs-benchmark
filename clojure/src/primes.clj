(ns primes)

(defn prime? [n]
  (every? #(pos? (rem n %)) (range 2 (inc (long (Math/sqrt n))))))

(defn -main [& _]
  (println (filter prime? (range 2 101))))
