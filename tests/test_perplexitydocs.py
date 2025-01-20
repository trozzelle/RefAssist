from PerplexityDocs.main import main


def test_hello_world() -> None:
    if hello_world() != "Hello World":
        raise ValueError('Expected value to be "Hello World"')
