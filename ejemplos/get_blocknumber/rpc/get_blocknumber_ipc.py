#!/usr/bin/env python
"""Obtiene el número de bloque actual de la red Ethereum.
Por simplicidad, este código *no maneja errores*. Una implementación
real debería manejar errores de conexión y otros problemas."
Este script asume que hay un nodo de Ethereum en ejecución"
y que el socket IPC está disponible en la ruta especificada."
"""

import json
import os
import socket
from typing import List, Any

# Este script asume que hay un nodo de Ethereum en ejecución
# y que el socket IPC está disponible en la ruta especificada
IPC_PATH = os.path.expanduser("~/blockchain-iua/bfatest/node/geth.ipc")


def rpcreq(method: str, params: List) -> Any:
    """Realiza una llamada RPC a un nodo de Ethereum"""
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(IPC_PATH)
        payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
        s.sendall(json.dumps(payload).encode("utf-8"))
        response = s.recv(4096)
        return json.loads(response.decode("utf-8"))["result"]


def get_block_number() -> int:
    """Devuelve el bloque actual de una red Ethereum."""
    block_number = rpcreq("eth_blockNumber", [])
    return int(block_number, 16)


if __name__ == "__main__":
    print(get_block_number())
