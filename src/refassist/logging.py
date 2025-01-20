import sys
import os
from loguru import logger
from datetime import datetime
from typing import Union
from rich.logging import RichHandler


def get_logger(
    file_prefix: str = "",
    file_suffix: str = "",
    level: Union[str, int] = "DEBUG",
) -> logger:
    logger.remove()

    handlers = [{"sink": RichHandler(markup=True)}]
    logger.add(f"logs/{file_prefix}{{time:YYYYMMDD}}{file_suffix}.log", level=level)
    logger.configure(handlers=handlers)
    return logger


logger = get_logger()
