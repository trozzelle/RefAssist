from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PerplexityResponse:
    """Container model for response from Perplexity API."""

    content: str
    citations: List[str]
    usage: Dict[str, int]
