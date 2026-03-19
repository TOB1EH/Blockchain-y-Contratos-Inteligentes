#!/usr/bin/env python3
"""Obtiene el número de bloque actual de la red Ethereum"""

# Importa el módulo web3 y trata de autodetectar una red. Para que funcione, tiene
# que haber un nodo de Ethereum en ejecución en el puerto 8545.
from web3.auto import w3
# Importa el middleware para redes PoA. Este middleware es necesario para conectarse
# a redes PoA como la BFA.
from web3.middleware import geth_poa_middleware
w3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Imprime el número de bloque actual de la red Ethereum
# No hay control de errores, por lo que si no hay un nodo de Ethereum en ejecución
# en el puerto 8545, el programa fallará.
print(w3.eth.block_number)
