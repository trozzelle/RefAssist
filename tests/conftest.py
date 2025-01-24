import pytest
from pathlib import Path
from typing import List
from unittest.mock import Mock
import tempfile
import os

from refassist.models import Document, PerplexityResponse, QueryResult
from refassist.client import PerplexityClient
from refassist.query import QueryHandler


# Using tempfile to create ephemeral test files
# to keep test_data/ clear for real documentation
@pytest.fixture
def temp_docs_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        test_doc = "# Test Document\nThis is test documentation."
        Path(temp_dir, "test1.md").write_text(test_doc)
        Path(temp_dir, "test2.md").write_text(test_doc)
        Path(temp_dir, "sub_directory").mkdir()
        Path(temp_dir, "sub_directory", "test1.md").write_text(test_doc)
        yield temp_dir


@pytest.fixture
def temp_bad_filetypes_directory():
    with tempfile.TemporaryDirectory() as temp_dir:
        test_doc = "# Test Document\nThis is test documentation."
        Path(temp_dir, "test1.abc").write_text(test_doc)
        yield temp_dir


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
