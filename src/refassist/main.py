from dotenv import dotenv_values
import asyncio
import typer
from typing import Optional
from pathlib import Path
import os
from rich.console import Console
from rich.logging import RichHandler
from rich.prompt import Prompt
from rich import print as rprint

from refassist.client import PerplexityClient
from refassist.loader import DocumentLoader
from refassist.query import QueryHandler
from refassist.logging import logger

app = typer.Typer()
console = Console()


async def interactive_mode(query_handler: QueryHandler):

    while True


def main() -> None:



if __name__ == "__main__":
    main()
