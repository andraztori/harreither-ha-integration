"""API exceptions for the Harreither integration."""

from __future__ import annotations


class HarrieitherClientError(Exception):
    """Exception to indicate a general API error."""


class HarrieitherClientCommunicationError(
    HarrieitherClientError,
):
    """Exception to indicate a communication error."""


class HarrieitherClientAuthenticationError(
    HarrieitherClientError,
):
    """Exception to indicate an authentication error."""
