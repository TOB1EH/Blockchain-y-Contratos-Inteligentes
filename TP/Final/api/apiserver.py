#!/usr/bin/env python3
"""
API REST para interactuar con los contratos CFP y CFPFactory.
"""

import json
import logging
import os
import re
import rlp
from rlp.sedes import binary, List as RLPList

from datetime import datetime, timezone
from flask import Flask, jsonify, request
from flask import send_file
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data

import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

import messages
import database
import merkle
from event_listener import start_listener

import hashlib
from werkzeug.utils import secure_filename

# Directorio donde se guardarán los archivos subidos post-cierre
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configurar el logging para mostrar mensajes informativos en la consola
# durante la ejecucion del servidor
logging.basicConfig(level=logging.INFO)

# Inicializar la aplicación Flask para definir los endpoints de la API
app = Flask(__name__)

# ----- Leer variables de entorno -----

# Credenciales y configuracion del nodo Ethereum y contratos
MNEMONIC        = os.environ["CFP_MNEMONIC"]
FACTORY_ADDRESS = os.environ["CFP_FACTORY_ADDRESS"]
ADMIN_ADDRESS   = os.environ["CFP_ADMIN_ADDRESS"]
ENS_REGISTRY    = os.environ.get("CFP_ENS_REGISTRY", "")
ERC20_TOKEN     = os.environ.get("CFP_ERC20_TOKEN", "")
RPC_URL         = os.environ.get("CFP_RPC_URL", "http://localhost:8545")
CONTRACTS_DIR   = os.environ.get("CFP_CONTRACTS_DIR", "../contracts")
CFP_DB_PATH     = os.environ.get("CFP_DB_PATH", "cfp.db")

# Direccion nula para comparar con direcciones no asignadas
ZERO = "0x0000000000000000000000000000000000000000"

# ----- Conectarse al nodo Ethereum -----
w3 = Web3(Web3.HTTPProvider(RPC_URL))
w3.eth.default_block = 'pending' # para leer el estado más actualizado incluyendo transacciones pendientes
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
def load_abi(contract_name: str) -> list:
    """Carga la ABI de un contrato desde los artefactos de Hardhat."""

    # Resolver CONTRACTS_DIR dinamicamente en caso de usar ruta relativa por defecto "../contracts"
    if CONTRACTS_DIR.startswith("../"):
        resolved_dir = BASE_DIR.parent / CONTRACTS_DIR.lstrip("../")
    else:
        resolved_dir = Path(CONTRACTS_DIR)

    # Construir la ruta al archivo JSON del contrato y cargar la ABI
    path = os.path.join(
        str(resolved_dir),
        "artifacts",
        "contracts",
        f"{contract_name}.sol",
        f"{contract_name}.json"
    )

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

# Verificar que el servidor es el owner del contrato
on_chain_owner = cfp_factory.functions.owner().call()
if on_chain_owner.lower() != server_account.address.lower():
    raise SystemExit(
        f"El owner del contrato ({on_chain_owner}) no coincide con "
        f"la cuenta del servidor ({server_account.address})."
        "Verificá CFP_MNEMONIC y CFP_FACTORY_ADDRESS en las variables de entorno."
    )

# Cargar ABIs de contratos ENS y Token
ens_registry_abi   = load_abi("ENSRegistry") if ENS_REGISTRY else None
token_abi          = load_abi("CFPGovernanceToken") if ERC20_TOKEN else None

# Crear objetos contrato ENS y Token
ens_contract = (
    w3.eth.contract(address=Web3.to_checksum_address(ENS_REGISTRY), abi=ens_registry_abi)
    if ENS_REGISTRY and ens_registry_abi else None
)
token_contract = (
    w3.eth.contract(address=Web3.to_checksum_address(ERC20_TOKEN), abi=token_abi)
    if ERC20_TOKEN and token_abi else None
)

# Base de datos y event listener para mantener la informacion de las propuestas
# registrada en el servidor sin necesidad de consultar al nodo Ethereum cada vez.
database.init_db()
# Minar un bloque inicial para que el listener tenga un punto de partida limpio
try:
    w3.provider.make_request("evm_mine", [])
except Exception:
    pass
def send_transaction(tx_function):
    """
    Construye, firma y envia una transaccion usando la cuenta del servidor.
    Espera la confirmacion y devuelve el recibo.
    """

    # Estructurar la transaccion con los parametros necesarios
    tx = tx_function.build_transaction({
        'from':     server_account.address,
        'nonce':    w3.eth.get_transaction_count(server_account.address),
        'gasPrice': w3.eth.gas_price,
        'chainId':  w3.eth.chain_id,
    })

    # Firmar la transaccion con la clave privada del servidor
    signed = w3.eth.account.sign_transaction(tx, server_account.key)

    # Enviar la transaccion al nodo y esperar la confirmacion
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    return w3.eth.wait_for_transaction_receipt(tx_hash)

start_listener(cfp_factory, w3, send_transaction, ENS_REGISTRY, server_account.key.hex())

# Patrones de validacion
HASH_RE    = re.compile(r'^0x[0-9a-fA-F]{64}$')   # 32 bytes = 64 hex chars
ADDRESS_RE = re.compile(r'^0x[0-9a-fA-F]{40}$')   # 20 bytes = 40 hex chars

# Validaciones
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

# Tipos de datos para EIP-712 para MetaMask
TYPE_DEFINITIONS ={
    "CreateRequest": [
        {"name": "operation", "type": "string"},
        {"name": "contract",  "type": "address"},
        {"name": "callId",    "type": "bytes32"}
    ],
    "RegisterRequest": [
        {"name": "operation", "type": "string"},
        {"name": "contract",  "type": "address"},
        {"name": "nonce",     "type": "uint256"},
        {"name": "name",      "type": "string"}
    ],
    "AdminActionRequest": [
        {"name": "operation", "type": "string"},
        {"name": "contract",  "type": "address"},
        {"name": "nonce",     "type": "uint256"},
        {"name": "target",    "type": "address"}
    ]
}

def make_eip712_message(primary_type, message_data, chain_id, contract_address):
    """
    Construye el objeto EIP-712 listo para verificar.
    """
    return encode_typed_data(full_message={
        "domain": {
            "name":              "CFP API",
            "version":           "1",
            "chainId":           chain_id,
            "verifyingContract": contract_address,
        },
        "types": {
            "EIP712Domain": [
                {"name": "name",             "type": "string"},
                {"name": "version",          "type": "string"},
                {"name": "chainId",          "type": "uint256"},
                {"name": "verifyingContract","type": "address"},
            ],
            primary_type: TYPE_DEFINITIONS[primary_type],
        },
        "primaryType": primary_type,
        "message":     message_data,
    })

def recover_typed_address(signable_message, signature: str) -> str:
    """
    Recupera la direccion del firmante a partir de un mensaje tipado (EIP-712).
    """
    sig = signature if signature.startswith("0x") else "0x" + signature
    if len(sig) != 132:
        raise ValueError("Invalid signature length")
    return Account.recover_message(signable_message, signature=sig)

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
    # (indices: 0=creator, 1=cfp, 2=guaranteeAmount)
    cfp_address = call_data[1]
    if cfp_address == ZERO:
        raise ValueError("No existe un contrato CFP para el callId proporcionado")

    # Crear y devolver el objeto contrato de CFP usando la direccion obtenida y la ABI de CFP
    return w3.eth.contract(
        address=Web3.to_checksum_address(cfp_address),
        abi=cfp_abi
    )

def compute_call_id(title: str, description: str) -> str:
    """
    Calcular el callId a partir del titulo y descripcion
    """

    # Define un sedes para una lista de dos elementos: titulo y descripcion, ambos como bytes
    sedes   = RLPList([binary, binary])

    # Encode el titulo y descripcion usando RLP para obtener un byte array
    encoded = rlp.encode(
        [title.encode("utf-8"), description.encode("utf-8")], sedes
    )

    # Calcular el hash keccak256 del byte array codificado y devolverlo como un string hexadecimal
    # con prefijo '0x'
    return "0x" + Web3.keccak(encoded).hex()

def compute_registration_status(address: str, db_exists: bool) -> str:
    """
    Computa el estado de registro consultando la cadena como fuente de verdad.
    La DB solo aporta metadatos off-chain (name, nonce).
    """
    checksum = Web3.to_checksum_address(address)
    is_auth = cfp_factory.functions.isAuthorized(checksum).call()
    is_reg = cfp_factory.functions.isRegistered(checksum).call()
    if is_auth:
        return "authorized"
    if is_reg and db_exists:
        return "registered"
    return "pending"

def err(msg, code):
    """
    Helper para devolver un error con un mensaje y codigo HTTP personalizados.
    """
    return jsonify(message=msg), code

# Helper ENS
def _resolve_ens_reverse(address):
    """Resuelve el nombre ENS inverso de una direccion. Retorna None si no hay."""
    if not ens_contract or not address:
        return None
    try:
        from eth_utils import keccak as eth_keccak
        def _namehash(n):
            node = b'\x00' * 32
            if n:
                labels = n.split(".")
                for label in reversed(labels):
                    node = eth_keccak(node + eth_keccak(text=label))
            return node

        addr_clean = address[2:].lower() if address.startswith("0x") else address.lower()
        reverse_name = f"{addr_clean}.addr.reverse"
        node = _namehash(reverse_name)

        resolver_addr = ens_contract.functions.resolver(node).call()
        if resolver_addr == ZERO:
            return None

        resolver_abi = load_abi("PublicResolver")
        resolver = w3.eth.contract(address=resolver_addr, abi=resolver_abi)
        resolved_name = resolver.functions.name(node).call()
        if not resolved_name:
            return None

        # Verificacion forward: el nombre debe resolver a la direccion original
        fwd_node = _namehash(resolved_name)
        fwd_resolver_addr = ens_contract.functions.resolver(fwd_node).call()
        if fwd_resolver_addr != ZERO:
            fwd_resolver = w3.eth.contract(address=fwd_resolver_addr, abi=resolver_abi)
            fwd_addr = fwd_resolver.functions.addr(fwd_node).call()
            if fwd_addr.lower() == address.lower():
                return resolved_name

        return resolved_name
    except Exception:
        return None

# ----- Endpoints de solo lectura (GET) -----

@app.get("/calls")
def list_calls():
    """Devuelve el listado de llamados creados on-chain. Filtro opcional ?creator=0x..."""
    creator = request.args.get("creator", None)
    try:
        calls = database.get_all_calls(creator)
        # Resolver ENS para cada creador unico
        creator_cache = {}
        for c in calls:
            addr = c.get("creator")
            if addr and addr not in creator_cache:
                creator_cache[addr] = _resolve_ens_reverse(addr) or addr
            c["creator_ens"] = creator_cache.get(addr, addr) if addr else addr
        return jsonify(calls=calls)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)


@app.get("/proposals")
def list_proposals():
    """Devuelve propuestas. Filtro opcional ?proponent=0x..."""
    proponent = request.args.get("proponent", None)
    try:
        if proponent:
            if not is_valid_address(proponent):
                return err(messages.INVALID_ADDRESS, 400)
            proposals = database.get_proposals_by_proponent(proponent)
        else:
            return err(messages.MISSING_FIELD, 400)
        return jsonify(proposals=proposals)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)


@app.get("/contract-address")
def contract_address():
    """Devuelve la direccion del contrato CFPFactory."""
    return jsonify(address=FACTORY_ADDRESS)

@app.get("/contract-owner")
def contract_owner():
    """Devuelve el propietario del contrato CFPFactory."""

    try:
        return jsonify(address=cfp_factory.functions.owner().call())
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
    """
    Devuelve la informacion de una llamada específica. Lo lee de la DB
    """
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)

    try:
        # Intentar obtener la informacion del llamado desde la base de datos.
        # Si no existe, devolver error 404.
        call = database.get_call(call_id)
        if not call:
            return err(messages.CALLID_NOT_FOUND, 404)
        response = {
            "title":       call["title"],
            "description": call["description"],
            "status":      call["status"],
            "guaranteeAmount": call["guarantee_amount"],
            "ens_name":    call.get("ens_name"),
        }
        if call["status"] != "pending":
            creator_ens = _resolve_ens_reverse(call["creator"]) if call["creator"] else None
            response.update({
                "creator": call["creator"],
                "creator_ens": creator_ens or call["creator"],
                "cfp":     call["cfp_address"],
            })
        return jsonify(response)
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

        return jsonify(
            closingTime = datetime.fromtimestamp(cfp_closing_time, tz=timezone.utc).isoformat()
        )
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
        cfp = get_cfp_contract(call_id)
    except ValueError:
        return err(messages.CALLID_NOT_FOUND, 404)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

    try:
        proposal_bytes  = bytes.fromhex(proposal[2:])

        # Obtener los datos de la propuesta.
        data            = cfp.functions.proposalData(proposal_bytes).call()
        sender          = data[0]
        block_number    = data[1]
        timestamp       = data[2]

        if sender == ZERO:
            return err(messages.PROPOSAL_NOT_FOUND, 404)

        timestamp_iso   = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
        closing_ts      = cfp.functions.closingTime().call()
        now_ts          = int(datetime.now(tz=timezone.utc).timestamp())
        status          = "open" if now_ts <= closing_ts else "closed"

        response_data = {
            "sender": sender,
            "blockNumber": block_number,
            "timestamp": timestamp_iso,
            "estado": status
        }

        # Si fue registrada via la API, agregar title, description y proof  parcial
        prop_record = database.get_proposal(proposal)
        if prop_record:
            full_proof      = json.loads(prop_record["proof_json"])
            title           = prop_record["title"]
            description     = prop_record["description"]
            call_key        = call_id.lower()
            title_key       = "0x" + bytes(Web3.keccak(text=title)).hex()
            desc_key        = "0x" + bytes(Web3.keccak(text=description)).hex()
            response_data["title"] = title
            response_data["description"] = description
            response_data["proof"] = {
                k: v for k, v in full_proof.items() if k in (call_key, title_key, desc_key)
            }

        # Devolver la informacion de la propuesta en formato JSON
        return jsonify(response_data)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/registrations/<address>")
def get_registration(address):
    """
    Obtiene la información de registro para una dirección específica.
    El estado se computa consultando la cadena como fuente de verdad.
    """
    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)
    try:
        reg = database.get_registration(address)
        db_exists = reg is not None
        status = compute_registration_status(address, db_exists)
        if reg:
            return jsonify(
                status=status,
                name=reg["name"],
                nonce=reg["nonce"]
            )
        return jsonify(status=status)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)


@app.get("/creators")
def creators():
    """
    Lista todos los creadores registrados en la API, enriqueciendo cada uno
    con su estado on-chain consultado en tiempo real.
    """
    try:
        registrations = database.get_all_registrations()
        result = []
        for reg in registrations:
            status = compute_registration_status(reg["address"], True)
            ens = _resolve_ens_reverse(reg["address"])
            result.append({
                "address": reg["address"],
                "ens": ens or reg["address"],
                "name": reg["name"],
                "nonce": reg["nonce"],
                "status": status
            })
        return jsonify(creators=result)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/admin/pending")
def admin_pending():
    """
    Lista las solicitudes de registro pendientes de autorizacion.
    Consulta getAllPending() del contrato como fuente de verdad y cruza
    con la DB para obtener los nombres.
    """
    try:
        pending_addresses = cfp_factory.functions.getAllPending().call({
            'from': server_account.address
        })
        result = []
        for addr in pending_addresses:
            addr_lower = addr.lower()
            reg = database.get_registration(addr_lower)
            result.append({
                "address": addr,
                "name": reg["name"] if reg else None
            })
        return jsonify(pending=result)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/admin/nonce")
def admin_nonce():
    """
    Obtiene el nonce para el administrador.
    """
    try:
        return jsonify(nonce=database.get_admin_nonce())
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/admin/address")
def admin_address():
    """
    Devuelve la direccion del administrador de la API.
    El frontend lo usa para determinar si el usuario conectado es el admin.
    """
    return jsonify(address=ADMIN_ADDRESS)

@app.get("/calls/<call_id>/proposals")
def call_proposals(call_id):
    """
    Lista las propuestas presentadas para un llamado, incluyendo sus archivos.
    Permite al creador del llamado ver las propuestas recibidas.
    """
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)

    try:
        call = database.get_call(call_id)
        if not call or call["status"] != "created":
            return err(messages.CALLID_NOT_FOUND, 404)

        proposals = database.get_proposals_by_call(call_id)
        result = []
        for p in proposals:
            uploads = database.get_proposal_uploads(p["proposal_id"])
            result.append({
                "proposalId": p["proposal_id"],
                "title": p["title"],
                "description": p["description"],
                "files": [{"hash": u["file_hash"], "name": u["file_name"]} for u in uploads]
            })
        return jsonify(proposals=result), 200
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/calls/<call_id>/deliveries")
def call_deliveries(call_id):
    """
    Lista las entregas post-cierre de un llamado, incluyendo sus archivos.
    Accesible públicamente para consultar archivos recibidos.
    """
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)

    try:
        call = database.get_call(call_id)
        if not call or call["status"] != "created":
            return err(messages.CALLID_NOT_FOUND, 404)

        deliveries = database.get_deliveries_by_call(call_id)
        return jsonify(deliveries=deliveries), 200
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/proposals/<proposal_id>/files/<file_hash>")
def download_proposal_file(proposal_id, file_hash):
    """
    Permite descargar un archivo subido durante el registro de una propuesta.
    """
    if not is_valid_hash(proposal_id) or not is_valid_hash(file_hash):
        return err(messages.INVALID_PROPOSAL, 400)

    uploads = database.get_proposal_uploads(proposal_id)
    for u in uploads:
        if u["file_hash"].lower() == file_hash.lower():
            if os.path.exists(u["file_path"]):
                return send_file(u["file_path"], download_name=u["file_name"])

    return err(messages.NOT_FOUND, 404)

@app.get("/deliveries/<proposal_id>")
def get_delivery_info(proposal_id):
    """Devuelve los datos de la entrega post-cierre y la lista de archivos."""
    if not is_valid_hash(proposal_id):
        return err(messages.INVALID_PROPOSAL, 400)
        
    delivery = database.get_delivery(proposal_id)
    if not delivery:
        return err(messages.NOT_DELIVERED, 404)
        
    files = database.get_proposal_files(proposal_id)
    # Obtener prop_record para incluir call_id
    prop_record = database.get_proposal(proposal_id)
    return jsonify({
        "sender": delivery["sender"],
        "filesRoot": delivery["files_root"],
        "deliveredAt": delivery["delivered_at"],
        "callId": prop_record["call_id"] if prop_record else None,
        "files": [{"hash": f["file_hash"], "name": f["file_name"]} for f in files]
    }), 200

@app.get("/deliveries/<proposal_id>/files/<file_hash>")
def download_file(proposal_id, file_hash):
    """Permite descargar un archivo validado."""
    if not is_valid_hash(proposal_id) or not is_valid_hash(file_hash):
        return err(messages.INVALID_PROPOSAL, 400)
        
    files = database.get_proposal_files(proposal_id)
    for f in files:
        if f["file_hash"].lower() == file_hash.lower():
            if os.path.exists(f["file_path"]):
                return send_file(f["file_path"], download_name=f["file_name"])
            
    return err(messages.NOT_FOUND, 404)

# ----- Endpoints de Token -----

@app.get("/token/address")
def token_address():
    """Devuelve la direccion del token ERC-20."""
    if not token_contract:
        return err("Token no configurado", 404)
    return jsonify(address=ERC20_TOKEN)

@app.get("/token/balance/<address>")
def token_balance(address):
    """Devuelve el balance de tokens de una direccion."""
    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)
    if not token_contract:
        return err("Token no configurado", 404)
    try:
        balance = token_contract.functions.balanceOf(
            Web3.to_checksum_address(address)
        ).call()
        return jsonify(balance=str(balance))
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.get("/token/name")
def token_name():
    """Devuelve el nombre y simbolo del token."""
    if not token_contract:
        return err("Token no configurado", 404)
    try:
        name = token_contract.functions.name().call()
        symbol = token_contract.functions.symbol().call()
        decimals = token_contract.functions.decimals().call()
        tokens_per_eth = token_contract.functions.tokensPerEth().call()
        return jsonify(name=name, symbol=symbol, decimals=decimals, tokensPerEth=str(tokens_per_eth))
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

# ----- Endpoints ENS -----

@app.get("/ens/registry")
def ens_registry():
    """Devuelve la direccion del registry ENS."""
    if not ens_contract:
        return err("ENS no configurado", 404)
    return jsonify(address=ENS_REGISTRY)

@app.get("/ens/addresses")
def ens_addresses():
    """Devuelve las direcciones de todos los contratos ENS."""
    if not ens_contract:
        return err("ENS no configurado", 404)
    try:
        from eth_utils import keccak as eth_keccak
        def _namehash(name):
            node = b'\x00' * 32
            if name:
                labels = name.split(".")
                for label in reversed(labels):
                    node = eth_keccak(node + eth_keccak(text=label))
            return node

        registrar_addr = ens_contract.functions.owner(_namehash("usuarios.cfp")).call()
        resolver_addr = ens_contract.functions.resolver(_namehash("usuarios.cfp")).call()
        reverse_addr = ens_contract.functions.owner(_namehash("addr.reverse")).call()

        return jsonify(
            registry=ENS_REGISTRY,
            registrar=registrar_addr,
            resolver=resolver_addr,
            reverseRegistrar=reverse_addr,
        )
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.post("/ens/resolve")
def ens_resolve():
    """Resuelve nombre ENS a direccion usando PublicResolver."""
    if not ens_contract:
        return err("ENS no configurado", 404)
    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)
    name = req.get("name")
    if not name:
        return err(messages.MISSING_FIELD, 400)

    try:
        from eth_utils import to_bytes, keccak
        def namehash(name):
            node = b'\x00' * 32
            if name:
                labels = name.split(".")
                for label in reversed(labels):
                    node = keccak(node + keccak(text=label))
            return node

        # Calcular namehash("alice.usuarios.cfp") → bytes32
        node = namehash(name)

        # Consultar resolver desde el registry
        resolver_addr = ens_contract.functions.resolver(node).call()
        if resolver_addr == ZERO:
            return err(messages.ENS_NAME_NOT_FOUND, 404)

        # Llamar addr() al resolver
        resolver_abi = load_abi("PublicResolver")
        resolver = w3.eth.contract(address=resolver_addr, abi=resolver_abi)
        resolved = resolver.functions.addr(node).call()
        if resolved == ZERO:
            return err(messages.ENS_NAME_NOT_FOUND, 404)

        return jsonify(address=resolved, name=name)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.post("/ens/reverse")
def ens_reverse():
    """Resuelve una direccion a nombre ENS (resolucion inversa)."""
    if not ens_contract:
        return err("ENS no configurado", 404)
    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)
    address = req.get("address")
    if not address or not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)

    try:
        from eth_utils import to_bytes, keccak
        def namehash(name):
            node = b'\x00' * 32
            if name:
                labels = name.split(".")
                for label in reversed(labels):
                    node = keccak(node + keccak(text=label))
            return node

        # reverse node = namehash(address + ".addr.reverse")
        addr_clean = address[2:].lower()
        reverse_name = f"{addr_clean}.addr.reverse"
        node = namehash(reverse_name)

        resolver_addr = ens_contract.functions.resolver(node).call()
        if resolver_addr == ZERO:
            return err(messages.ENS_ADDRESS_NOT_FOUND, 404)

        resolver_abi = load_abi("PublicResolver")
        resolver = w3.eth.contract(address=resolver_addr, abi=resolver_abi)
        resolved_name = resolver.functions.name(node).call()
        if not resolved_name:
            return err(messages.ENS_ADDRESS_NOT_FOUND, 404)

        return jsonify(name=resolved_name, address=address)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

# ----- Endpoints de Garantia -----

@app.get("/calls/<call_id>/guarantee")
def call_guarantee(call_id):
    """Devuelve informacion de la garantia de un llamado."""
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)
    try:
        cfp = get_cfp_contract(call_id)
        call_data = database.get_call(call_id)
        cfp_address = call_data["cfp_address"] if call_data else None
        guarantee = cfp.functions.guaranteeAmount().call()
        token_addr = cfp.functions.token().call()
        finalized = cfp.functions.finalized().call()
        return jsonify(
            cfp=cfp_address,
            guaranteeAmount=str(guarantee),
            token=token_addr,
            finalized=finalized,
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
    Acepta multipart/form-data con:
      - callId, title, description (form fields)
      - files (archivos adjuntos, uno o más)
    """

    # Verifica que se hayan proporcionado todos los campos necesarios
    call_id     = request.form.get("callId")
    title       = request.form.get("title")
    description = request.form.get("description")
    sender      = request.form.get("sender")
    uploaded_files = request.files.getlist("files")

    if call_id is None or title is None or description is None:
        return err(messages.MISSING_FIELD, 400)
    if not is_valid_hash(call_id):
        return err(messages.INVALID_CALLID, 400)

    title       = title.rstrip()
    description = description.rstrip()

    if not title:
        return err(messages.INVALID_TITLE, 400)
    if len(title.encode("utf-8")) > 512:
        return err(messages.TITLE_TOO_LONG, 400)
    if len(description.encode("utf-8")) > 4096:
        return err(messages.DESCRIPTION_TOO_LONG, 400)

    # Calcular hashes de los archivos subidos
    file_hashes = []
    file_records = []
    for f in uploaded_files:
        content = f.read()
        f.seek(0)
        f_hash = "0x" + Web3.keccak(content).hex()
        file_hashes.append(f_hash)
        file_records.append({
            "hash": f_hash,
            "name": secure_filename(f.filename or "archivo"),
            "content": content
        })

    if len(file_hashes) > 125:
        return err(messages.TOO_MANY_FILES, 400)
    if len(file_hashes) != len(set(h.lower() for h in file_hashes)):
        return err(messages.INVALID_PROPOSAL, 400)

    try:
        cfp = get_cfp_contract(call_id)
    except ValueError:
        return err(messages.CALLID_NOT_FOUND, 404)
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

    try:
        # proposalId = Merkle root de [callId, keccak(title), keccak(desc)] + file_hashes
        proposal_id    = merkle.compute_proposal_id(call_id, title, description, file_hashes)
        proposal_bytes = bytes.fromhex(proposal_id[2:])

        data = cfp.functions.proposalData(proposal_bytes).call()
        if data[0] != ZERO:
            return err(messages.ALREADY_REGISTERED, 403)

        # Pruebas Merkle para cada hoja (para el recibo)
        proofs = merkle.compute_proposal_proofs(call_id, title, description, file_hashes)

        # Determinar si el llamado requiere garantia consultando la DB
        call = database.get_call(call_id)
        guarantee_amount = call["guarantee_amount"] if call else 0
        requires_collateral = guarantee_amount > 0

        if requires_collateral:
            # Con garantia: el usuario debe llamar registerProposalWithCollateral
            # via MetaMask. La API solo prepara y guarda los datos off-chain.
            database.insert_proposal(proposal_id, call_id, title, description, proofs, sender)
            prop_dir = os.path.join(UPLOAD_FOLDER, proposal_id)
            os.makedirs(prop_dir, exist_ok=True)
            # Guarda archivos en disco y registra en la BD
            for fr in file_records:
                path = os.path.join(prop_dir, fr["name"])
                with open(path, "wb") as out_file:
                    out_file.write(fr["content"])
                database.insert_proposal_upload(proposal_id, fr["hash"], fr["name"], path)

            return jsonify(
                message=messages.REQUIRES_COLLATERAL,
                proposalId=proposal_id,
                proof=proofs,
                requiresCollateral=True,
                cfpAddress=call["cfp_address"],
                guaranteeAmount=guarantee_amount,
            ), 201
        else:
            # Sin garantia: la API paga el gas y envia la transaccion
            send_transaction(
                cfp_factory.functions.registerProposal(
                    bytes.fromhex(call_id[2:]), proposal_bytes
                )
            )
            # Guarda en la BD
            database.insert_proposal(proposal_id, call_id, title, description, proofs, sender)

            prop_dir = os.path.join(UPLOAD_FOLDER, proposal_id)
            os.makedirs(prop_dir, exist_ok=True)
            for fr in file_records:
                path = os.path.join(prop_dir, fr["name"])
                with open(path, "wb") as out_file:
                    out_file.write(fr["content"])
                database.insert_proposal_upload(proposal_id, fr["hash"], fr["name"], path)

            # Devolver la respuesta con el proposalId y las pruebas Merkle
            return jsonify(
                message=messages.OK,
                proposalId=proposal_id,
                proof=proofs
            ), 201
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.post("/register")
def register():
    """
    Inicia el registro de un creador (o lo renueva).
    Requiere firma EIP-712 (RegisterRequest, nonce=0) coincidente con 'address'.
    """

    # Ejecuta la función de seguridad inicial de las rutas POST para asegurar que la cabecera
    # declare JSON; bloquea si devuelve nulidad.
    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    # Extrae la dirección y su firma digital enviadas para el proceso de autorización.
    address     = req.get("address")
    name        = req.get("name")
    signature   = req.get("signature")
    if address is None or name is None or signature is None:
        return err(messages.MISSING_FIELD, 400)
    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)
    # La cuenta administradora no puede registrarse como creador
    if address.lower() == ADMIN_ADDRESS.lower():
        return err(messages.ADMIN_CANNOT_REGISTER, 403)

    name = name.rstrip()
    if not name:
        return err(messages.INVALID_NAME, 400)
    if len(name.encode('utf-8')) > 512:
        return err(messages.NAME_TOO_LONG, 400)

    try:
        # Obtiene chainId para incluirlo en el mensaje EIP-712
        chain_id = w3.eth.chain_id
        signable = make_eip712_message(
            "RegisterRequest",
            {
                "operation": "register",
                "contract": Web3.to_checksum_address(FACTORY_ADDRESS),
                "nonce": 0,
                "name": name
            },
            chain_id,
            Web3.to_checksum_address(FACTORY_ADDRESS)
        )
        recovered = recover_typed_address(signable, signature)
    except Exception:
        return err(messages.INVALID_SIGNATURE, 400)

    if recovered.lower() != address.lower():
        return err(messages.INVALID_SIGNATURE, 400)

    try:
        reg = database.get_registration(address)
        if reg:
            return err(messages.ALREADY_IN_SYSTEM, 403)

        database.upsert_registration(address, name)
        status = compute_registration_status(address, True)
        return jsonify(status=status), 200
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)

@app.post("/create")
def create():
    """
    Crea un nuevo llamado (CFP).
    Requiere firma EIP-712 (CreateRequest) de un creador autorizado.
    Valida la relación criptográfica entre el callId y los datos (title, description).
    """
    try:
        # Ejecuta la función de seguridad inicial de las rutas POST para asegurar que la cabecera
        # declare JSON; bloquea si devuelve nulidad.
        req = check_mimetype()
        if req is None:
            return err(messages.INVALID_MIMETYPE, 400)

        call_id         = req.get("callId")
        title           = req.get("title")
        description     = req.get("description")
        signature       = req.get("signature")
        guarantee_amount = req.get("guaranteeAmount", 0)
        ens_name        = req.get("ensName", "")
        closing_time    = req.get("closingTime")

        if not isinstance(guarantee_amount, int) or guarantee_amount < 0:
            return err(messages.INVALID_AMOUNT, 400)
        if call_id is None or title is None or description is None or signature is None:
            return err(messages.MISSING_FIELD, 400)
        if not is_valid_hash(call_id):
            return err(messages.INVALID_CALLID, 400)
        if closing_time is None:
            return err(messages.MISSING_FIELD, 400)
        if not isinstance(closing_time, int) or closing_time <= w3.eth.get_block("latest").timestamp:
            return err(messages.PAST_CLOSING_TIME, 400)

        title = title.rstrip()
        description = description.rstrip()
        if not title:
            return err(messages.INVALID_TITLE, 400)
        if len(title.encode("utf-8")) > 512:
            return err(messages.TITLE_TOO_LONG, 400)
        if len(description.encode("utf-8")) > 4096:
            return err(messages.DESCRIPTION_TOO_LONG, 400)

        # Verificar que callId = keccak256(rlp.encode([title, description])) para
        # evitar que alguien cree llamados con callIds falsos
        if call_id.lower() != compute_call_id(title, description).lower():
            return err(messages.INVALID_CALLID, 400)

        # Mensaje: CREATE_PREFIX + contract(20) + callId(32) = 62 bytes
        try:
            chain_id = w3.eth.chain_id
            signable = make_eip712_message(
                "CreateRequest",
                {
                    "operation": "create",
                    "contract": Web3.to_checksum_address(FACTORY_ADDRESS),
                    "callId": bytes.fromhex(call_id[2:])
                },
                chain_id,
                Web3.to_checksum_address(FACTORY_ADDRESS)
            )
            recovered = recover_typed_address(signable, signature)
        except Exception:
            return err(messages.INVALID_SIGNATURE, 400)

        if not cfp_factory.functions.isAuthorized(
            Web3.to_checksum_address(recovered)
        ).call():
            return err(messages.UNAUTHORIZED, 403)

        if database.get_call(call_id):
            return err(messages.ALREADY_CREATED, 403)

        if ens_name and database.get_call_by_ens_name(ens_name):
            return err("El nombre ENS del llamado ya existe", 409)

        database.insert_call(call_id, title, description, guarantee_amount, ens_name)
        return jsonify(message=messages.OK, guaranteeAmount=guarantee_amount, ensName=ens_name), 201

    except Exception:
        logging.exception("Exception in /create")
        return err(messages.INTERNAL_ERROR, 500)

@app.post("/authorize/<address>")
def authorize(address):
    """
    Autoriza una direccion para crear llamados.
    """
    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)

    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    signature = req.get("signature")
    if signature is None:
        return err(messages.MISSING_FIELD, 400)

    try:
        nonce    = database.get_admin_nonce()
        chain_id = w3.eth.chain_id
        signable = make_eip712_message(
            "AdminActionRequest",
            {
                "operation": "authorize",
                "contract": Web3.to_checksum_address(FACTORY_ADDRESS),
                "nonce": nonce,
                "target": Web3.to_checksum_address(address)
            },
            chain_id,
            Web3.to_checksum_address(FACTORY_ADDRESS)
        )
        recovered = recover_typed_address(signable, signature)
    except Exception:
        return err(messages.INVALID_SIGNATURE, 400)

    if recovered.lower() != ADMIN_ADDRESS.lower():
        return err(messages.INVALID_SIGNATURE, 400)

    # Verificar el registro: debe estar registrado on-chain y en la DB
    try:
        checksum = Web3.to_checksum_address(address)
        if not cfp_factory.functions.isRegistered(checksum).call():
            return err(messages.NOT_REGISTERED, 404)
        if not database.get_registration(address):
            return err(messages.NOT_REGISTERED, 404)

        send_transaction(
            cfp_factory.functions.authorize(checksum)
        )
        database.increment_admin_nonce()
        return jsonify(message=messages.OK), 200
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)


@app.post("/unauthorize/<address>")
def unauthorize(address):
    """
    Desautoriza una direccion previamente autorizada.
    """
    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)

    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    signature = req.get("signature")
    if signature is None:
        return err(messages.MISSING_FIELD, 400)

    # Validar firma PRIMERO
    try:
        nonce    = database.get_admin_nonce()
        chain_id = w3.eth.chain_id
        signable = make_eip712_message(
            "AdminActionRequest",
            {
                "operation": "unauthorize",
                "contract": Web3.to_checksum_address(FACTORY_ADDRESS),
                "nonce": nonce,
                "target": Web3.to_checksum_address(address)
            },
            chain_id,
            Web3.to_checksum_address(FACTORY_ADDRESS)
        )
        recovered = recover_typed_address(signable, signature)
    except Exception:
        return err(messages.INVALID_SIGNATURE, 400)

    if recovered.lower() != ADMIN_ADDRESS.lower():
        return err(messages.INVALID_SIGNATURE, 400)

    # Verificar que la dirección esté registrada o autorizada on-chain
    try:
        checksum = Web3.to_checksum_address(address)
        if not cfp_factory.functions.isRegistered(checksum).call() and not cfp_factory.functions.isAuthorized(checksum).call():
            return err(messages.NOT_REGISTERED, 404)

        # Verificar que tenga un registro en la DB (preserva nonce anti-replay)
        reg = database.get_registration(address)
        if not reg:
            return err(messages.NOT_REGISTERED, 404)

        send_transaction(
            cfp_factory.functions.unauthorize(checksum)
        )
        database.increment_admin_nonce()

        return jsonify(message=messages.OK), 200
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)


@app.post("/verify-proof")
def verify_proof():
    """
    Verifica la validez de una prueba de Merkle para una propuesta.
    """
    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    proposal_id = req.get("proposalId")
    leaf        = req.get("leaf")
    proof       = req.get("proof")

    if proposal_id is None or leaf is None or proof is None:
        return err(messages.MISSING_FIELD, 400)
    if not is_valid_hash(proposal_id):
        return err(messages.INVALID_PROPOSAL, 400)
    if not is_valid_hash(leaf):
        return err(messages.INVALID_PROPOSAL, 400)
    if not isinstance(proof, list):
        return err(messages.INVALID_PROPOSAL, 400)
    if len(proof) > 7:
        return err(messages.PROOF_TOO_LONG, 400)
    for p in proof:
        if not is_valid_hash(p):
            return err(messages.INVALID_PROPOSAL, 400)

    return jsonify(valid=merkle.verify_proof(proof, proposal_id, leaf)), 200

@app.post("/deliver")
def deliver_files():
    """
    Entrega post-cierre.
    Recibe multipart/form-data:
      - 'receipt': el JSON completo devuelto en register-proposal
      - 'files': los archivos físicos reales
    """
    if 'receipt' not in request.form:
        return err(messages.MISSING_FIELD, 400)

    files = request.files.getlist('files')
    if not files:
        return err(messages.MISSING_FIELD, 400)
    try:
        # El recibo contiene el proposalId y las pruebas Merkle de los archivos
        receipt = json.loads(request.form['receipt'])
        proposal_id = receipt.get('proposalId')
        proof = receipt.get('proof', {})
    except Exception:
        return err(messages.INVALID_PROPOSAL, 400)
    if not is_valid_hash(proposal_id):
        return err(messages.INVALID_PROPOSAL, 400)
    # 1. Recuperar el llamado y la propuesta desde la DB
    prop_record = database.get_proposal(proposal_id)
    if not prop_record:
        return err(messages.PROPOSAL_NOT_FOUND, 404)

    call_id = prop_record["call_id"]
    try:
        # Recuperar el contrato del llamado para consultar su estado on-chain
        cfp = get_cfp_contract(call_id)
    except Exception:
        return err(messages.CALLID_NOT_FOUND, 404)
    # 2. Verificar que el llamado esté cerrado
    closing_ts = cfp.functions.closingTime().call()
    now_ts = int(datetime.now(tz=timezone.utc).timestamp())
    if now_ts <= closing_ts:
        return err(messages.CALL_NOT_CLOSED, 403)
    # 3. Verificar que la propuesta esté registrada on-chain
    proposal_bytes = bytes.fromhex(proposal_id[2:])
    p_data = cfp.functions.proposalData(proposal_bytes).call()
    if p_data[0] == ZERO:
        return err(messages.PROPOSAL_NOT_FOUND, 404)
    # 4. Verificar que no haya sido entregada ya
    delivery_data = cfp.functions.deliveryData(proposal_bytes).call()
    if delivery_data[4]: # 'delivered' es el quinto elemento del struct
        return err(messages.ALREADY_DELIVERED, 403)
    # 5. Calcular hashes de los archivos subidos
    file_hashes = []
    file_records = []

    for f in files:
        file_content = f.read()
        f.seek(0) # Resetear puntero por si acaso
        f_hash = "0x" + Web3.keccak(file_content).hex()
        file_hashes.append(f_hash)
        file_records.append({
            "hash": f_hash,
            "name": secure_filename(f.filename or "archivo_sin_nombre"),
            "content": file_content
        })
    # 6. Validar contra las pruebas del recibo
    # Chequear que todos los hashes calculados estén en las pruebas del recibo original
    # y que la prueba sea válida contra el proposalId.
    for fh in file_hashes:
        if fh not in proof:
            return err(messages.INVALID_PROPOSAL, 400)
        if not merkle.verify_proof(proof[fh], proposal_id, fh):
            return err(messages.INVALID_PROPOSAL, 400)
    # 7. Calcular el filesRoot (Raíz de Merkle exclusiva de los archivos)
    # Reutilizamos la función de Merkle ordenando los hashes de archivos
    file_leaves = [bytes.fromhex(h[2:]) for h in file_hashes]
    root, _ = merkle.build_merkle_tree(file_leaves)
    files_root_hex = "0x" + root.hex()

    # Este `filesRoot` es un arbol Merkle exclusivo de los archivos
    # (sin `callId`, `title`, `description`). Sirve como sello criptografico
    # del conjunto exacto de archivos entregados.

    # 8. Transacción on-chain (La API paga el Gas con su server_account)
    try:
        tx_receipt = send_transaction(
            cfp.functions.registerDelivery(
                proposal_bytes, 
                bytes.fromhex(files_root_hex[2:])
            )
        )
    except Exception as e:
        return err(messages.INTERNAL_ERROR, 500)

    # 9. Guardar los archivos físicos y actualizar DB
    # Creamos subcarpeta para la propuesta
    prop_dir = os.path.join(UPLOAD_FOLDER, proposal_id)
    os.makedirs(prop_dir, exist_ok=True)
    database.insert_delivery(proposal_id, call_id, p_data[0], files_root_hex)
    for fr in file_records:
        path = os.path.join(prop_dir, fr["name"])
        with open(path, "wb") as out_file:
            out_file.write(fr["content"])
        database.insert_proposal_file(proposal_id, fr["hash"], fr["name"], path)
    # Respuesta al frontend
    return jsonify({
        "message": messages.OK,
        "filesRoot": files_root_hex,
        "proposalId": proposal_id,
        "txHash": Web3.to_hex(tx_receipt["transactionHash"]),
        "blockNumber": tx_receipt["blockNumber"]
    }), 201

@app.patch("/registrations/<address>")
def patch_registration(address):
    """
    Actualiza el nombre de un registro existente.
    """
    if not is_valid_address(address):
        return err(messages.INVALID_ADDRESS, 400)
    if address.lower() == ADMIN_ADDRESS.lower():
        return err(messages.ADMIN_CANNOT_REGISTER, 403)

    req = check_mimetype()
    if req is None:
        return err(messages.INVALID_MIMETYPE, 400)

    name      = req.get("name")
    signature = req.get("signature")

    if name is None or signature is None:
        return err(messages.MISSING_FIELD, 400)

    name = name.rstrip()
    if not name:
        return err(messages.INVALID_NAME, 400)
    if len(name.encode("utf-8")) > 512:
        return err(messages.NAME_TOO_LONG, 400)

    try:
        reg = database.get_registration(address)
        if not reg:
            return err(messages.NOT_REGISTERED, 404)

        nonce = reg["nonce"]

        try:
            chain_id = w3.eth.chain_id
            signable = make_eip712_message(
                "RegisterRequest",
                {
                    "operation": "update",
                    "contract": Web3.to_checksum_address(FACTORY_ADDRESS),
                    "nonce": nonce,
                    "name": name
                },
                chain_id,
                Web3.to_checksum_address(FACTORY_ADDRESS)
            )
            recovered = recover_typed_address(signable, signature)
        except Exception:
            return err(messages.INVALID_SIGNATURE, 400)

        if recovered.lower() != address.lower():
            return err(messages.INVALID_SIGNATURE, 400)

        database.update_registration_name(address, name)
        return jsonify(message=messages.OK), 200
    except Exception:
        return err(messages.INTERNAL_ERROR, 500)


def check_mimetype():
    """Valida que la solicitud tenga Content-Type application/json y devuelve el JSON parseado."""

    if request.mimetype != "application/json":
        return None
    return request.get_json(silent=True)

@app.errorhandler(Exception)
def handle_exception(e):
    """
    Maneja excepciones no controladas.
    """
    logging.error("Error no manejado: %s", str(e))
    return err(messages.INTERNAL_ERROR, 500)

if __name__ == "__main__":
    app.run(debug=False, port="5000")
