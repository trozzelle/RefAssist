from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Document:
    content: str
    path: Path
    metadata: Dict[str, Any]
