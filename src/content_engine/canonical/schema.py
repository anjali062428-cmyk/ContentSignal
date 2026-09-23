"""
Canonical Schema Definition.
Declares standard canonical fields for normalized content intelligence analysis.
Not all datasets require every canonical slot; each dataset exposes its available capabilities.
"""
from typing import Dict, Any, List

CANONICAL_SLOTS = [
    "canonical_record_id",
    "canonical_title",
    "canonical_content_type",
    "canonical_date",
    "canonical_visibility",
    "canonical_engagement",
    "canonical_conversion",
    "canonical_search_visibility",
    "canonical_position",
    "canonical_ctr",
    "canonical_freshness",
    "canonical_text_length",
    "canonical_outcome",
]

CANONICAL_METADATA = {
    "canonical_record_id": {"description": "Primary unique identifier for the content item/page/post", "type": "string"},
    "canonical_title": {"description": "Content headline, title, or label", "type": "string"},
    "canonical_content_type": {"description": "Type/format of content (e.g. blog, video, status, photo)", "type": "string"},
    "canonical_date": {"description": "Creation, publication, or post date", "type": "datetime"},
    "canonical_visibility": {"description": "Overall exposure (impressions, reach, views, sessions)", "type": "numeric"},
    "canonical_engagement": {"description": "Audience interactions (likes, shares, comments, claps, engaged sessions)", "type": "numeric"},
    "canonical_conversion": {"description": "Commercial conversion (leads, sales, paid flag, revenue)", "type": "numeric"},
    "canonical_search_visibility": {"description": "Organic search exposure (search volume, organic impressions, clicks)", "type": "numeric"},
    "canonical_position": {"description": "Search ranking position (1 is top rank)", "type": "numeric"},
    "canonical_ctr": {"description": "Click-through rate (percentage or ratio)", "type": "numeric"},
    "canonical_freshness": {"description": "Days since last update, edit, or publication", "type": "numeric"},
    "canonical_text_length": {"description": "Content length in words, characters, or tokens", "type": "numeric"},
    "canonical_outcome": {"description": "Primary optimization target or success indicator", "type": "numeric"},
}


class CanonicalRecord:
    def __init__(self, **kwargs):
        for slot in CANONICAL_SLOTS:
            setattr(self, slot, kwargs.get(slot, None))

    def to_dict(self) -> Dict[str, Any]:
        return {slot: getattr(self, slot, None) for slot in CANONICAL_SLOTS}
