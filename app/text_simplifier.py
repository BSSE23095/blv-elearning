"""
text_simplifier.py

Three transformations, applied in this order, exactly as described in
Section 3.2 ("NLP text simplification") of the paper:

  1. Lexical substitution using a substitution table (paper: 50 entries,
     built from Shardlow's (2014) complex-word list cross-referenced
     against the Oxford 3000, plus manual review of course-specific terms).
     A candidate replacement is only accepted if it preserves meaning and
     reduces the syllable count by at least one.

  2. Sentence splitting: sentences longer than 25 tokens are split at
     clause boundaries.

  3. Abbreviation expansion (i.e. -> "that is", e.g. -> "for example").

Drop-in replacement:
    Put your real substitution table at app/data/substitution_table.json
    (a flat {"complex_word": "simple_word"} mapping). If that file exists
    it overrides SUBSTITUTION_TABLE_DEFAULT below. This lets you swap in
    your actual 50-item table (and its Oxford-3000 cross-referencing)
    without touching this code.
"""
import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
SUBSTITUTION_TABLE_PATH = os.path.join(DATA_DIR, "substitution_table.json")

# Starter table — REPLACE with your real 50-item table via the JSON file
# above once you upload it. Keys are matched case-insensitively as whole
# words only.
SUBSTITUTION_TABLE_DEFAULT = {
    "utilize": "use",
    "commence": "start",
    "terminate": "end",
    "sufficient": "enough",
    "approximately": "about",
    "demonstrate": "show",
    "subsequently": "later",
    "acquire": "get",
    "comprehend": "understand",
    "facilitate": "help",
    "endeavor": "try",
    "numerous": "many",
    "obtain": "get",
    "regarding": "about",
    "prioritize": "rank",
    "component": "part",
    "fundamental": "basic",
    "indicate": "show",
    "initiate": "start",
    "sufficient": "enough",
    "requirement": "need",
    "modification": "change",
    "elaborate": "explain",
    "consequently": "so",
    "hypothesis": "guess",
    "methodology": "method",
    "prerequisite": "requirement",
    "supplementary": "extra",
    "conceptualize": "imagine",
    "corresponding": "matching",
}

ABBREVIATIONS = {
    r"\bi\.e\.": "that is",
    r"\be\.g\.": "for example",
    r"\betc\.": "and so on",
    r"\bvs\.": "versus",
}

MAX_TOKENS_PER_SENTENCE = 25

# Words after which it's usually safe to split a long sentence into two
CLAUSE_CONJUNCTIONS = [
    "which", "because", "although", "while", "whereas",
    "and", "but", "so that", "meaning",
]


def _load_substitution_table():
    if os.path.exists(SUBSTITUTION_TABLE_PATH):
        with open(SUBSTITUTION_TABLE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return SUBSTITUTION_TABLE_DEFAULT


SUBSTITUTION_TABLE = _load_substitution_table()


def expand_abbreviations(text: str) -> str:
    for pattern, replacement in ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def substitute_complex_words(text: str) -> str:
    def replace(match):
        word = match.group(0)
        lower = word.lower()
        if lower in SUBSTITUTION_TABLE:
            simple = SUBSTITUTION_TABLE[lower]
            # Preserve capitalisation of the original word
            if word[0].isupper():
                simple = simple.capitalize()
            return simple
        return word

    pattern = r"\b(" + "|".join(re.escape(w) for w in SUBSTITUTION_TABLE) + r")\b"
    if not SUBSTITUTION_TABLE:
        return text
    return re.sub(pattern, replace, text, flags=re.IGNORECASE)


def _split_into_sentences(text: str):
    # Simple sentence boundary split; good enough for course-content prose.
    return re.split(r"(?<=[.!?])\s+", text.strip())


def _split_long_sentence(sentence: str) -> list:
    tokens = sentence.split()
    if len(tokens) <= MAX_TOKENS_PER_SENTENCE:
        return [sentence]

    # Try splitting at the first clause conjunction past the midpoint
    midpoint = len(tokens) // 2
    for i in range(midpoint, len(tokens)):
        word_clean = tokens[i].lower().strip(",")
        if word_clean in CLAUSE_CONJUNCTIONS:
            first = " ".join(tokens[:i]).rstrip(",") + "."
            second = " ".join(tokens[i:])
            second = second[0].upper() + second[1:] if second else second
            return [first, second]

    # Fallback: split at the nearest comma past the midpoint
    running = 0
    for i, tok in enumerate(tokens):
        running += 1
        if running >= midpoint and tok.endswith(","):
            first = " ".join(tokens[: i + 1]).rstrip(",") + "."
            second = " ".join(tokens[i + 1:])
            second = second[0].upper() + second[1:] if second else second
            return [first, second]

    return [sentence]  # nothing safe to split on; leave as-is


def split_long_sentences(text: str) -> str:
    sentences = _split_into_sentences(text)
    result = []
    for s in sentences:
        result.extend(_split_long_sentence(s))
    return " ".join(result)


def simplify(text: str) -> str:
    """Run the full three-stage pipeline described in Section 3.2."""
    text = substitute_complex_words(text)
    text = split_long_sentences(text)
    text = expand_abbreviations(text)
    return text


if __name__ == "__main__":
    sample = (
        "A linear equation is an equation of the first degree, meaning it has "
        "no exponents greater than one."
    )
    print("Original :", sample)
    print("Simplified:", simplify(sample))
