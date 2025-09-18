import random
import re
from bot.config import REWRITE_LEVEL, EXTRA_HASHTAGS

# A dictionary of words and their potential replacements
SYNONYMS = {'buy': ['grab', 'get'], 'today': ['right now', 'today only']}

def light_rewrite(text: str) -> str:
    """
    Performs a light, optional rewrite of the text to avoid exact duplicates.
    Also appends extra hashtags based on a random chance.
    """
    if not text or random.random() > REWRITE_LEVEL:
        return text

    tokens = re.split(r'(\W+)', text)
    out = []
    for t in tokens:
        low = t.lower()
        if low in SYNONYMS and random.random() < 0.5:
            repl = random.choice(SYNONYMS[low])
            # Preserve capitalization
            out.append(repl.capitalize() if t and t[0].isupper() else repl)
        else:
            out.append(t)

    # Optionally add extra hashtags
    if EXTRA_HASHTAGS and random.random() < 0.3:
        out.append(" " + EXTRA_HASHTAGS)

    return "".join(out)
