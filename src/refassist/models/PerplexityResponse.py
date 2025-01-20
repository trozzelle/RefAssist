from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PerplexityResponse:
    """Container model for response from Perplexity API."""

    content: str
    citations: List[str]
    usage: Dict[str, int]
