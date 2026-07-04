# agent/languages.py
"""Utility module for language detection and providing system prompts per language.

The backend expects two symbols:
* `detect_language(text: str) -> str` – returns a language code such as "en" for English.
* `SYSTEM_PROMPTS` – a mapping from language code to a system‑prompt string used by the LLM.

This implementation uses a tiny heuristic based on Unicode ranges for a few Indian languages.
It can be extended later without touching the rest of the code.
"""
import re
from typing import Dict

# Regex patterns for supported scripts
_LANGUAGE_PATTERNS: Dict[str, re.Pattern] = {
    "hi": re.compile(r"[\u0900-\u097F]"),  # Devanagari (Hindi)
    "te": re.compile(r"[\u0C00-\u0C7F]"),  # Telugu
    "ta": re.compile(r"[\u0B80-\u0BFF]"),  # Tamil
    "kn": re.compile(r"[\u0C80-\u0CFF]"),  # Kannada
}


def detect_language(text: str) -> str:
    """Return a short language code for *text*.

    The function scans the text for characters belonging to the supported scripts.
    If a match is found the corresponding ISO‑639‑1 code is returned; otherwise "en"
    (English) is used as the default.
    """
    for code, pattern in _LANGUAGE_PATTERNS.items():
        if pattern.search(text):
            return code
    return "en"


# Minimal system prompts – can be customised per language later
SYSTEM_PROMPTS: Dict[str, str] = {
    "en": "You are an empathetic welfare assistant. Respond in a friendly tone.",
    "hi": "आप एक सहानुभूतिपूर्ण कल्याण सहायक हैं। मित्रवत स्वर में उत्तर दें।",
    "te": "మీరు అనుకంపతో కూడిన సంక్షేమ సహాయకులు. స్నేహపూర్వక టోన్‌లో సమాధానం ఇవ్వండి.",
    "ta": "நீங்கள் இரக்கம் கொண்ட நலன் உதவியாளர். அன்பான தொனியில் பதிலளிக்கவும்.",
    "kn": "ನೀವು ಮನೋಭಾವಪೂರ್ಣ ಕಲ್ಯಾಣ ಸಹಾಯಕ. ಸ್ನೇಹಪರ ಶೈಲಿಯಲ್ಲಿ ಉತ್ತರಿಸಿ.",
}

__all__ = ["detect_language", "SYSTEM_PROMPTS"]
