import re
from collections import Counter

text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
counts = Counter(w.lower() for w in re.findall(r"\w+", text))

for word, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:5]:
    print(f"{word}: {count}")
