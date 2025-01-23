from typing import Optional, List
import torch
import duckdb
from duckdb import DuckDBPyConnection
from duckdb.typing import DuckDBPyType
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter

from refassist.log import logger

ARRAY_TYPE = DuckDBPyType(list[float])
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 200
MODEL_NAME = "BAAI/bge-small-en-v1.5"


class VectorDB:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.conn: Optional[DuckDBPyConnection] = None
        self.embed_model = self._setup_embedding_model()
        self.node_parser = self._setup_node_parser()
        self.device = "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"  # Nvidia GPUs
        elif torch.backends.mps.is_available():
            self.device = "mps"  # Apple Silicon / MLX

    def connect(self, in_memory: bool = False) -> None:
        """Connect to DuckDB instance"""
        try:
            if self.db_path is None or in_memory:
                self.conn = duckdb.connect(":memory:")
            else:
                self.conn = duckdb.connect(self.db_path)

            self._load_extension()
            self._initialize_schema()
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close(self) -> None:
        """Close connection to DuckDB instance"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _load_extension(self) -> None:
        """Load an extension into the DuckDB instance"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            self.conn.install_extension("vss")
            self.conn.load_extension("vss")
            self.conn.execute("SET GLOBAL hnsw_enable_experimental_persistence = true;")
        except Exception as e:
            logger.error(f"Failed to load VSS extension: {e}")
            raise

    def _initialize_schema(self) -> None:
        """Initialize the RAG schema"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            # Create documents table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INT PRIMARY KEY,
                    file TEXT,
                    text TEXT
                );
            """)

            # Create chunks table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id INT PRIMARY KEY,
                    doc_id INT,
                    chunk_text TEXT,
                    chunk_index INT,
                    FOREIGN KEY(doc_id) REFERENCES documents(id)
                );
            """)

            # Create embeddings table
            self.conn.execute(f"""
                CREATE TABLE IF NOT EXISTS embeddings (
                    chunk_id INT,
                    embedding {ARRAY_TYPE},
                    FOREIGN KEY (chunk_id) REFERENCES chunks(id)
                );
            """)
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    def _setup_embedding_model(self) -> HuggingFaceEmbedding:
        """Set up vector embedding model"""
        return HuggingFaceEmbedding(
            model_name=MODEL_NAME,
            device=self.device,
        )

    @staticmethod
    def _setup_node_parser() -> SentenceSplitter:
        """Set up tokenizer"""
        return SentenceSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separator=" ",
            paragraph_separator="\n\n",
        )

    def process_documents(self, documents: List[Document]) -> None:
        """Process documents into chunks"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            for i, doc in enumerate(documents):
                self.conn.execute(
                    "INSERT INTO documents (id, file, text) VALUES (?, ?, ?)",
                    [i, str(doc.metadata.get("file_path", "")), doc.text],
                )

                nodes = self.node_parser.get_nodes_from_documents([doc])

                for chunk_idx, node in enumerate(nodes):
                    self.conn.execute(
                        """
                        INSERT INTO chunks (id, doc_id, chunk_text, chunk_index)
                        VALUES (( SELECT COALESCE(MAX(id), -1) + 1 FROM chunks), ?, ?, ?)
                    """,
                        [i, node.text, chunk_idx],
                    )

        except Exception as e:
            logger.error(f"Failed to process documents: {e}")
            raise

    def create_embeddings(self) -> None:
        """Generate embeddings from chunked documents"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            chunks = self.conn.execute("SELECT id, chunk_text FROM chunks").fetchall()

            for chunk_id, chunk_text in chunks:
                embedding = self.embed_model.get_text_embedding(chunk_text)
                self.conn.execute(
                    "INSERT INTO embeddings (chunk_id, embedding) VALUES (?, ?)",
                    [chunk_id, embedding],
                )
        except Exception as e:
            logger.error(f"Failed to create embeddings: {e}")
            raise

    def rag_query(
        self, query_text: str, top_k: int = 5, similarity_threshold: float = 0.0
    ) -> List[dict]:
        """ "Embed the prompt and return vector similarity matches"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            query_embedding = self.embed_model.get_text_embedding(query_text)

            results = self.conn.execute(
                """
                WITH top_matches AS (
                    SELECT
                        chunk_id,
                        array_inner_product(embedding::FLOAT[384], ?::FLOAT[384]) as similarity
                    FROM embeddings
                    ORDER BY similarity DESC
                    LIMIT ?
                )
                SELECT
                    c.id as chunk_id,
                    c.chunk_text,
                    c.chunk_index,
                    c.doc_id,
                    d.file,
                    d.text as full_doc_text,
                    m.similarity
                FROM top_matches m
                JOIN chunks c ON c.id = m.chunk_id
                JOIN documents d ON d.id = c.doc_id
                WHERE m.similarity >= ?
                ORDER BY m.similarity DESC
            """,
                [query_embedding, top_k, similarity_threshold],
            ).fetchall()

            return [
                {
                    "chunk_id": row[0],
                    "chunk_text": row[1],
                    "chunk_index": row[2],
                    "doc_id": row[3],
                    "file": row[4],
                    "document_text": row[5],
                    "similarity": row[6],
                }
                for row in results
            ]

        except Exception as e:
            logger.error(f"Failed to query database: {e}")
            raise

    def retrieve_rag_docs(self, doc_ids: List[str]) -> List[dict]:
        """Retrieve original documents to include in LLM query"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            results = self.conn.execute(
                """
                SELECT id, file, text FROM documents WHERE id IN ?""",
                [doc_ids],
            ).fetchall()

            return results

        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            raise
