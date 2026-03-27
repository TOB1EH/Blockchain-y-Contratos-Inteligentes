#!/usr/bin/env python3
"""API server para sellado de archivos en una blockchain simulada."""

import os
import re
from os import listdir
from hashlib import sha256

from flask import Flask, current_app, json, jsonify, request

app = Flask(__name__)

HASH_PATTERN = re.compile(r"0x[0-9a-fA-F]{64}$")


def is_valid_hash(string):
    """Valida que el string sea un hash SHA-256 en formato hexadecimal con prefijo '0x'."""
    return isinstance(string, str) and re.match(HASH_PATTERN, string)


class StamperException(Exception):
    """Excepción personalizada para errores relacionados con el proceso de sellado."""


class Stamper:
    """Clase que simula el proceso de sellado de archivos en una blockchain."""

    def __init__(self, address):
        self.block_number = 0
        self.database = {}
        self.address = address

    def stamp(self, hash_value):
        """Registra un hash en la "blockchain" simulada, incrementando el número de bloque."""
        self.block_number += 1
        if not is_valid_hash(hash_value):
            raise StamperException("Invalid hash format")
        if hash_value in self.database:
            raise StamperException("Hash is already stamped")
        self.database[hash_value] = {
            "signer": self.address,
            "blockNumber": self.block_number,
        }
        return sha256(
            f"{self.address}{self.block_number}{hash_value}".encode()
        ).hexdigest()

    def stamped(self, hash_value):
        """Devuelve la información de sellado para un hash dado, o None si no está sellado."""
        return self.database.get(hash_value)


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

    try:
        transaction_hash = stamper.stamp(hash_value)
        return (
            jsonify(transaction=transaction_hash, blockNumber=stamper.block_number),
            201,
        )
    except StamperException as exc:
        return jsonify(message=str(exc)), 400


def create_app():
    """Función de fábrica para crear la aplicación Flask y configurar la instancia de Stamper."""
    keystore_dir = os.path.expanduser("~/.ethereum/keystore")
    keystore = [os.path.join(keystore_dir, f) for f in sorted(listdir(keystore_dir))]
    with open(keystore[0], encoding="ascii") as f:
        sender = f"0x{json.load(f)['address']}"

    app.config["stamper"] = Stamper(sender)  # <- inyección de dependencia
    return app


if __name__ == "__main__":
    create_app()
    app.run(debug=True)
