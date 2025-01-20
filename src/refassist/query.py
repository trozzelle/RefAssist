from typing import List, Dict
import asyncio
from refassist.models import QueryResult, Document
from refassist.client import PerplexityClient
from refassist.log import logger


class QueryHandler:
    def __init__(self, client: PerplexityClient, documents: List[Document]) -> None:
        self.client = client
        self.documents = documents
        self._context_cache: Dict[str, str] = {}

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
            context = "\n\n".join(doc.content for doc in self.documents)

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
