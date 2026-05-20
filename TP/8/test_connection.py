"""
Script de prueba para verificar la conexión a la blockchain y al contrato
CFPFactory desplegado en el TP7.
"""

import os, json
from web3 import Web3

ABI_DIR = "../7/artifacts/contracts/CFPFactory.sol/CFPFactory.json"

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
print("Conectado:", w3.is_connected())
print("Bloque actual:", w3.eth.block_number)

factory_address = os.environ["CFP_FACTORY_ADDRESS"]
print("Factory address:", factory_address)

# Cargar ABI
with open(ABI_DIR, encoding="utf-8") as f:
    abi = json.load(f)["abi"]

factory = w3.eth.contract(
    address=Web3.to_checksum_address(factory_address),
    abi=abi
)

print("Owner:", factory.functions.owner().call())
