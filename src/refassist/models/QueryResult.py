from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class QueryResult:
    answer: str
    sources: List[str]
    code_examples: List[str]
