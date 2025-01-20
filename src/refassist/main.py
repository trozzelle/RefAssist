import asyncio
import typer
from typing_extensions import Annotated
import os
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich import print as rprint
from dotenv import dotenv_values

from refassist.client import PerplexityClient
from refassist.loader import DocumentLoader
from refassist.query import QueryHandler
from refassist.log import logger

config = dotenv_values(Path(__file__).parent.parent.with_name(".env"))

console = Console()


async def interactive_mode(query_handler: QueryHandler):
    while True:
        query = Prompt.ask(
            "\n[bold blue]Ask a question about the documentation"
            "[dim](or 'exit' to quit[/]"
        )

        if query.lower() in ("exit", "quit"):
            break

        code_example = "code" in query.lower() or "example" in query.lower()

        try:
            with console.status("[bold green]Processing query..."):
                result = await query_handler.process_query(
                    query, code_examples=code_example
                )

            rprint("\n[bold green]Query result:[/]")
            rprint(result.answer)

            if result.code_examples:
                rprint("\n[bold yellow]Code examples:[/]")
                for i, example in enumerate(result.code_examples, start=1):
                    rprint(f"{i}. {example}")
                    rprint(example)

            if result.sources:
                rprint("\n[bold yellow]Sources:[/]")
                for source in result.sources:
                    rprint(f"- {source}")

        except Exception as e:
            logger.error(f"Error: {e}")
            rprint("\n[bold red]An error occurred. Please try again.[/]")


def main(
    file: Annotated[str, typer.Option(help="Path to a file or directory.")] = "",
    api_key: Annotated[str, typer.Option(help="Your Perplexity AI API key.")] = "",
) -> None:
    api_key = api_key or os.getenv("PERPLEXITY_API_KEY") or config["PERPLEXITY_API_KEY"]

    if not api_key:
        raise typer.BadParameter("API key is required")

    if not file:
        raise typer.BadParameter("File or directory is required")

    try:
        with console.status("[bold green]Loading documentation...[/]"):
            documents = DocumentLoader.load_documentation(path=file)

        rprint(f"\n[bold green]Loaded {len(documents)} documents.[/]")

        client = PerplexityClient(api_key)
        query_handler = QueryHandler(client, documents)

        rprint("\n[bold]Welcome to the Documentation Assistant![/bold]")
        rprint("Ask questions about the documentation or type 'exit' to quit.")

        asyncio.run(interactive_mode(query_handler))

    except Exception as e:
        logger.error(f"Error: {e}")
        raise typer.Exit(1)


if __name__ == "__main__":
    typer.run(main)
