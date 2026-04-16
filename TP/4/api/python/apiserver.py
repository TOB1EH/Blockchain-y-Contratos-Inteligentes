#!/usr/bin/env python3
"""API server para sellado de archivos en la blockchain BFA."""

import os
import re
import getpass
import json
import argparse
from os import listdir
# from hashlib import sha256

from flask import Flask, current_app, json, jsonify, request
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from eth_account.messages import encode_defunct

app = Flask(__name__)

HASH_PATTERN = re.compile(r"0x[0-9a-fA-F]{64}$")

def is_valid_hash(string):
    """Valida que el string sea un hash SHA-256 en formato hexadecimal con prefijo '0x'."""
    return isinstance(string, str) and re.match(HASH_PATTERN, string)

SIGNATURE_PATTERN = re.compile(r"0x[a-fA-F0-9]{130}$")

def is_valid_signature(string):
    """Valida que el string sea una firma ECDSA de 65 bytes en hex con prefijo '0x'."""
    return isinstance(string, str) and re.match(SIGNATURE_PATTERN, string)


class StamperException(Exception):
    """Excepción personalizada para errores relacionados con el proceso de sellado."""


class Stamper:
    """Clase que interactúa con el contrato de sellado en la blockchain BFA."""

    def __init__(self, w3, account, contract, private_key):
        self.w3 = w3
        self.account = account
        self.contract = contract
        self.private_key = private_key

    def stamp(self, hash_value: str, signature: str = None):
        """
        Registra un hash. Si se proporciona firma, usa stampSigned.
        Retorna dict con 'transaction' (hash de tx) y 'blockNumber'.
        Lanza StamperException si falla.
        """

        # Validar formato del hash
        if not is_valid_hash(hash_value):
            raise StamperException("Invalid hash format")

        # Verificar que el hash no este registrado
        if self.stamped(hash_value) is not None:
            raise StamperException("Hash is already stamped")

        # Convertir el hash (string con '0x') a bytes32
        hash_bytes = bytes.fromhex(hash_value[2:]) # Eliminar '0x' y convertir a bytes

        # Si se paso una firma por parametro, usar stampSigned
        if signature:
            # Validar formato de la firma
            if not is_valid_signature(signature):
                raise StamperException("Invalid signature format")

            # Convertir la firma de hex a bytes
            signature_bytes = bytes.fromhex(signature[2:]) # Eliminar '0x'

            # Verificar que la firma sea válida para el hash dado
            # recuperando la dirección del firmante
            try:
                message = encode_defunct(hexstr=hash_value)

                # Usar signature_bytes en lugar del string de la firma para recuperar la dirección
                recovered = self.w3.eth.account.recover_message(message, signature=signature_bytes)
                # recovered = Account.recover_message(message, signature_bytes)
                if recovered == "0x" + "0" * 40:
                    raise StamperException("Invalid signature (zero address)")
            except Exception as e:
                raise StamperException(f"Invalid signature: {str(e)}") from e

            # Crear la transacción usando stampSigned en lugar de stamp
            tx_function = self.contract.functions.stampSigned(hash_bytes, signature_bytes)
        # Si no se paso una firma, usar stamp
        else:
            tx_function = self.contract.functions.stamp(hash_bytes)

        # Construir la transacción
        try:
            tx = tx_function.build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                # 'gas': 100000,  # Estimación de gas
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
        except Exception as e:
            raise StamperException(f"Error building transaction: {str(e)}") from e

        # Firmar la transacción
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)

        # Enviar la transaccion firmada
        try:
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        except Exception as e:
            raise StamperException(f"Error sending transaction: {str(e)}") from e

        # Esperar el recibo de la transaccion para obtener el número de bloque y confirmar exito
        try:
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        except Exception as e:
            raise StamperException(f"Error waiting for transaction receipt: {str(e)}") from e

        # Verificar el status de la transacción para confirmar que se ejecutó correctamente
        if receipt.status != 1:
            raise StamperException("Transaction reverted (unknown reason)")

        return {
            # "transaction": tx_hash.hex(),
            "transaction": receipt.transactionHash.hex(),
            "blockNumber": receipt.blockNumber
        }


    def stamped(self, hash_value: str):
        """
        Consulta si un hash ya fue registrado.
        Retorna dict con 'signer' y 'blockNumber', o None si no existe.
        """
        # Validar formato del hash
        if not is_valid_hash(hash_value):
            raise StamperException("Invalid hash format")

        # Convertir el hash de string a bytes32
        hash_bytes = bytes.fromhex(hash_value[2:]) # Eliminar '0x' y convertir a bytes

        # Llamar al contrato para obtener la información del hash
        result = self.contract.functions.stamped(hash_bytes).call()

        # signer = result[0]
        # block_number = result[1]

        # El contrato devuelve una tupla (address signer, uint256 blockNumber)
        signer, block_number = result

        # Si el signer es la dirección cero, significa que no está registrado
        if signer == "0x" + "0" * 40:
            return None

        return {
            "signer": signer,
            "blockNumber": block_number
        }


@app.get("/stamped/<hash_value>")
def stamped(hash_value):
    """Endpoint para verificar si un hash ya ha sido sellado y obtener su información."""
    stamper = current_app.config["stamper"]
    if is_valid_hash(hash_value):
        stamped_data = stamper.stamped(hash_value)
        if stamped_data:
            return jsonify(stamped_data), 200
        return jsonify(message="Hash not found"), 404
    return jsonify(message="Invalid hash format"), 400


@app.post("/stamp")
def stamp():
    """Endpoint para sellar un hash, registrándolo en la "blockchain" simulada."""
    stamper = current_app.config["stamper"]

    if request.mimetype != "application/json":
        return jsonify(message=f"Invalid message mimetype: '{request.mimetype}'"), 400

    req = request.get_json(silent=True)
    if req is None:
        return jsonify(message="Request body is not a valid JSON"), 400

    hash_value = req.get("hash")
    if not is_valid_hash(hash_value):
        return jsonify(message="Invalid hash format"), 400

    signature = req.get("signature")
    if signature is not None and not is_valid_signature(signature):
        return jsonify(message="Invalid signature format"), 400

    stamped_data = stamper.stamped(hash_value)
    if stamped_data:
        return (
            jsonify(
                message="Hash is already stamped",
                signer=stamped_data["signer"],
                blockNumber=stamped_data["blockNumber"],
            ),
            403,
        )

    # Sellar el hash usando el método stamp del Stamper, pasando la firma si se proporcionó
    try:
        result = stamper.stamp(hash_value, signature)
        return (
            jsonify(transaction=result["transaction"], blockNumber=result["blockNumber"]),
            201,
        )
    except StamperException as exc:
        return jsonify(message=str(exc)), 400


def create_app():
    """Función de fábrica para crear la aplicación Flask y configurar la instancia de Stamper."""

    # Leer el keystore para obtener la cuenta y clave privada
    keystore_dir = os.path.expanduser("~/.ethereum/keystore")
    keystore = [os.path.join(keystore_dir, f) for f in sorted(listdir(keystore_dir))]

    with open(keystore[0], encoding="ascii") as f:
        encrypted_key = f.read()

    # Pedir contraseña y desifrar la cuenta
    password = os.environ.get("STAMPER_PASSWORD")
    if password is None:
        password = getpass.getpass("Ingrese la contraseña de tu cuenta de Ethereum: ")
    try:
        private_key = Account.decrypt(encrypted_key, password)
    except ValueError:
        print("Contraseña incorrecta. No se pudo descifrar la clave privada.")
        exit(1)

    # Conectar al nodo local via IPC
    ipc_path = os.path.expanduser("~/blockchain-iua/bfatest/node/geth.ipc")
    w3 = Web3(Web3.IPCProvider(ipc_path))

    if not w3.is_connected():
        print("Error: No se pudo conectar al nodo IPC en", ipc_path)
        exit(1)

    # Crear la cuenta a partir de la clave privada
    # para realizar las transacciones
    account = w3.eth.account.from_key(private_key)
    print(f"Cuenta cargada: {account.address}")

    # Inyectar el middleware necesario para la compatibilidad con BFA
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    # Cargar ABI y dirección del contrato desde el archivo de configuración
    with open("./../../Stamper.json", encoding="utf-8") as f:
        config = json.load(f)

    abi = config["abi"]
    contract_address = config["networks"]["55555000000"]["address"]
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Inyectar dependencias a la app
    app.config["stamper"] = Stamper(w3, account, contract, private_key)
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Servidor API Stamper")
    parser.add_argument("--password-file", help="Archivo con la contraseña de la cuenta Ethereum")
    args = parser.parse_args()

    # Si se proporcionó un archivo de contraseña, leerlo y establecer la variable de entorno
    if args.password_file:
        try:
            with open(args.password_file, "r", encoding="utf-8") as f:
                password = f.read().strip()
            os.environ["STAMPER_PASSWORD"] = password
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo {args.password_file}")
            exit(1)

    create_app()
    app.run(debug=True)
