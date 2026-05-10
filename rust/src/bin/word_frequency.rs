use std::collections::HashMap;

fn main() {
    let text = "Rust is fast and safe. Rust makes systems code feel modern.";
    let mut counts = HashMap::new();

    for word in text.split(|ch: char| !ch.is_alphanumeric()).filter(|word| !word.is_empty()) {
        *counts.entry(word.to_lowercase()).or_insert(0) += 1;
    }

    let mut words = counts.into_iter().collect::<Vec<_>>();
    words.sort_by_key(|(word, count)| (std::cmp::Reverse(*count), word.clone()));

    for (word, count) in words.into_iter().take(5) {
        println!("{word}: {count}");
    }
}
