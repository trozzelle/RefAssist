from typing import List, Union
from pathlib import Path
from refassist.log import logger
from refassist.models import Document


class DocumentLoader:
    SUPPORTED_EXTENSIONS = {".md", ".txt", ".rst"}

    @staticmethod
    def load_documentation(path: Union[str, Path]) -> List[Document]:
        path = Path(path)

        if not path.exists():
            logger.error(f"File {path} does not exist")
            raise FileNotFoundError(f"File {path} does not exist")

        documents: List[Document] = []

        if path.is_file():
            if path.suffix in DocumentLoader.SUPPORTED_EXTENSIONS:
                documents.append(DocumentLoader._load_file(path))
            else:
                raise ValueError(f"File {path} is not supported")
        elif path.is_dir():
            for file_path in path.rglob("*"):
                if file_path.suffix in DocumentLoader.SUPPORTED_EXTENSIONS:
                    documents.append(DocumentLoader._load_file(file_path))

        if not documents:
            raise ValueError(f"No supported files found in {path}")

        return documents

    @staticmethod
    def _load_file(path: Path) -> Document:
        try:
            content = path.read_text(encoding="utf-8")
            return Document(
                content=content,
                path=path,
                metadata={"size": path.stat().st_size, "modified": path.stat().st_mtime},
            )
        except Exception as e:
            logger.error(f"Error loading file at {path}: {e}")
            raise
