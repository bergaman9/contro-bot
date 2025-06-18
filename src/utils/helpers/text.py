"""Text formatting and manipulation utilities."""
import re
from typing import Optional, List
import unicodedata


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to a maximum length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and normalizing."""
    # Normalize unicode characters
    text = unicodedata.normalize('NFKC', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text.strip()


def escape_markdown(text: str) -> str:
    """Escape Discord markdown characters."""
    markdown_chars = ['*', '_', '~', '`', '|', '>', '#', '-', '=', '[', ']', '(', ')']
    for char in markdown_chars:
        text = text.replace(char, f'\\{char}')
    return text


def format_number(number: int) -> str:
    """Format number with thousand separators."""
    return f"{number:,}"


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """Return singular or plural form based on count."""
    if count == 1:
        return f"{count} {singular}"
    return f"{count} {plural or singular + 's'}"


def split_text(text: str, max_length: int = 2000) -> List[str]:
    """Split text into chunks for Discord messages."""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    lines = text.split('\n')
    current_chunk = ""
    
    for line in lines:
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk.strip())
            current_chunk = line
        else:
            current_chunk += '\n' + line if current_chunk else line
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def title_case(text: str) -> str:
    """Convert text to title case, handling special cases."""
    # Words that should remain lowercase
    lowercase_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 'from', 'by', 'of', 'in'}
    
    words = text.lower().split()
    result = []
    
    for i, word in enumerate(words):
        # Always capitalize first and last word
        if i == 0 or i == len(words) - 1:
            result.append(word.capitalize())
        elif word in lowercase_words:
            result.append(word)
        else:
            result.append(word.capitalize())
    
    return ' '.join(result) 