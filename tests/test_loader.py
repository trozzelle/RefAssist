import pytest
from pathlib import Path
from refassist.loader import DocumentLoader


def load_single_markdown_file(test_data_dir):
    file_path = test_data_dir / Path("test.md")
    documents = DocumentLoader.load_documentation(file_path)

    assert len(documents) == 1
    assert documents[0].path == file_path
    assert documents[0].content.startswith("# Test")
