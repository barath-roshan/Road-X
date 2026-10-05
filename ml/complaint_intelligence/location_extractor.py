"""Location entity mention extractor for citizen complaint text."""

from __future__ import annotations

import re
from typing import List, Dict, Tuple, Optional

from ml.complaint_intelligence.schemas import LocationMention, LocationEntityType


class LocationExtractor:
    """Extracts candidate location entity mentions (landmarks, roads, bus stops, intersections, localities)

    from natural language complaint text.

    Note: Extracted text mentions are string entity references for assisted intelligence
    and must NOT be confused with authoritative GPS coordinates provided separately.
    """

    def __init__(self) -> None:
        # Pre-compile Regex patterns for various Indian location entity types
        self._patterns: List[Tuple[LocationEntityType, re.Pattern[str]]] = [
            (
                LocationEntityType.BUS_STOP,
                re.compile(
                    r"\b(?:near|at|opposite|behind|beside)?\s*"
                    r"([A-Z0-9][a-zA-Z0-9'\.-]+(?:\s+[A-Z0-9][a-zA-Z0-9'\.-]+)*\s+(?:bus\s*stand|bus\s*stop|bus\s*terminal|depot))\b",
                    re.IGNORECASE,
                ),
            ),
            (
                LocationEntityType.INTERSECTION,
                re.compile(
                    r"\b(?:near|at|opposite|behind|on)?\s*"
                    r"([A-Z0-9][a-zA-Z0-9'\.-]+(?:\s+[A-Z0-9][a-zA-Z0-9'\.-]+)*\s+(?:junction|intersection|cross|crossing|signal|circle|roundabout|flyover|bridge))\b",
                    re.IGNORECASE,
                ),
            ),
            (
                LocationEntityType.ROAD,
                re.compile(
                    r"\b(?:on|near|along)?\s*"
                    r"([A-Z0-9][a-zA-Z0-9'\.-]+(?:\s+[A-Z0-9][a-zA-Z0-9'\.-]+)*\s+(?:road|street|st\.|avenue|ave|highway|nh-\d+|nh\d+|sh-\d+|sh\d+|expressway|salai|marg|lane|bypass))\b",
                    re.IGNORECASE,
                ),
            ),
            (
                LocationEntityType.LANDMARK,
                re.compile(
                    r"\b(?:near|at|opposite|behind|next to|facing)?\s*"
                    r"([A-Z0-9][a-zA-Z0-9'\.-]+(?:\s+[A-Z0-9][a-zA-Z0-9'\.-]+)*\s+(?:railway\s*station|train\s*station|hospital|school|college|university|park|market|mall|temple|church|mosque|post\s*office|stadium|complex))\b",
                    re.IGNORECASE,
                ),
            ),
            (
                LocationEntityType.LOCALITY,
                re.compile(
                    r"\b(?:in|at|near)?\s*"
                    r"([A-Z0-9][a-zA-Z0-9'\.-]+(?:\s+[A-Z0-9][a-zA-Z0-9'\.-]+)*\s+(?:nagar|colony|layout|extension|extn|sector|block|puram|pally|wadi|pet|bazaar|giri|town))\b",
                    re.IGNORECASE,
                ),
            ),
            (
                LocationEntityType.AREA,
                re.compile(
                    r"\b(?:in|near|at)\s+([A-Z][a-zA-Z0-9'\.-]+(?:\s+[A-Z][a-zA-Z0-9'\.-]+)*\s+area)\b",
                    re.IGNORECASE,
                ),
            ),
        ]

    def extract_locations(self, text: str) -> List[LocationMention]:
        """Extract location mentions from text string.

        Args:
            text: Cleaned or raw complaint text.

        Returns:
            List of LocationMention Pydantic models.
        """
        if not text or not text.strip():
            return []

        mentions: List[LocationMention] = []
        occupied_spans: List[Tuple[int, int]] = []

        for entity_type, pattern in self._patterns:
            for match in pattern.finditer(text):
                # Target group 1 if present, otherwise full match
                extracted_str = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                extracted_str = extracted_str.strip()

                if len(extracted_str) < 3:
                    continue

                start, end = match.span(1) if match.lastindex and match.lastindex >= 1 else match.span()

                # Avoid adding overlapping text spans
                if any(not (end <= s or start >= e) for s, e in occupied_spans):
                    continue

                occupied_spans.append((start, end))
                mentions.append(
                    LocationMention(
                        text=extracted_str,
                        type=entity_type,
                        start_idx=start,
                        end_idx=end,
                    )
                )

        # Sort mentions by start index in original text
        mentions.sort(key=lambda m: m.start_idx if m.start_idx is not None else 0)
        return mentions
