#!/usr/bin/env python3
"""
API REST para interactuar con los contratos CFP y CFPFactory del trabajo Practico N°7.
"""

import os
import json
import re

from datetime import datetime, timezone
from flask import Flask, jsonify, request
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from eth_account.messages import encode_defunct

import messages

# Inicializar la aplicación Flask para definir los endpoints de la API
app = Flask(__name__)

# ----- Leer variables de entorno -----

# Credenciales y configuracion del nodo Ethereum y contratos
MNEMONIC        = os.environ["CFP_MNEMONIC"]
FACTORY_ADDRESS = os.environ["CFP_FACTORY_ADDRESS"]
RPC_URL         = os.environ.get("CFP_RPC_URL", "http://localhost:8545")
TP7_DIR         = os.environ.get("CFP_TP7_DIR", "../7")

# Direccion nula para comparar con direcciones no asignadas
ZERO = "0x0000000000000000000000000000000000000000"

# ----- Conectarse al nodo Ethereum -----
w3 = Web3(Web3.HTTPProvider(RPC_URL))
# In yectar compatibilidad para operar sobre redes locales
w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

# Habilitar el uso de funciones de HD Wallet en eth_account para derivar
# la cuenta del servidor a partir de una frase mnemotecnica (mnemonic)
Account.enable_unaudited_hdwallet_features()
server_account = Account.from_mnemonic(
    mnemonic=MNEMONIC,
    account_path="m/44'/60'/0'/0/0"
)

# Cargar ABI de los contratos desde los artefactos del TP7
def load_abi(contract_name):
    """Carga la ABI de un contrato desde los artefactos de Hardhat."""

    # Construir la ruta al archivo JSON del contrato y cargar la ABI
    path = os.path.join(
        TP7_DIR,
        "artifacts",
        "contracts",
        f"{contract_name}.sol",
        f"{contract_name}.json"
    )
    # El archivo JSON tiene la siguiente estructura:
    # {
    #     "abi": [...],
    #     "bytecode": "0x...",
    #     ...
    # }
    # Solo nos interesa la parte de "abi" para interactuar con los contratos desde el servidor
    with open(path, encoding="utf-8") as f:
        return json.load(f)["abi"]

# Cargar las ABIs de los contratos CFPFactory y CFP
cfp_factory_abi = load_abi("CFPFactory")
cfp_abi         = load_abi("CFP")

# Crear el objeto contrato de CFPFactory
cfp_factory = w3.eth.contract(
    # Formatear la direccion del contrato a checksum address para
    # evitar problemas de mayusculas/minusculas
    address=Web3.to_checksum_address(FACTORY_ADDRESS),
    abi=cfp_factory_abi
)

# Patrones de validacion
HASH_RE    = re.compile(r'^0x[0-9a-fA-F]{64}$')   # 32 bytes = 64 hex chars
ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')   # 20 bytes = 40 hex chars

def is_valid_hash(value):
    """
    Valida que el valor sea un hash hexadecimal de 32 bytes.
    (64 caracteres hexadecimales con prefijo '0x')
    """
    return isinstance(value, str) and bool(HASH_RE.match(value))

def is_valid_address(value):
    """
    Valida que el valor sea una dirección hexadecimal de 20 bytes
    (40 caracteres hexadecimales con prefijo '0x')
    """
    return isinstance(value, str) and bool(ADDRESS_RE.match(value))

def send_transaction(tx_function):
    """
    Construye, firma y envia una transaccion usando la cuenta del servidor.
    Espera la confirmacion y devuelve el recibo.
    """

    # Estructurar la transaccion con los parametros necesarios
    tx = tx_function.build_transaction({
        'from': server_account.address,
        'nonce': w3.eth.get_transaction_count(server_account.address),
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id,
    })

    # Firmar la transaccion con la clave privada del servidor
    signed = w3.eth.account.sign_transaction(tx, server_account.key)

    # Enviar la transaccion al nodo y esperar la confirmacion
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)

def get_cfp_contract(call_id_hex):
    """
    Dado un callId en hexadecimal, devuelve el objeto contrato CFP correspondiente.
    Lanza ValueError si la direccion no es valida o no corresponde a un contrato CFP.
    """

    # Convertir de hex string a bytes (removiendo '0x')
    call_id_bytes = bytes.fromhex(call_id_hex[2:])

    # Llamar a la funcion calls() del factory para obtener la direccion del contrato CFP
    call_data = cfp_factory.functions.calls(call_id_bytes).call()

    # La direccion del contrato CFP esta en la posicion 1 del tuple devuelto por calls()
    cfp_address = call_data[1]
    if cfp_address == ZERO:
        raise ValueError("No existe un contrato CFP para el callId proporcionado")

    # Crear y devolver el objeto contrato de CFP usando la direccion obtenida y la ABI de CFP
    return w3.eth.contract(
        address=Web3.to_checksum_address(cfp_address),
        abi=cfp_abi
    )

def err(msg, code):
    """
    Helper para devolver un error con un mensaje y codigo HTTP personalizados.
    """
    return jsonify(message=msg), code

# ----- Endpoints de solo lectura (GET) -----

@app.get("/contract-address")
def contract_address():
    """Devuelve la direccion del contrato CFPFactory."""
    return jsonify(address=FACTORY_ADDRESS)

@app.get("/contract-owner")
def contract_owner():
    """Devuelve el propietario del contrato CFPFactory."""

    try:
        owner = cfp_factory.functions.owner().call()
        return jsonify(address=owner)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/authorized/<address>")
def authorized(address):
    """Indica si la direccion esta autorizada en el contrato CFPFactory."""

    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)

    try:
        result = cfp_factory.functions.isAuthorized(
            # Convertir a checksum address para evitar problemas de mayusculas/minusculas
            Web3.to_checksum_address(address)
        ).call()
        return jsonify(authorized=result)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/calls/<call_id>")
def calls(call_id):
    """Devuelve la informacion de una llamada específica."""
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)

    try:
        call_id_bytes   = bytes.fromhex(call_id[2:])

        # Leer mapeo de contrato CFPFactory para obtener la direccion del contrato CFP
        # correspondiente al callId proporcionado
        call_data       = cfp_factory.functions.calls(call_id_bytes).call()
        cfp_creator     = call_data[0]
        cfp_address     = call_data[1]
        if cfp_address == ZERO:
            return err(messages.CALLID_NOT_FOUND, 404)
        return jsonify(creator=cfp_creator, cfp=cfp_address)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/closing-time/<call_id>")
def closing_time(call_id):
    """Devuelve el tiempo de cierre de la CFP correspondiente al callId proporcionado."""

    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)

    try:
        # Obtener el contrato CFP correspondiente al callId proporcionado
        cfp = get_cfp_contract(call_id)

        # Llamar a la funcion closingTime() del contrato CFP para obtener el timestamp de cierre
        cfp_closing_time = cfp.functions.closingTime().call()

        # Convertir el timestamp a formato legible (ISO 8601)
        closing_time_iso = datetime.fromtimestamp(cfp_closing_time, tz=timezone.utc).isoformat()
        return jsonify(closingTime=closing_time_iso)
    except ValueError:
        return err(messages.CALLID_NOT_FOUND, 404)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/proposal-data/<call_id>/<proposal>")
def proposal_data(call_id, proposal):
    """
    Devuelve la informacion de una propuesta específica dentro de un Contrato CFP
    determinada por callId.
    """

    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)
    if not is_valid_hash(proposal):
        return err(messages.INVALID_PROPOSAL, 400)

    try:
        # Encontrar el contrato CFP correspondiente al callId proporcionado
        cfp             = get_cfp_contract(call_id)
        proposal_bytes  = bytes.fromhex(proposal[2:])

        # Obtener los datos de la propuesta.
        data            = cfp.functions.proposalData(proposal_bytes).call()
        sender          = data[0]
        block_number    = data[1]
        timestamp       = data[2]

        if sender == ZERO:
            return err(messages.PROPOSAL_NOT_FOUND, 404)

        timestamp_iso   = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

        # Devolver la informacion de la propuesta en formato JSON
        return jsonify(
            sender=sender,
            blockNumber=block_number,
            timestamp=timestamp_iso
        )
    except ValueError:
        return err(messages.CALLID_NOT_FOUND, 404)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

# ----- Endpoints de escritura (POST) -----

@app.post("/register-proposal")
def register_proposal():
    """
    Registra una nueva propuesta para un llamado específico.
    """

    # Ejecuta la función de seguridad inicial de las rutas POST para
    # asegurar que la cabecera declare JSON; bloquea si devuelve nulidad.
    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    # Validar que se hayan proporcionado los campos necesarios
    call_id     = req.get("callId")
    proposal    = req.get("proposal")
    if call_id is None or proposal is None:
        return err(messages.MISSING_FIELD, 400)
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)
    if not is_valid_hash(proposal):
        return err(messages.INVALID_PROPOSAL, 400)

    try:
        # Verificar que el llamado existe
        call_id_bytes = bytes.fromhex(call_id[2:])
        proposal_bytes = bytes.fromhex(proposal[2:])
        call_data = cfp_factory.functions.calls(call_id_bytes).call()
        cfp_address = call_data[1]
        if cfp_address == ZERO:
            return err(messages.CALLID_NOT_FOUND, 404)

        # Verificar que la propuesta no esta registrada
        cfp = w3.eth.contract(
            address=Web3.to_checksum_address(cfp_address),
            abi=cfp_abi
        )
        data = cfp.functions.proposalData(proposal_bytes).call()
        if data[0] != ZERO:
            return err(messages.ALREADY_REGISTERED, 403)

        # Registrar la propuesta
        send_transaction(
            cfp_factory.functions.registerProposal(call_id_bytes, proposal_bytes)
        )
        return jsonify(message=messages.OK), 201

    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.post("/register")
def register():
    """
    Autoriza una nueva direccion para que pueda registrar propuestas en los contratos CFP.
     - El cliente debe enviar un JSON con los campos "address" y "signature".
     - La firma debe ser una firma Ethereum del mensaje que contiene la direccion del
     contrato CFPFactory usando la clave privada de la direccion que se quiere autorizar.
     - El servidor verifica que la firma sea valida y que la direccion recuperada de la firma
     coincida con la direccion declarada en el JSON.
     - Si la firma es valida, el servidor llama a la funcion authorize() del contrato
     CFPFactory para autorizar la direccion.
     - Esto asegura que solo el propietario de una direccion puede autorizarla, evitando que
     alguien
    """

    # Ejecuta la función de seguridad inicial de las rutas POST para asegurar que la cabecera
    # declare JSON; bloquea si devuelve nulidad.
    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    # Extrae la dirección y su firma digital enviadas para el proceso de autorización.
    address     = req.get("address")
    signature   = req.get("signature")
    if address is None or signature is None:
        return err(messages.MISSING_FIELD, 400)
    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)

    # Verificar la firma
    # El mensaje es la direccion del contrato (20 bytes)
    try:
        contract_bytes      = bytes.fromhex(FACTORY_ADDRESS[2:])
        signable_message    = encode_defunct(contract_bytes)
        recovered_address   = Account.recover_message(
            signable_message,
            signature=bytes.fromhex(signature[2:]) if signature.startswith("0x") else bytes.fromhex(signature)
        )
    except Exception:
        return err(messages.INVALID_SIGNATURE, 400)

    # La direccion recuperada debe coincidir con la declarada
    if recovered_address.lower() != address.lower():
        return err(messages.INVALID_SIGNATURE, 400)

    try:
        checksum_address = Web3.to_checksum_address(address)

        # Verificar que la direccion este ya autorizada
        if cfp_factory.functions.isAuthorized(checksum_address).call():
            return err(messages.ALREADY_AUTHORIZED, 403)

        # Autorizar la direccion llamando a la funcion authorize() del contrato CFPFactory
        send_transaction(
            cfp_factory.functions.authorize(checksum_address)
        )
        return jsonify(message=messages.OK), 200

    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.post("/create")
def create():
    """
    Crea un nuevo llamado CFP a partir de un callId y closingTime proporcionados por el cliente.
     - El cliente debe enviar un JSON con los campos "callId", "closingTime" y "signature".
     - La firma debe ser una firma Ethereum del mensaje que contiene el callId y el closingTime
     usando la clave privada de una direccion autorizada en el contrato CFPFactory.
     - El servidor verifica que la firma sea valida y que la direccion recuperada de la firma este
     autorizada para crear llamados.
     - Si la firma es valida, el servidor llama a la funcion createFor() del contrato CFPFactory
     para crear el llamado a nombre del firmante.
     - Esto asegura que solo las direcciones autorizadas pueden crear llamados, evitando que alguien
     cree llamados con callIds falsos o con tiempos de cierre invalidos.
     - El campo closingTime debe ser una fecha y hora en formato ISO 8601 y el servidor debe validar
     que sea una fecha futura antes de crear el llamado.
     - El mensaje que se firma para crear un llamado debe contener el callId y el closingTime, para
     evitar que alguien pueda reutilizar una firma valida para crear llamados con callIds o tiempos
     de cierre diferentes a los declarados en la firma.
     - El servidor debe validar que el callId tenga un formato valido (hash hexadecimal de 32 bytes)
     y que el closingTime tenga un formato valido (fecha y hora en formato ISO 8601) antes de
     intentar crear el llamado, para evitar gastar gas en transacciones que van a fallar por formato
     invalido.
    """

    # Ejecuta la función de seguridad inicial de las rutas POST para asegurar que la cabecera
    # declare JSON; bloquea si devuelve nulidad.
    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    call_id         = req.get("callId")
    closing_time    = req.get("closingTime")
    signature       = req.get("signature")
    if call_id is None or closing_time is None or signature is None:
        return err(messages.MISSING_FIELD, 400)
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)

    # Parsear el closingTime en fotmato ISO 8601
    try:
        # Convertir el string de tiempo de cierre a un objeto datetime
        closing_time_dt = datetime.fromisoformat(closing_time)

        # Convertir a timestamp Unix
        closing_time_ts = int(closing_time_dt.timestamp())
    except (ValueError, TypeError):
        return err(messages.INVALID_TIME_FORMAT, 400)

    # Validar que el tiempo de cierre sea en el futuro
    now = int(datetime.now(timezone.utc).timestamp())
    if closing_time_ts <= now:
        return err(messages.INVALID_CLOSING_TIME, 400)

    # Reconstruir el mensaje de 84 bytes y verificar la firma
    # 20 bytes (contrato) + 32 bytes (callId) + 32 bytes (closingTime)
    try:
        contract_bytes      = bytes.fromhex(FACTORY_ADDRESS[2:])
        call_id_bytes       = bytes.fromhex(call_id[2:])
        closing_time_bytes  = closing_time_ts.to_bytes(32, byteorder='big')
        message_bytes       = contract_bytes + call_id_bytes + closing_time_bytes

        signable_message    = encode_defunct(message_bytes)
        recovered_address   = Account.recover_message(
            signable_message,
            signature=bytes.fromhex(signature[2:]) if signature.startswith("0x") else bytes.fromhex(signature)
        )
    except Exception:
        return err(messages.INVALID_SIGNATURE, 400)

    try:
        checksum_creator = Web3.to_checksum_address(recovered_address)

        # Verificar que el llamado no exite ya
        call_data = cfp_factory.functions.calls(call_id_bytes).call()
        cfp_address = call_data[1]
        if cfp_address != ZERO:
            return err(messages.ALREADY_CREATED, 403)

        # Verificar que el firmante este autorizado para crear llamados
        if not cfp_factory.functions.isAuthorized(checksum_creator).call():
            return err(messages.UNAUTHORIZED, 403)

        # Crear el llamado a nombre del firmante
        send_transaction(
            cfp_factory.functions.createFor(
                call_id_bytes,
                closing_time_ts,
                checksum_creator
            )
        )
        return jsonify(message=messages.OK), 201
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)


def check_mimetype():
    """Valida que la solicitud tenga Content-Type application/json y devuelve el JSON parseado."""

    if request.mimetype != "application/json":
        return None
    return request.get_json(silent=True)

if __name__ == "__main__":
    app.run(debug=False, port="5000")
