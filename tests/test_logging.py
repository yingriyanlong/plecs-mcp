import logging

from plecs_mcp.logging_setup import configure, get_logger


def test_logging_configures():
    configure()
    lg = get_logger()
    assert lg.name == "plecs_mcp"
    assert lg.handlers  # at least the stderr handler
    assert lg.propagate is False
