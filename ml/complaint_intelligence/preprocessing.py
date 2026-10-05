"""Text preprocessing and cleaning pipeline for citizen complaint text."""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, Any

from ml.common.exceptions import RoadXDataError


class ComplaintPreprocessor:
    """Preprocessor for natural language citizen grievance text.

    Performs whitespace normalization, Unicode normalization, and text validation while
    preserving critical location indicators, street numbers, and road-related terminology.
    """

    def __init__(self) -> None:
        # Regex for multi-whitespace normalization
        self._whitespace_pattern = re.compile(r"\s+")
        # Regex to strip unwanted control characters while preserving alphanumeric, punctuation, unicode letters
        self._control_char_pattern = re.compile(r"[\x00-\x1f\x7f-\x9f]")

    def validate_text(self, text: Any) -> str:
        """Validate that input text is a non-empty string.

        Raises:
            RoadXDataError: If text is None, non-string, or empty after whitespace stripping.
        """
        if text is None:
            raise RoadXDataError("Complaint text cannot be None.")

        if not isinstance(text, str):
            text = str(text)

        stripped = text.strip()
        if not stripped:
            raise RoadXDataError("Complaint text cannot be empty or whitespace only.")

        return text

    def clean_text(self, text: str) -> str:
        """Perform Unicode NFKC normalization and whitespace cleanup.

        Preserves numbers, punctuation, road names, and case.
        """
        text = self.validate_text(text)

        # 1. Unicode normalization (NFKC)
        normalized = unicodedata.normalize("NFKC", text)

        # 2. Remove control characters
        cleaned = self._control_char_pattern.sub("", normalized)

        # 3. Collapse multiple whitespaces / newlines into a single space
        cleaned = self._whitespace_pattern.sub(" ", cleaned).strip()

        return cleaned

    def preprocess(self, text: str) -> Dict[str, Any]:
        """Process text and return structured preprocessed output dictionary.

        Returns:
            Dict containing:
                - 'raw_text': Original input string
                - 'cleaned_text': Normalized string preserving casing
                - 'lowercase_text': Normalized string in lowercase
                - 'char_count': Character count of cleaned text
                - 'word_count': Word count of cleaned text
        """
        cleaned = self.clean_text(text)
        lowercased = cleaned.lower()
        words = lowercased.split()

        return {
            "raw_text": text,
            "cleaned_text": cleaned,
            "lowercase_text": lowercased,
            "char_count": len(cleaned),
            "word_count": len(words),
        }
