#!/usr/bin/env python
"""Obtiene el número de bloque actual de la red Ethereum.
Por simplicidad, este código *no maneja errores*. Una implementación
real debería manejar errores de conexión y otros problemas.
Este script asume que hay un nodo de Ethereum en ejecución en el puerto 8545.
"""

from typing import List, Any

import requests

# Este script asume que hay un nodo de Ethereum en ejecución en el puerto 8545
RPC_PORT = 8545
RPC_HOST = "localhost"


def rpcreq(method: str, params: List) -> Any:
    """Realiza una llamada RPC a un nodo de Ethereum"""
    session = requests.Session()
    payload = {
        "jsonrpc": "2.0", 
        "method": method, 
        "params": params, 
        "id": 1
        }
    headers = {"Content-type": "application/json"}
    response = session.post(
        f"http://{RPC_HOST}:{RPC_PORT}", json=payload, headers=headers
    )
    return response.json()["result"]


def get_block_number() -> int:
    """Returns the current number of the Ethereum blockchain."""
    block_number = rpcreq("eth_blockNumber", [])
    return int(block_number, 16)


if __name__ == "__main__":
    print(get_block_number())
