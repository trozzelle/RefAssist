from typing import Optional, List, Set
import hashlib
import torch
import duckdb
from duckdb import DuckDBPyConnection
from duckdb.typing import DuckDBPyType
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from sympy.integrals.meijerint_doc import doc

from refassist.log import logger

ARRAY_TYPE = DuckDBPyType(list[float])
CHUNK_SIZE = 1024
CHUNK_OVERLAP = 200
MODEL_NAME = "BAAI/bge-small-en-v1.5"


class VectorDB:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.conn: Optional[DuckDBPyConnection] = None
        self.device = "cpu"
        if torch.cuda.is_available():
            self.device = "cuda"  # Nvidia GPUs
        elif torch.backends.mps.is_available():
            self.device = "mps"  # Apple Silicon / MLX
        self.embed_model = self._setup_embedding_model()
        self.node_parser = self._setup_node_parser()

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
            # Create sequences for primary key fields
            self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS doc_id_seq START 1;
            CREATE SEQUENCE IF NOT EXISTS chunk_id_seq START 1;
            CREATE SEQUENCE IF NOT EXISTS embed_id_seq START 1;""")

            # Create documents table
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INT PRIMARY KEY,
                    file TEXT,
                    text TEXT,
                    content_hash TEXT UNIQUE,
                    last_modified TIMESTAMP,
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

    @staticmethod
    def _compute_hash(text: str) -> str:
        """Compute hash of document content"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _get_existing_doc_hashes(self) -> Set[str]:
        """Get set of existing document hashes"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            results = self.conn.execute(
                """
                SELECT content_hash FROM documents
                """
            ).fetchall()
            return {row[0] for row in results}

        except Exception as e:
            logger.error(f"Failed to get existing document hashes: {e}")
            raise

    def _remove_old_data(self, doc_id: int) -> None:
        """Delete chunks and embeddings of a document"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            self.conn.execute(
                """
            DELETE FROM embeddings
            WHERE chunk_id IN (
            SELECT id FROM chunks WHERE doc_id = ?
            )""",
                [doc_id],
            )

            self.conn.execute(
                """"
            DELETE FROM chunks WHERE doc_id = ?""",
                [doc_id],
            )

        except Exception as e:
            logger.error(f"Failed to remove old data: {e}")
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

    def process_documents_memory(self, documents: List[Document]) -> None:
        """Process documents into chunks for in-memory database"""
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

    def create_embeddings_memory(self) -> None:
        """Generate embeddings from chunked documents for in-memory database"""
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

    def process_documents(self, documents: List[Document]) -> None:
        """Process documents for persistent database"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            # This might be backwards, it may be more efficient
            # to do this logic in the db
            existing_hashes = self._get_existing_doc_hashes()

            for doc in documents:
                content_hash = self._compute_hash(doc.text)
                file_path = str(doc.metadata.get("file_path", ""))
                last_modified = doc.metadata.get("last_modified", None)

                if content_hash in existing_hashes:
                    logger.info(f"Document {doc.text} has already been processed")
                    continue

                existing_doc = self.conn.execute(
                    """
                    SELECT id FROM documents WHERE file = ?""",
                    [file_path],
                ).fetchone()

                if existing_doc:
                    doc_id = existing_doc[0]
                    self._remove_old_data(doc.id)

                    doc_id = self.conn.execute(
                        """
                    UPDATE documents SET text = ?, content_hash = ?, last_modified = ?
                    WHERE id = ?
                    RETURNING id""",
                        [doc.text, content_hash, last_modified, doc_id],
                    ).fetchone()
                else:
                    doc_id = self.conn.execute(
                        """
                    INSERT INTO documents (id, file, text, content_hash, last_modified)
                    RETURNING id""",
                        [file_path, doc.text, content_hash, last_modified],
                    ).fetchone()

                nodes = self.node_parser.get_nodes_from_documents([doc])

                for chunk_idx, node in enumerate(nodes):
                    self.conn.execute(
                        """INSERT INTO chunks (id, doc_id, chunk_text, chunk_index)
                        VALUES (nextval('chunk_id_seq'), ?, ?, ?)""",
                        [doc_id, node.text, chunk_idx],
                    )

        except Exception as e:
            logger.error(f"Failed to process documents: {e}")
            raise

    def create_embeddings(self) -> None:
        """Create embeddings for persistent database"""
        if not self.conn:
            raise RuntimeError("Database connection not established")

        try:
            # We narrow to only the chunks that
            # don't already have an embedding
            chunks = self.conn.execute("""
            SELECT c.id, c.chunk_text
            FROM chunks c
            LEFT JOIN embeddings e ON c.id = e.chunk_id
            WHERE e.chunk_id IS NULL""").fetchall()

            if not chunks:
                logger.info(f"No chunks found for document {doc.text}")
                return

            logger.info(f"Creating embeddings for {len(chunks)} chunks")

            for chunk_id, chunk_text in chunks:
                embedding = self.embed_model.get_text_embedding(chunk_text)
                self.conn.execute(
                    """
                INSERT INTO embeddings (chunk_id, embedding) VALUES (?, ?)""",
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
