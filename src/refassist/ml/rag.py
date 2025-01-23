from typing import List, Optional
from pathlib import Path

from llama_index.core import SimpleDirectoryReader, Document
from refassist.ml.vectordb import VectorDB
from refassist.log import logger


class RAGService:
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            # Figure out a better place for this
            db_path = Path(__file__).parent / "app.db"
        self.vector_db = VectorDB(db_path)

    def initialize(self, documents_path: str, in_memory: bool = False) -> None:
        """Initialize the RAG service with documents."""
        try:
            # Connect to vector database
            self.vector_db.connect(in_memory=in_memory)

            # Load documents
            documents = self._load_documents(documents_path)

            # Process documents and create embeddings
            # Split to save on processing if we're just
            # doing it in memory
            if in_memory:
                self.vector_db.process_documents_memory(documents)
                self.vector_db.close()
            else:
                self.vector_db.process_documents(documents)
                self.vector_db.create_embeddings()

        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")
            raise

    def query(self, query_text: str, top_k: int = 5) -> List[dict]:
        """Query the RAG system with a question."""
        try:
            rag_matches = self.vector_db.rag_query(
                query_text=query_text, top_k=top_k, similarity_threshold=0.7
            )
            doc_ids = list(set(match["doc_id"] for match in rag_matches))

            return self.vector_db.retrieve_rag_docs(doc_ids)

        except Exception as e:
            logger.error(f"Failed to query RAG system: {e}")
            raise

    @staticmethod
    def _load_documents(documents_path: str) -> List[Document]:
        """Load documents from the specified path."""
        try:
            reader = SimpleDirectoryReader(
                documents_path, required_exts=[".md"], recursive=True
            )
            return reader.load_data()
        except Exception as e:
            logger.error(f"Failed to load documents: {e}")
            raise

    def close(self) -> None:
        """Close the vector database connection."""
        try:
            self.vector_db.close()
        except Exception as e:
            logger.error(f"Failed to close RAG service: {e}")
            raise
