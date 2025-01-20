from openai import OpenAI
from openai.types.chat import ChatCompletion

from refassist.models.PerplexityResponse import PerplexityResponse
from refassist.log import logger


class PerplexityClient:
    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(api_key=api_key, base_url="https://api.perplexity.ai")

        self.model = "llama-3.1-sonar-small-128k-online"

    async def query_document(
        self, query: str, context: str, temperature: float = 0.2
    ) -> PerplexityResponse:
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a technical documentation assistant. "
                        "Provide clear, accurate responses based on the "
                        "provided documentation context. Include relevant "
                        "code examples when appropriate."
                    ),
                },
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"},
            ]

            response: ChatCompletion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                top_p=0.9,
            )

            return PerplexityResponse(
                content=response.choices[0].message.content,
                citations=response.model_extra.citations
                if hasattr(response.model_extra, "citations")
                else [],
                usage=response.usage.model_dump(),
            )

        except Exception as e:
            logger.error(f"Perplexity query failed: {str(e)}")
            raise
