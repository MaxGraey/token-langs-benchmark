(ns word-frequency
  (:require [clojure.string :as str]))

(def text "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.")

(defn -main [& _]
  (->> text
       str/lower-case
       (re-seq #"\w+")
       frequencies
       (sort-by (juxt (comp - val) key))
       (take 5)
       (run! (fn [[w c]] (println (str w ": " c))))))
