import logging

logger = logging.getLogger(__package__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    fmt="[{asctime} {name}] {levelname}: {message}",
    datefmt=logging.Formatter.default_time_format,
    style="{",
    validate=True,
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)
logger.propagate = False