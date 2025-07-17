import re

def split_text(query: str, language: str) -> str:
    # Simple split by sentences or key points
    parts = re.split(r'[.?!;]', query)
    return ' '.join([part.strip() for part in parts if part.strip()]) 