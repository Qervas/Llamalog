import re
from typing import Tuple
from collections import Counter
import string

def extract_meaningful_words(code: str) -> list:
    """Extract meaningful words from code, focusing on identifiers and important terms."""
    # Remove comments
    code = re.sub(r'//.*|/\*[\s\S]*?\*/|#.*', '', code)

    # Extract words, focusing on camelCase, snake_case, and regular words
    words = re.findall(r'[a-zA-Z][a-zA-Z0-9]*(?:[_-][a-zA-Z0-9]+)*|\b[A-Z][A-Z0-9]+\b', code)

    # Split camelCase
    expanded_words = []
    for word in words:
        expanded_words.extend(re.findall(r'[A-Z][a-z]*|[a-z]+', word))

    # Split snake_case
    final_words = []
    for word in expanded_words:
        final_words.extend(word.split('_'))

    return [w.lower() for w in final_words if len(w) > 2]

def generate_snippet_title(content: str, language: str) -> Tuple[str, str]:
    """Generate a meaningful title for code snippets using simple NLP."""
    # Common words to ignore
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'is', 'are'}

    # Get meaningful words
    words = extract_meaningful_words(content)

    # Count word frequencies
    word_freq = Counter(w for w in words if w not in stop_words)

    # Get the most common words (excluding very common programming terms)
    common_prog_terms = {'int', 'str', 'string', 'float', 'bool', 'void', 'return', 'true', 'false'}
    meaningful_words = [word for word, _ in word_freq.most_common(3)
                       if word not in common_prog_terms][:2]

    if meaningful_words:
        title = " ".join(meaningful_words).title()
        return f"{language}: {title}", f"{language} implementation"

    # Fallback: try to get purpose from first line
    first_line = content.strip().split('\n')[0].strip()
    if first_line.startswith(('def ', 'class ', 'function', 'interface')):
        purpose = first_line.split()[1].split('(')[0]
        return f"{language}: {purpose}", f"{language} definition"

    return f"{language} snippet", f"{language} code"
