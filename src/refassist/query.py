from typing import List, Dict, Optional
import asyncio
from refassist.models import QueryResult, Document
from refassist.client import PerplexityClient
from refassist.ml.rag import RAGService
from refassist.log import logger


class QueryHandler:
    def __init__(
        self,
        client: PerplexityClient,
        documents: List[Document],
        db_path: Optional[str] = None,
    ) -> None:
        self.client = client
        self.documents = documents
        self.rag_service = RAGService(db_path)

    async def initialize(self, documents_path: str) -> None:
        try:
            self.rag_service.initialize(documents_path)
        except Exception as e:
            logger.error(f"Failed to initialize rag service: {e}")
            raise

    def _extract_code_examples(self, text: str) -> List[str]:
        code_blocks = []
        lines = text.splitlines()
        in_code_block = False
        current_block = []

        for line in lines:
            if line.startswith("```"):
                if in_code_block:
                    if current_block:
                        code_blocks.append("\n".join(current_block))
                        current_block = []
                    in_code_block = False
                else:
                    in_code_block = True
            elif in_code_block:
                current_block.append(line)

        return code_blocks

    async def process_query(
        self, query: str, *, code_examples: bool = False
    ) -> QueryResult:
        try:
            rag_results = self.rag_service.query(query)

            context = "\n\n".join(result["text"] for result in rag_results)

            if code_examples:
                query = f"Please provide code examples for {query}"

            response = await self.client.query_document(query=query, context=context)

            code_examples = self._extract_code_examples(response.content)

            sources = [
                str(doc.path)
                for doc in self.documents
                if any(citation in doc.content for citation in response.citations)
            ]

            return QueryResult(
                answer=response.content,
                sources=sources,
                code_examples=code_examples,
            )
        except Exception as e:
            logger.error(f"Error processing query: {query}: {e}")
            raise

    def close(self) -> None:
        try:
            self.rag_service.close()
        except Exception as e:
            logger.error(f"Failed to close RAG service: {e}")
            raise
