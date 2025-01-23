# RefAssist: Technical Documentation Assistant

A WIP CLI tool for querying technical documentation using Perplexity AI's Sonar LLM with RAG (Retrieval Augmented Generation) capabilities. I'm mostly using this to learn and experiment with different LLM and RAG approaches as well as building around them. Expect the code to be a better reference than a functional tool, at least in its current state.


## Features

- Query documentation using natural language
- RAG support using DuckDB and vector similarity search
- Support for Markdown, RST, and text files
- Code example extraction and highlighting
- Source citation tracking
- Optional in-memory or persistent vector database
- GPU acceleration support (CUDA and MPS)

`src/refassist/ml/notebooks/` contains some notebooks I've used to experiment with different RAG approaches.

## Installation

Requires Python 3.12.8 or higher.

```bash
git clone https://github.com/yourusername/refassist.git
cd refassist
uv sync --all-extras --dev
```


```bash
PERPLEXITY_API_KEY=your_api_key_here
```

## Usage

Basic usage:

```bash
python -m refassist.main --file /path/to/docs
```

With RAG enabled:

```bash
python -m refassist.main --file /path/to/docs --store-files
```

Options:
- `--file`: Path to documentation file or directory
- `--api-key`: Your Perplexity AI API key (optional if set in .env or $PERPLEXITY_API_KEY is set)
- `--store-files`: Enable RAG processing and storage
- `--in-memory`: Use ephemeral in-memory database
- `--db-path`: Custom path for persistent database storage

## Development

1. Install development dependencies:
```bash
uv sync --all-extras --dev
```

2. Run tests:
```bash
pytest tests --cov=src
```

3. Run pre-commit hooks:
```bash
pre-commit run --all-files
```

## Docker

Build and run with Docker:

```bash
docker build -t refassist .
docker run -it --env-file .env refassist
```
