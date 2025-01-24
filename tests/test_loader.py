import pytest
from pathlib import Path
from refassist.loader import DocumentLoader
from tests.conftest import temp_docs_directory, temp_bad_filetypes_directory


def test_load_documentation_single_file(temp_docs_directory):
    file_path = Path(temp_docs_directory) / "test1.md"
    docs = DocumentLoader.load_documentation(file_path)
    assert len(docs) == 1
    assert docs[0].path == file_path
    assert "Test Document" in docs[0].content
    assert "This is test documentation" in docs[0].content


def test_load_documentation_directory(temp_docs_directory):
    docs = DocumentLoader.load_documentation(temp_docs_directory)
    assert len(docs) == 3
    assert all(doc.path.suffix == ".md" for doc in docs)


def test_load_documentation_unsupported_file(temp_bad_filetypes_directory):
    file_path = Path(temp_bad_filetypes_directory) / "test1.abc"
    with pytest.raises(ValueError, match="is not supported"):
        DocumentLoader.load_documentation(file_path)


def test_load_documentation_nonexistent_file():
    with pytest.raises(FileNotFoundError):
        DocumentLoader.load_documentation("nonexistent.md")
