import pytest
from pathlib import Path
from typing import List
from unittest.mock import Mock

from refassist.models import Document, PerplexityResponse, QueryResult
from refassist.client import PerplexityClient
from refassist.query import QueryHandler


@pytest.fixture
def sample_document() -> Document:
    return Document(
        content="Test string",
        path="test.md",
        metadata={"size": 100, "modified": 1234567890},
    )


@pytest.fixture
def sample_documents(sample_document) -> List[Document]:
    return [sample_document]


@pytest.fixture
def mock_perplexity_response() -> PerplexityResponse:
    return PerplexityResponse(
        content="Test response with a ```code block```",
        citations=["citation 1", "citation 2"],
        usage={"prompt_tokens": 10, "completion_tokens": 10},
    )
