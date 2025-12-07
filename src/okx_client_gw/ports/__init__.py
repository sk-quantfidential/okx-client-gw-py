"""Port interfaces (Protocol classes) for dependency inversion."""

from okx_client_gw.ports.http_client import OkxHttpClientProtocol
from okx_client_gw.ports.ws_client import OkxWsClientProtocol

__all__ = [
    "OkxHttpClientProtocol",
    "OkxWsClientProtocol",
]
