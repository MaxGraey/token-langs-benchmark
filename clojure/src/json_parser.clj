(ns json-parser)

(declare parse-value)

(defn- skip-ws [s i]
  (loop [i i]
    (if (and (< i (count s)) (#{\space \tab \newline \return} (.charAt s i)))
      (recur (inc i))
      i)))

(def ^:private escapes
  {\" \" \\ \\ \/ \/ \b \backspace \f \formfeed \n \newline \r \return \t \tab})

(defn- parse-string [s i]
  (loop [i (inc i), acc (StringBuilder.)]
    (let [c (.charAt s i)]
      (cond
        (= c \")  [(.toString acc) (inc i)]
        (= c \\)  (recur (+ i 2) (.append acc (escapes (.charAt s (inc i)))))
        :else     (recur (inc i) (.append acc c))))))

(defn- parse-number [s i]
  (let [m (re-find #"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?" (subs s i))]
    [(Double/parseDouble m) (+ i (count m))]))

(defn- parse-array [s i]
  (let [i (skip-ws s (inc i))]
    (if (= (.charAt s i) \])
      [[] (inc i)]
      (loop [i i, acc []]
        (let [[v j] (parse-value s i)
              j (skip-ws s j)]
          (case (.charAt s j)
            \, (recur (skip-ws s (inc j)) (conj acc v))
            \] [(conj acc v) (inc j)]))))))

(defn- parse-object [s i]
  (let [i (skip-ws s (inc i))]
    (if (= (.charAt s i) \})
      [{} (inc i)]
      (loop [i i, acc {}]
        (let [[k j] (parse-string s i)
              j (skip-ws s j)
              j (do (assert (= (.charAt s j) \:)) (inc j))
              [v j] (parse-value s (skip-ws s j))
              j (skip-ws s j)]
          (case (.charAt s j)
            \, (recur (skip-ws s (inc j)) (assoc acc k v))
            \} [(assoc acc k v) (inc j)]))))))

(defn parse-value [s i]
  (let [i (skip-ws s i), c (.charAt s i)]
    (case c
      \n [nil (+ i 4)]
      \t [true (+ i 4)]
      \f [false (+ i 5)]
      \" (parse-string s i)
      \[ (parse-array s i)
      \{ (parse-object s i)
      (parse-number s i))))

(defn -main [& _]
  (println (first (parse-value "{\"name\":\"Ada\",\"scores\":[1,2,3],\"ok\":true}" 0))))
