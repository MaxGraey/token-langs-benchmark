import re
from collections import Counter


text = "Python is concise and dynamic. Python makes glue code feel modern."
counts = Counter(w.lower() for w in re.findall(r"\w+", text))

for word, count in sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:5]:
    print(f"{word}: {count}")
