"""Casos de prueba para el servidor de APIs."""

# pylint: disable=global-statement,invalid-name,too-many-lines
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from os import urandom
from random import randrange
from typing import Optional

import pytest
import requests
import rlp
from rlp.sedes import binary, List as RLPList
from dateutil.parser import isoparse
from dateutil.relativedelta import relativedelta
from eth_account import Account
from eth_account.messages import SignableMessage, encode_defunct, encode_typed_data
from eth_account.signers.local import LocalAccount
from jsonschema import validate
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.types import RPCEndpoint

import messages

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")

# SHA-256 de test/MerkleVerifier.sol en el momento de la última compilación.
# Si este valor no coincide con el archivo en disco, get_verifier_contract()
# fallará con un error explícito. Ver test/README.md para instrucciones de
# actualización.
MERKLE_VERIFIER_SHA256 = "e31728f2b86cc1a7f14f1ecefaf8eefba10a0191576b318605dd0dfbd9ef683d"


@pytest.fixture(autouse=True)
def settle_hardhat():
    """Mina un bloque vacío después de cada test para que eth_getTransactionCount
    no quede stale."""
    yield
    get_w3().provider.make_request(RPCEndpoint("evm_mine"), [])


calls_created_schema = {
    "type": "object",
    "properties": {
        "creator": {"type": "string"},
        "cfp": {"type": "string"},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "status": {"type": "string"},
    },
    "required": ["creator", "cfp", "title", "description", "status"],
}

calls_pending_schema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "status": {"type": "string"},
    },
    "required": ["title", "description", "status"],
}

proposal_data_schema = {
    "type": "object",
    "properties": {
        "sender": {"type": "string"},
        "blockNumber": {"anyOf": [{"type": "number"}, {"type": "string"}]},
        "timestamp": {"type": "string"},
        "estado": {"type": "string", "enum": ["open", "closed"]},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "proof": {
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
        },
    },
    "required": ["sender", "blockNumber", "timestamp", "estado"],
}


def single_field_schema(field, field_type="string"):
    """Genera un esquema de validación de un solo campo."""
    return {
        "type": "object",
        "properties": {
            f"{field}": {"type": f"{field_type}"},
        },
        "required": [f"{field}"],
    }


message_schema = single_field_schema("message")
authorized_schema = single_field_schema("authorized", "boolean")
closing_time_schema = single_field_schema("closingTime")

register_proposal_schema = {
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "proposalId": {"type": "string"},
        "proof": {
            "type": "object",
            "additionalProperties": {"type": "array", "items": {"type": "string"}},
        },
    },
    "required": ["message", "proposalId", "proof"],
}
address_schema = single_field_schema("address")

registration_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "nonce": {"type": "integer"},
        "status": {"type": "string"},
    },
    "required": ["name", "nonce", "status"],
}

registration_status_schema = {
    "type": "object",
    "properties": {
        "status": {"type": "string"},
    },
    "required": ["status"],
}

CREATE_PREFIX = b"createPOST"
REGISTER_PREFIX = b"registerPOST"
UPDATE_PREFIX = b"registrationsPATCH"
AUTHORIZE_PREFIX = b"authorizePOST"
UNAUTHORIZE_PREFIX = b"unauthorizePOST"

# ABI mínima necesaria para la interacción directa con el contrato en los tests
FACTORY_MINIMAL_ABI = [
    {
        "type": "function",
        "name": "register",
        "inputs": [],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "authorize",
        "inputs": [{"name": "creator", "type": "address"}],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "isAuthorized",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"type": "bool"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "isRegistered",
        "inputs": [{"name": "account", "type": "address"}],
        "outputs": [{"type": "bool"}],
        "stateMutability": "view",
    },
    {
        "type": "function",
        "name": "create",
        "inputs": [
            {"name": "callId", "type": "bytes32"},
            {"name": "timestamp", "type": "uint256"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
    {
        "type": "function",
        "name": "registerProposal",
        "inputs": [
            {"name": "callId", "type": "bytes32"},
            {"name": "proposal", "type": "bytes32"},
        ],
        "outputs": [],
        "stateMutability": "nonpayable",
    },
]

SERVER = "http://127.0.0.1:5000"
APPLICATION_JSON = "application/json"
WEB3_URI = os.environ.get("CFP_WEB3_URI", "http://127.0.0.1:8545")

# Frase default de Hardhat (tiene ETH en el nodo local)
HARDHAT_MNEMONIC = "test test test test test test test test test test test junk"
# Frase MetaMask opcional; si no se provee usa la de Hardhat (para tests en dev)
METAMASK_MNEMONIC = os.environ.get("CFP_METAMASK_MNEMONIC", HARDHAT_MNEMONIC)

accounts = []
calls = {}
_run_id = os.urandom(4).hex()  # único por ejecución, evita conflictos entre runs

# Estado lazy de web3 y contrato de fábrica para los tests
_w3 = None
_factory_contract = None
_owner_account = None
_funder_account = None
_admin_account = None
_verifier_contract = None


def get_w3() -> Web3:
    """Retorna la instancia de web3 (inicialización lazy)."""
    global _w3
    if _w3 is None:
        _w3 = Web3(Web3.HTTPProvider(WEB3_URI))
        _w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        _w3.eth.account.enable_unaudited_hdwallet_features()
    return _w3


def get_factory_contract():
    """Retorna el contrato de fábrica para interacción directa (inicialización lazy)."""
    global _factory_contract, _owner_account
    if _factory_contract is None:
        w3 = get_w3()
        mnemonic = os.environ.get("CFP_MNEMONIC", "")
        factory_address = os.environ.get("CFP_FACTORY_ADDRESS", "")
        _owner_account = w3.eth.account.from_mnemonic(mnemonic)
        _factory_contract = w3.eth.contract(
            address=w3.to_checksum_address(factory_address),
            abi=FACTORY_MINIMAL_ABI,
        )
    return _factory_contract, _owner_account


def get_funder_account():
    """Retorna la cuenta fondeadora (cuenta 0 de Hardhat, no de CFP_MNEMONIC)."""
    global _funder_account
    if _funder_account is None:
        w3 = get_w3()
        _funder_account = w3.eth.account.from_mnemonic(
            HARDHAT_MNEMONIC, account_path="m/44'/60'/0'/0/0"
        )
    return _funder_account


def get_admin_account():
    """Retorna la cuenta administradora (índice 0 de la frase MetaMask)."""
    global _admin_account
    if _admin_account is None:
        w3 = get_w3()
        _admin_account = w3.eth.account.from_mnemonic(
            METAMASK_MNEMONIC, account_path="m/44'/60'/0'/0/0"
        )
    return _admin_account


def get_verifier_contract():
    """Despliega (la primera vez) el contrato MerkleVerifier y retorna la instancia cacheada."""
    global _verifier_contract
    if _verifier_contract is None:
        sol_path = os.path.join(TEST_DIR, "MerkleVerifier.sol")
        with open(sol_path, "rb") as f:
            actual_sha256 = hashlib.sha256(f.read()).hexdigest()
        assert actual_sha256 == MERKLE_VERIFIER_SHA256, (
            f"MerkleVerifier.sol ha cambiado (SHA-256: {actual_sha256}). "
            "Recompilá el contrato, actualizá test/MerkleVerifier.json y "
            "la constante MERKLE_VERIFIER_SHA256 en este archivo. "
            "Ver test/README.md para instrucciones."
        )
        w3 = get_w3()
        with open(os.path.join(TEST_DIR, "MerkleVerifier.json"), encoding="utf-8") as f:
            artifact = json.load(f)
        funder = get_funder_account()
        deploy_tx = (
            w3.eth.contract(
                abi=artifact["abi"],
                bytecode=artifact["bytecode"],
            )
            .constructor()
            .build_transaction(
                {
                    "from": funder.address,
                    "nonce": w3.eth.get_transaction_count(funder.address),
                    "gas": 500000,
                    "gasPrice": w3.to_wei("1", "gwei"),
                }
            )
        )
        signed = funder.sign_transaction(deploy_tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        _verifier_contract = w3.eth.contract(
            address=receipt["contractAddress"],
            abi=artifact["abi"],
        )
    return _verifier_contract


def fund_account(address: str) -> None:
    """Transfiere ETH suficiente a una cuenta para pagar gas."""
    w3 = get_w3()
    funder = get_funder_account()
    tx = {
        "from": funder.address,
        "to": address,
        "value": w3.to_wei("0.01", "ether"),
        "gas": 21000,
        "gasPrice": w3.to_wei("1", "gwei"),
        "nonce": w3.eth.get_transaction_count(funder.address),
    }
    signed = funder.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)


def send_register_tx(account: LocalAccount) -> None:
    """Llama a contract.register() en nombre de la cuenta dada."""
    w3 = get_w3()
    factory, _ = get_factory_contract()
    tx = factory.functions.register().build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 200000,
            "gasPrice": w3.to_wei("1", "gwei"),
        }
    )
    signed = account.sign_transaction(tx)  # type: ignore[arg-type]
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)


def wait_for_registration_status(
    address: str, expected_status: str, timeout: int = 15
) -> bool:
    """Espera hasta que GET /registrations/:address devuelva el estado esperado."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = get_registration(address)
        if resp.status_code == 200 and resp.json().get("status") == expected_status:
            get_w3().provider.make_request(RPCEndpoint("evm_mine"), [])
            return True
        time.sleep(0.5)
    return False


def url(action: str, arg: Optional[str] = None) -> str:
    """Genera una URL para una acción y un argumento opcional."""
    return f"{SERVER}/{action}/{arg}" if arg else f"{SERVER}/{action}"


def random_hex(length: int) -> str:
    """Genera una string hexadecimal aleatoria de la longitud dada."""
    return f"0x{urandom(length).hex()}"


def random_hash() -> str:
    """Genera un hash aleatorio."""
    return random_hex(32)


def random_address() -> str:
    """Genera una dirección aleatoria."""
    return random_hex(20)


def random_signature() -> str:
    """Genera una firma aleatoria."""
    return random_hex(65)


def get_closing_time(past: bool = False) -> datetime:
    """Genera una fecha aleatoria en el futuro o pasado."""
    days: int = 1 + randrange(90)
    if past:
        days = -days
    hour: int = randrange(8, 18)
    return datetime.now(timezone.utc) + relativedelta(
        days=days, hour=hour, minute=0, second=0, microsecond=0
    )


def get_contract_address() -> str:
    """Obtiene la dirección del contrato."""
    response = requests.get(url("contract-address"), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    validate(instance=response.json(), schema=address_schema)
    return response.json()["address"]


def get_contract_owner() -> str:
    """Obtiene la dirección del dueño del contrato."""
    response = requests.get(url("contract-owner"), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    validate(instance=response.json(), schema=address_schema)
    return response.json()["address"]


def to_hex(value: bytes) -> str:
    """Convierte bytes a string hexadecimal con prefijo 0x."""
    h = value.hex()
    return h if h.startswith("0x") else "0x" + h


def sign(message: str, account: LocalAccount) -> str:
    """Firma un mensaje desde la cuenta especificada."""
    signable_message: SignableMessage = encode_defunct(hexstr=message)
    return to_hex(account.sign_message(signable_message).signature)

TYPE_DEFINITIONS = {
    "CreateRequest": [
        {"name": "operation", "type": "string"},
        {"name": "contract",  "type": "address"},
        {"name": "callId",    "type": "bytes32"},
    ],
    "RegisterRequest": [
        {"name": "operation", "type": "string"},
        {"name": "contract",  "type": "address"},
        {"name": "nonce",     "type": "uint256"},
        {"name": "name",      "type": "string"},
    ],
    "AdminActionRequest": [
        {"name": "operation", "type": "string"},
        {"name": "contract",  "type": "address"},
        {"name": "nonce",     "type": "uint256"},
        {"name": "target",    "type": "address"},
    ],
}
def make_eip712_message(primary_type, message_data, contract_address):
    """
    Construye el objeto EIP-712 listo para firmar en los tests.
    """
    # En los tests sabemos que chain_id es 31337 (la red de hardhat local)
    return encode_typed_data(full_message={
        "domain": {
            "name":              "CFP API",
            "version":           "1",
            "chainId":           31337,
            "verifyingContract": Web3.to_checksum_address(contract_address),
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


def sign_bytes(signable_message: SignableMessage, account: LocalAccount) -> str:
    """Firma un mensaje EIP-712 estructurado desde la cuenta especificada."""
    return to_hex(account.sign_message(signable_message).signature)


def make_register_message(contract_address: str, name: str) -> SignableMessage:
    """Construye el mensaje a firmar para /register."""
    return make_eip712_message("RegisterRequest", {
        "operation": "register",
        "contract": Web3.to_checksum_address(contract_address),
        "nonce": 0,
        "name": name
    }, contract_address)


def make_update_message(contract_address: str, nonce: int, name: str) -> SignableMessage:
    """Construye el mensaje a firmar para PATCH /registrations."""
    return make_eip712_message("RegisterRequest", {
        "operation": "update",
        "contract": Web3.to_checksum_address(contract_address),
        "nonce": nonce,
        "name": name
    }, contract_address)


def get_admin_nonce() -> int:
    """Obtiene el nonce actual del administrador."""
    response = requests.get(url("admin/nonce"), timeout=3)
    assert response.status_code == 200
    return response.json()["nonce"]


def make_authorize_message(
    contract_address: str, nonce: int, target_address: str
    ) -> SignableMessage:
    """Construye el mensaje a firmar para /authorize."""
    return make_eip712_message("AdminActionRequest", {
        "operation": "authorize",
        "contract": Web3.to_checksum_address(contract_address),
        "nonce": nonce,
        "target": Web3.to_checksum_address(target_address)
    }, contract_address)


def make_unauthorize_message(
    contract_address: str, nonce: int, target_address: str
    ) -> SignableMessage:
    """Construye el mensaje a firmar para /unauthorize."""
    return make_eip712_message("AdminActionRequest", {
        "operation": "unauthorize",
        "contract": Web3.to_checksum_address(contract_address),
        "nonce": nonce,
        "target": Web3.to_checksum_address(target_address)
    }, contract_address)


def post_authorize(address: str, signature: str):
    """Envía POST /authorize/:address."""
    return requests.post(
        url("authorize", address), json={"signature": signature}, timeout=15
    )


def post_unauthorize(address: str, signature: str):
    """Envía POST /unauthorize/:address."""
    return requests.post(
        url("unauthorize", address), json={"signature": signature}, timeout=15
    )


def get_registration(address: str):
    """Obtiene el nombre, nonce y estado de una dirección registrada."""
    return requests.get(url("registrations", address), timeout=3)


def patch_registration(address: str, name: str, signature: str):
    """Actualiza el nombre de una dirección registrada."""
    return requests.patch(
        url("registrations", address),
        json={"name": name, "signature": signature},
        timeout=10,
    )


def make_call_id(title: str, description: str) -> str:
    """Computa el callId como keccak256(rlp([title_utf8, description_utf8]))."""
    sedes = RLPList([binary, binary])
    encoded = rlp.encode([title.encode("utf-8"), description.encode("utf-8")], sedes)
    return "0x" + Web3.keccak(encoded).hex()


def _hash_pair(a: bytes, b: bytes) -> bytes:
    if a <= b:
        return bytes(Web3.keccak(a + b))
    return bytes(Web3.keccak(b + a))


def _compute_merkle_root(leaves: list) -> bytes:
    n = len(leaves)
    if n == 1:
        return leaves[0]
    tree: list[bytes | None] = [None] * (2 * n - 1)
    for i in range(n):
        tree[2 * n - 2 - i] = leaves[i]
    for i in range(n - 2, -1, -1):
        left, right = tree[2 * i + 1], tree[2 * i + 2]
        assert left is not None and right is not None
        tree[i] = _hash_pair(left, right)
    assert tree[0] is not None
    return tree[0]


def compute_proposal_id(
    call_id: str, title: str, description: str, file_hashes: list
) -> str:
    """Computa el identificador de propuesta como raíz del árbol de Merkle (compatible con OZ)."""
    call_leaf = bytes.fromhex(call_id[2:])
    title_leaf = bytes(Web3.keccak(text=title))
    desc_leaf = bytes(Web3.keccak(text=description))
    file_leaves = [bytes.fromhex(h[2:]) for h in file_hashes]
    leaves = sorted([call_leaf, title_leaf, desc_leaf] + file_leaves)
    return "0x" + _compute_merkle_root(leaves).hex()


def _merkle_proof_for(sorted_leaves: list, tree: list, leaf: bytes) -> list:
    n = len(sorted_leaves)
    pos = 2 * n - 2 - sorted_leaves.index(leaf)
    proof = []
    p = pos
    while p > 0:
        sibling = p + 1 if p % 2 == 1 else p - 1
        proof.append("0x" + tree[sibling].hex())
        p = (p - 1) // 2
    return proof


def compute_proposal_proofs(
    call_id: str, title: str, description: str, file_hashes: list
) -> dict:
    """Retorna el dict {leaf_hex: proof} que debe devolver el servidor."""
    call_leaf = bytes.fromhex(call_id[2:])
    title_leaf = bytes(Web3.keccak(text=title))
    desc_leaf = bytes(Web3.keccak(text=description))
    file_leaves = [bytes.fromhex(h[2:]) for h in file_hashes]
    all_leaves = [call_leaf, title_leaf, desc_leaf] + file_leaves
    sorted_leaves = sorted(all_leaves)
    tree: list[bytes | None] = [None] * (2 * len(sorted_leaves) - 1)
    n = len(sorted_leaves)
    for i in range(n):
        tree[2 * n - 2 - i] = sorted_leaves[i]
    for i in range(n - 2, -1, -1):
        left, right = tree[2 * i + 1], tree[2 * i + 2]
        assert left is not None and right is not None
        tree[i] = _hash_pair(left, right)
    return {
        "0x" + leaf.hex(): _merkle_proof_for(sorted_leaves, tree, leaf)
        for leaf in all_leaves
    }


def verify_merkle_proof(proof: list, root: str, leaf_hex: str) -> bool:
    """Verifica una prueba de Merkle compatible con OZ."""
    current = bytes.fromhex(leaf_hex[2:])
    for sibling in proof:
        current = _hash_pair(current, bytes.fromhex(sibling[2:]))
    return "0x" + current.hex() == root


def make_create_message(contract_address: str, call_id: str) -> SignableMessage:
    """Construye el mensaje a firmar para /create."""
    return make_eip712_message("CreateRequest", {
        "operation": "create",
        "contract": Web3.to_checksum_address(contract_address),
        "callId": bytes.fromhex(call_id[2:])
    }, contract_address)


def post_create(account: LocalAccount, title: str, description: str):
    """Registra un llamado en la API: genera callId, firma y envía POST /create."""
    call_id = make_call_id(title, description)
    factory, _ = get_factory_contract()
    signature = sign_bytes(make_create_message(factory.address, call_id), account)
    return requests.post(
        url("create"),
        json={
            "callId": call_id,
            "title": title,
            "description": description,
            "signature": signature,
        },
        timeout=10,
    )


def send_create_tx(account: LocalAccount, call_id: str, closing_time: datetime) -> None:
    """Llama a factory.create() en nombre de la cuenta dada."""
    w3 = get_w3()
    factory, _ = get_factory_contract()
    call_id_bytes = bytes.fromhex(call_id[2:])
    closing_ts = int(closing_time.timestamp())
    tx = factory.functions.create(call_id_bytes, closing_ts).build_transaction(
        {
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gas": 1500000,
            "gasPrice": w3.to_wei("1", "gwei"),
        }
    )
    signed = account.sign_transaction(tx)  # type: ignore[arg-type]
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)


def wait_for_call_status(call_id: str, expected_status: str, timeout: int = 15) -> bool:
    """Espera hasta que GET /calls/:call_id devuelva el estado esperado."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(url("calls", call_id), timeout=3)
        if resp.status_code == 200 and resp.json().get("status") == expected_status:
            get_w3().provider.make_request(RPCEndpoint("evm_mine"), [])
            return True
        time.sleep(0.5)
    return False


def post_register(address, signature, name="Test User"):
    """Registra una dirección."""
    return requests.post(
        url("register"),
        json={"address": address, "signature": signature, "name": name},
        timeout=10,
    )


def post_register_proposal(call_id, title, description, files=None):
    """Registra una propuesta enviando título, descripción y archivos."""
    return requests.post(
        url("register-proposal"),
        json={
            "callId": call_id,
            "title": title,
            "description": description,
            "files": files if files is not None else [],
        },
        timeout=10,
    )


def get_proposal_data(call_id, proposal):
    """Obtiene los datos de una propuesta."""
    return requests.get(url("proposal-data", f"{call_id}/{proposal}"), timeout=3)


def test_authorized_unknown_address() -> None:
    """Prueba que una dirección desconocida no esté autorizada."""
    for _ in range(10):
        response = requests.get(url("authorized", random_address()), timeout=3)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 200
        validate(instance=response.json(), schema=authorized_schema)
        assert response.json()["authorized"] is False


def test_authorized_invalid_address() -> None:
    """Prueba que una dirección inválida no esté autorizada."""
    addresses = [
        "x",
        "0",
        "0x",
        "0x0",
        random_address()[:-1],
        random_address()[:-2],
        random_hash(),
    ]
    for address in addresses:
        response = requests.get(url("authorized", address), timeout=3)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 400
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_ADDRESS)


def test_register() -> None:
    """Prueba el registro de una dirección previamente registrada on-chain."""
    contract_address = get_contract_address()
    for _ in range(10):
        account = Account().create()
        fund_account(account.address)
        send_register_tx(account)
        msg = make_register_message(contract_address, "Test User")
        signature = sign_bytes(msg, account)
        response = post_register(account.address, signature, "Test User")
        assert response.status_code == 200
        validate(instance=response.json(), schema=registration_status_schema)
        assert response.json()["status"] == "registered"
        accounts.append(account)


def test_register_again() -> None:
    """Prueba que una dirección ya registrada en la BD no pueda registrarse de nuevo."""
    assert len(accounts) > 0
    contract_address = get_contract_address()
    for account in accounts:
        msg = make_register_message(contract_address, "Test User")
        signature = sign_bytes(msg, account)
        response = post_register(account.address, signature, "Test User")
        assert response.status_code == 403
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.ALREADY_IN_SYSTEM)


def test_register_invalid_address() -> None:
    """Prueba que una dirección inválida no pueda registrarse."""
    signature = random_signature()
    addresses = [
        "x",
        "0",
        "0x",
        "0x0",
        random_address()[:-1],
        random_address()[:-2],
        random_hash(),
    ]
    for address in addresses:
        response = post_register(address, signature)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_ADDRESS)
        assert response.status_code == 400


def test_register_invalid_signature() -> None:
    """Prueba que una dirección con una firma inválida no pueda registrarse."""
    assert len(accounts) > 0
    contract_address = get_contract_address()
    # Firma de otra cuenta: cuentas frescas (no en BD) con firma de accounts[0]
    for _ in range(5):
        fresh = Account().create()
        msg = make_register_message(contract_address, "Test User")
        signature = sign_bytes(msg, accounts[0])  # firmado por otra cuenta
        response = post_register(fresh.address, signature)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
        assert response.status_code == 400
    # Formatos inválidos de firma
    account = Account().create()
    msg = make_register_message(contract_address, "Test User")
    overlong_sig = sign_bytes(msg, account) + "ab"
    invalid = [
        random_hash(),
        random_address(),
        random_hex(32),
        random_hex(64),
        overlong_sig,
        "signature",
    ]
    for signature in invalid:
        response = post_register(account.address, signature)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
        assert response.status_code == 400


def test_register_pending() -> None:
    """Prueba que el registro de una cuenta sin registro on-chain retorne estado 'pending'."""
    contract_address = get_contract_address()
    account = Account().create()
    msg = make_register_message(contract_address, "Pending User")
    signature = sign_bytes(msg, account)
    response = post_register(account.address, signature, "Pending User")
    assert response.status_code == 200
    validate(instance=response.json(), schema=registration_status_schema)
    assert response.json()["status"] == "pending"
    # GET también debe reflejar el estado pending
    reg = get_registration(account.address)
    assert reg.status_code == 200
    assert reg.json()["status"] == "pending"


def test_register_transition() -> None:
    """Prueba que el estado se actualice a 'registered'
    cuando el usuario llama a contract.register()."""
    contract_address = get_contract_address()
    account = Account().create()
    # POST /register antes del registro on-chain → pending
    msg = make_register_message(contract_address, "Transition User")
    response = post_register(
        account.address, sign_bytes(msg, account), "Transition User"
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    # Llamar contract.register() on-chain
    fund_account(account.address)
    send_register_tx(account)
    # El estado se computa consultando la cadena en tiempo real
    assert wait_for_registration_status(
        account.address, "registered"
    ), "El estado no se actualizó a 'registered' en el tiempo esperado"


def test_register_invalid_mimetype() -> None:
    """Prueba que el registro con un tipo de contenido inválido falle."""
    account = Account().create()
    signature = sign(account.address, account)
    response = requests.post(
        url("register"),
        data={"address": account.address, "signature": signature},
        timeout=10,
    )
    assert APPLICATION_JSON in response.headers["Content-type"]
    validate(instance=response.json(), schema=message_schema)
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_MIMETYPE)


def test_register_missing_field() -> None:
    """Prueba que el registro falle si falta algún campo requerido."""
    account = Account().create()
    contract_address = get_contract_address()
    signature = sign(contract_address, account)
    cases = [
        {"address": account.address, "signature": signature},  # missing name
        {"address": account.address, "name": "Test"},  # missing signature
        {"signature": signature, "name": "Test"},  # missing address
        {},
    ]
    for body in cases:
        response = requests.post(url("register"), json=body, timeout=10)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.status_code == 400
        assert response.json()["message"] == messages.MISSING_FIELD


def test_register_name_too_long() -> None:
    """Prueba que el registro falle si el nombre supera 512 bytes en UTF-8."""
    contract_address = get_contract_address()
    # 512 bytes ASCII → aceptado (cuenta fresca sin registro on-chain → pending)
    name_ok = "a" * 512
    account = Account().create()
    sig = sign_bytes(make_register_message(contract_address, name_ok), account)
    response = post_register(account.address, sig, name_ok)
    assert response.status_code == 200
    assert "status" in response.json()
    # 512 bytes con caracteres de 2 bytes (é = U+00E9): 256 chars = 512 bytes → aceptado
    name_multibyte_ok = "é" * 256
    account = Account().create()
    sig = sign_bytes(
        make_register_message(contract_address, name_multibyte_ok), account
    )
    response = post_register(account.address, sig, name_multibyte_ok)
    assert response.status_code == 200
    assert "status" in response.json()
    # 513 bytes ASCII → rechazado
    name_long = "a" * 513
    account = Account().create()
    sig = sign_bytes(make_register_message(contract_address, name_long), account)
    response = post_register(account.address, sig, name_long)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 400
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.NAME_TOO_LONG
    # 257 chars de 'é' = 514 bytes → rechazado
    name_multibyte_long = "é" * 257
    account = Account().create()
    sig = sign_bytes(
        make_register_message(contract_address, name_multibyte_long), account
    )
    response = post_register(account.address, sig, name_multibyte_long)
    assert response.status_code == 400
    assert response.json()["message"] == messages.NAME_TOO_LONG


def test_register_empty_name() -> None:
    """Prueba que el registro falle si el nombre es una string vacía."""
    contract_address = get_contract_address()
    account = Account().create()
    msg = make_register_message(contract_address, "")
    signature = sign_bytes(msg, account)
    response = post_register(account.address, signature, "")
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 400
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.INVALID_NAME


def test_register_whitespace_name() -> None:
    """Prueba que /register elimine trailing whitespace del nombre antes de validarlo."""
    contract_address = get_contract_address()
    # Solo espacios → vacío tras strip → INVALID_NAME
    account = Account().create()
    msg = make_register_message(contract_address, "")
    response = post_register(account.address, sign_bytes(msg, account), "   ")
    assert response.status_code == 400
    assert response.json()["message"] == messages.INVALID_NAME
    # Trailing spaces → aceptado; nombre almacenado sin espacios finales
    account = Account().create()
    raw_name = f"WS-{_run_id}   "
    stripped_name = raw_name.rstrip()
    msg = make_register_message(contract_address, stripped_name)
    response = post_register(account.address, sign_bytes(msg, account), raw_name)
    assert response.status_code == 200
    reg = get_registration(account.address)
    assert reg.status_code == 200
    assert reg.json()["name"] == stripped_name


def test_authorize_accounts() -> None:
    """Autoriza todas las cuentas registradas vía API y espera que el estado se actualice."""
    assert len(accounts) > 0
    contract_address = get_contract_address()
    admin = get_admin_account()
    for account in accounts:
        nonce = get_admin_nonce()
        msg = make_authorize_message(contract_address, nonce, account.address)
        resp = post_authorize(account.address, sign_bytes(msg, admin))
        assert resp.status_code == 200
    for account in accounts:
        assert wait_for_registration_status(
            account.address, "authorized"
        ), f"La cuenta {account.address} no fue autorizada en el tiempo esperado"


def test_authorized() -> None:
    """Prueba que las cuentas autorizadas estén marcadas como tal en el contrato."""
    assert len(accounts) > 0
    for account in accounts:
        response = requests.get(url("authorized", account.address), timeout=3)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 200
        validate(instance=response.json(), schema=authorized_schema)
        assert response.json()["authorized"]


def test_get_registration() -> None:
    """Prueba que se pueda obtener el nombre, nonce y estado de una dirección registrada."""
    assert len(accounts) > 0
    for account in accounts:
        response = get_registration(account.address)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 200
        validate(instance=response.json(), schema=registration_schema)
        assert response.json()["name"] == "Test User"
        assert response.json()["nonce"] == 1
        assert response.json()["status"] == "authorized"


def test_admin_nonce() -> None:
    """Prueba que GET /admin/nonce devuelva un entero positivo."""
    nonce = get_admin_nonce()
    assert isinstance(nonce, int) and nonce >= 1


def test_admin_pending() -> None:
    """Prueba que GET /admin/pending devuelva direcciones registradas on-chain pero no autorizadas."""
    contract_address = get_contract_address()
    # Registrar una cuenta on-chain sin autorizar
    account = Account().create()
    fund_account(account.address)
    send_register_tx(account)
    # No llamar POST /register (solo on-chain)
    response = requests.get(url("admin/pending"), timeout=3)
    assert response.status_code == 200
    data = response.json()
    assert "pending" in data
    assert isinstance(data["pending"], list)
    # La cuenta debe aparecer en la lista de pendientes
    pending_addrs = [p["address"].lower() for p in data["pending"]]
    assert account.address.lower() in pending_addrs, \
        "La cuenta registrada on-chain debería estar en getAllPending()"
    # Si la cuenta no está en la API, su name debe ser None
    for p in data["pending"]:
        if p["address"].lower() == account.address.lower():
            assert p["name"] is None, \
                "Cuenta solo on-chain debe tener name=None en /admin/pending"
            break


def test_api_authorize() -> None:
    """Prueba que el api_manager pueda autorizar una dirección vía API."""
    contract_address = get_contract_address()
    admin = get_admin_account()
    # Crear cuenta, registrarla on-chain y en la API
    account = Account().create()
    fund_account(account.address)
    send_register_tx(account)
    msg = make_register_message(contract_address, "API Auth User")
    post_register(account.address, sign_bytes(msg, account), "API Auth User")
    assert wait_for_registration_status(
        account.address, "registered"
    ), "El estado no llegó a 'registered'"
    # Autorizar vía API
    nonce = get_admin_nonce()
    auth_msg = make_authorize_message(contract_address, nonce, account.address)
    response = post_authorize(account.address, sign_bytes(auth_msg, admin))
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.OK
    # El estado debe ser 'authorized'
    reg = get_registration(account.address)
    assert reg.status_code == 200
    assert reg.json()["status"] == "authorized"
    # El nonce debe haber incrementado
    assert get_admin_nonce() == nonce + 1


def test_api_unauthorize() -> None:
    """Prueba que el api_manager pueda revocar la autorización de una dirección vía API."""
    contract_address = get_contract_address()
    admin = get_admin_account()
    account = Account().create()
    fund_account(account.address)
    send_register_tx(account)
    msg = make_register_message(contract_address, "API Unauth User")
    post_register(account.address, sign_bytes(msg, account), "API Unauth User")
    assert wait_for_registration_status(
        account.address, "registered"
    ), "El estado no llegó a 'registered'"
    # Autorizar vía API
    auth_nonce = get_admin_nonce()
    auth_msg = make_authorize_message(contract_address, auth_nonce, account.address)
    auth_resp = post_authorize(account.address, sign_bytes(auth_msg, admin))
    assert auth_resp.status_code == 200
    assert wait_for_registration_status(
        account.address, "authorized"
    ), "El estado no llegó a 'authorized'"
    # Revocar vía API
    nonce = get_admin_nonce()
    unauth_msg = make_unauthorize_message(contract_address, nonce, account.address)
    response = post_unauthorize(account.address, sign_bytes(unauth_msg, admin))
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.OK
    # Sin llamados creados → la cuenta se preserva en DB (anti-replay); GET devuelve datos preservados
    reg = get_registration(account.address)
    assert reg.status_code == 200
    assert reg.json()["status"] == "pending"
    assert reg.json()["name"] == "API Unauth User"
    assert reg.json()["nonce"] == 1
    # El nonce debe haber incrementado
    assert get_admin_nonce() == nonce + 1


def test_api_authorize_not_registered() -> None:
    """Prueba que /authorize falle con 404 si la dirección no está registrada en la API."""
    contract_address = get_contract_address()
    admin = get_admin_account()
    nonce = get_admin_nonce()
    account = Account().create()  # nunca llamó a POST /register
    msg = make_authorize_message(contract_address, nonce, account.address)
    response = post_authorize(account.address, sign_bytes(msg, admin))
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 404
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.NOT_REGISTERED
    # El nonce no debe haber cambiado
    assert get_admin_nonce() == nonce


def test_api_authorize_invalid_signature() -> None:
    """Prueba errores de firma en /authorize y /unauthorize."""
    contract_address = get_contract_address()
    admin = get_admin_account()
    target = Account().create()
    nonce = get_admin_nonce()
    # Firmante incorrecto (cuenta aleatoria, no el api_manager)
    impostor = Account().create()
    wrong_signer_sig = sign_bytes(
        make_authorize_message(contract_address, nonce, target.address), impostor
    )
    response = post_authorize(target.address, wrong_signer_sig)
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Nonce incorrecto (current + 1)
    wrong_nonce_sig = sign_bytes(
        make_authorize_message(contract_address, nonce + 1, target.address), admin
    )
    response = post_authorize(target.address, wrong_nonce_sig)
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Dirección objetivo incorrecta (firma para otra dirección)
    other = Account().create()
    wrong_target_sig = sign_bytes(
        make_authorize_message(contract_address, nonce, other.address), admin
    )
    response = post_authorize(target.address, wrong_target_sig)
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Formatos inválidos de firma
    overlong = (
        sign_bytes(
            make_authorize_message(contract_address, nonce, target.address), admin
        )
        + "ab"
    )
    for sig in [random_hash(), random_address(), random_hex(64), overlong, "signature"]:
        response = post_authorize(target.address, sig)
        assert response.status_code == 400
        assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Nonce no debe haber cambiado
    assert get_admin_nonce() == nonce


def test_api_authorize_invalid_address() -> None:
    """Prueba que una dirección inválida en /authorize y /unauthorize devuelva 400."""
    admin = get_admin_account()
    contract_address = get_contract_address()
    nonce = get_admin_nonce()
    addresses = ["x", "0", "0x", "0x0", random_address()[:-1], random_hash()]
    for address in addresses:
        valid_target = Account().create()
        sig = sign_bytes(
            make_authorize_message(contract_address, nonce, valid_target.address), admin
        )
        response = post_authorize(address, sig)
        assert response.status_code == 400
        assert response.json()["message"].startswith(messages.INVALID_ADDRESS)
        response = post_unauthorize(address, sig)
        assert response.status_code == 400
        assert response.json()["message"].startswith(messages.INVALID_ADDRESS)


def test_get_registration_unknown_address() -> None:
    """Prueba que una dirección desconocida devuelva status 'pending'."""
    for _ in range(5):
        response = get_registration(random_address())
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 200
        validate(instance=response.json(), schema=registration_status_schema)
        assert response.json()["status"] == "pending"


def test_get_registration_invalid_address() -> None:
    """Prueba que una dirección inválida en GET /registrations devuelva 400."""
    addresses = [
        "x",
        "0",
        "0x",
        "0x0",
        random_address()[:-1],
        random_address()[:-2],
        random_hash(),
    ]
    for address in addresses:
        response = get_registration(address)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 400
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_ADDRESS)


def test_update_registration() -> None:
    """Prueba que se pueda actualizar el nombre de una dirección registrada."""
    assert len(accounts) > 0
    contract_address = get_contract_address()
    for account in accounts:
        for new_name in ["Nombre Actualizado", "Nombre Actualizado 2"]:
            reg = get_registration(account.address)
            nonce = reg.json()["nonce"]
            msg = make_update_message(contract_address, nonce, new_name)
            signature = sign_bytes(msg, account)
            response = patch_registration(account.address, new_name, signature)
            assert APPLICATION_JSON in response.headers["Content-type"]
            assert response.status_code == 200
            validate(instance=response.json(), schema=message_schema)
            assert response.json()["message"] == messages.OK
            reg = get_registration(account.address)
            assert reg.json()["name"] == new_name
            assert reg.json()["nonce"] == nonce + 1


def test_update_registration_invalid_mimetype() -> None:
    """Prueba que la actualización con tipo de contenido incorrecto devuelva 400."""
    assert len(accounts) > 0
    account = accounts[0]
    response = requests.patch(
        url("registrations", account.address),
        data={"name": "Test", "signature": random_signature()},
        timeout=10,
    )
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 400
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.INVALID_MIMETYPE)


def test_update_registration_missing_field() -> None:
    """Prueba que la actualización falle si falta algún campo requerido."""
    assert len(accounts) > 0
    address = accounts[0].address
    cases = [
        {"name": "Test"},  # falta signature
        {"signature": random_signature()},  # falta name
        {},
    ]
    for body in cases:
        response = requests.patch(url("registrations", address), json=body, timeout=10)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.status_code == 400
        assert response.json()["message"] == messages.MISSING_FIELD


def test_update_registration_name_too_long() -> None:
    """Prueba que la actualización falle si el nombre supera 512 bytes en UTF-8."""
    assert len(accounts) > 0
    account = accounts[0]
    contract_address = get_contract_address()
    nonce = get_registration(account.address).json()["nonce"]
    # 513 bytes ASCII → rechazado
    name_long = "a" * 513
    msg = make_update_message(contract_address, nonce, name_long)
    response = patch_registration(account.address, name_long, sign_bytes(msg, account))
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 400
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.NAME_TOO_LONG
    # 257 chars de 'é' = 514 bytes → rechazado
    name_multibyte_long = "é" * 257
    msg = make_update_message(contract_address, nonce, name_multibyte_long)
    response = patch_registration(
        account.address, name_multibyte_long, sign_bytes(msg, account)
    )
    assert response.status_code == 400
    assert response.json()["message"] == messages.NAME_TOO_LONG
    # El nonce no debe haber cambiado
    assert get_registration(account.address).json()["nonce"] == nonce


def test_update_registration_empty_name() -> None:
    """Prueba que la actualización falle si el nombre es una string vacía."""
    assert len(accounts) > 0
    account = accounts[0]
    contract_address = get_contract_address()
    nonce = get_registration(account.address).json()["nonce"]
    msg = make_update_message(contract_address, nonce, "")
    response = patch_registration(account.address, "", sign_bytes(msg, account))
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 400
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.INVALID_NAME
    # El nonce no debe haber cambiado
    assert get_registration(account.address).json()["nonce"] == nonce


def test_update_registration_whitespace_name() -> None:
    """Prueba que PATCH /registrations elimine trailing whitespace del nombre."""
    assert len(accounts) > 0
    account = accounts[0]
    contract_address = get_contract_address()
    nonce = get_registration(account.address).json()["nonce"]
    # Solo espacios → INVALID_NAME; nonce no cambia
    msg = make_update_message(contract_address, nonce, "")
    response = patch_registration(account.address, "   ", sign_bytes(msg, account))
    assert response.status_code == 400
    assert response.json()["message"] == messages.INVALID_NAME
    assert get_registration(account.address).json()["nonce"] == nonce
    # Trailing spaces → aceptado; nombre almacenado sin espacios finales
    raw_name = f"WS-patch-{_run_id}   "
    stripped_name = raw_name.rstrip()
    msg = make_update_message(contract_address, nonce, stripped_name)
    response = patch_registration(account.address, raw_name, sign_bytes(msg, account))
    assert response.status_code == 200
    reg = get_registration(account.address)
    assert reg.json()["name"] == stripped_name
    assert reg.json()["nonce"] == nonce + 1


def test_update_registration_not_found() -> None:
    """Prueba que la actualización de una dirección no registrada devuelva 404."""
    account = Account().create()
    msg = make_update_message(get_contract_address(), 1, "Test")
    signature = sign_bytes(msg, account)
    response = patch_registration(account.address, "Test", signature)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 404
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.NOT_REGISTERED


def test_update_registration_invalid_address() -> None:
    """Prueba que una dirección inválida en PATCH /registrations devuelva 400."""
    addresses = [
        "x",
        "0",
        "0x",
        "0x0",
        random_address()[:-1],
        random_address()[:-2],
        random_hash(),
    ]
    for address in addresses:
        response = requests.patch(
            url("registrations", address),
            json={"name": "Test", "signature": random_signature()},
            timeout=10,
        )
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 400
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_ADDRESS)


def test_update_registration_invalid_signature() -> None:
    """Prueba que la actualización con firma inválida devuelva 400."""
    assert len(accounts) > 1
    contract_address = get_contract_address()
    # Cuenta incorrecta: firma válida pero de otra cuenta
    for account in accounts[1:]:
        reg = get_registration(account.address)
        nonce = reg.json()["nonce"]
        msg = make_update_message(contract_address, nonce, "Test")
        signature = sign_bytes(msg, accounts[0])  # firmado por accounts[0]
        response = patch_registration(account.address, "Test", signature)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 400
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    account = accounts[0]
    reg = get_registration(account.address)
    nonce = reg.json()["nonce"]
    # Prefijo incorrecto: firma de /register usada en PATCH (separación de dominio)
    msg_register = make_register_message(contract_address, "Test")
    response = patch_registration(
        account.address, "Test", sign_bytes(msg_register, account)
    )
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Nonce stale: nonce anterior ya usado
    msg_stale = make_update_message(contract_address, nonce - 1, "Test")
    response = patch_registration(
        account.address, "Test", sign_bytes(msg_stale, account)
    )
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Nonce futuro
    msg_future = make_update_message(contract_address, nonce + 1, "Test")
    response = patch_registration(
        account.address, "Test", sign_bytes(msg_future, account)
    )
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Nombre incorrecto: firma cubre "A" pero se envía "B"
    msg_wrong_name = make_update_message(contract_address, nonce, "Nombre Correcto")
    response = patch_registration(
        account.address, "Nombre Incorrecto", sign_bytes(msg_wrong_name, account)
    )
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
    # Formatos inválidos
    fresh = Account().create()
    overlong_sig = (
        sign_bytes(make_update_message(contract_address, 1, "Test"), fresh) + "ab"
    )
    for signature in [
        random_hash(),
        random_address(),
        random_hex(64),
        overlong_sig,
        "signature",
    ]:
        response = patch_registration(account.address, "Test", signature)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 400
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)


def test_create_unauthorized() -> None:
    """Prueba que una dirección no autorizada no pueda registrar un llamado."""
    account = Account().create()
    title = "Llamado sin autorización"
    description = "Descripción de prueba"
    response = post_create(account, title, description)
    assert APPLICATION_JSON in response.headers["Content-type"]
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.UNAUTHORIZED)
    assert response.status_code == 403


def test_create_invalid_signature() -> None:
    """Prueba que una firma inválida rechace el registro del llamado."""
    title = "Llamado de prueba"
    description = "Descripción de prueba"
    call_id = make_call_id(title, description)
    factory, _ = get_factory_contract()
    overlong_sig = (
        sign_bytes(make_create_message(factory.address, call_id), Account().create())
        + "ab"
    )
    invalid = [
        random_hash(),
        random_address(),
        random_hex(64),
        overlong_sig,
        "signature",
    ]
    for signature in invalid:
        response = requests.post(
            url("create"),
            json={
                "callId": call_id,
                "title": title,
                "description": description,
                "signature": signature,
            },
            timeout=10,
        )
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_SIGNATURE)
        assert response.status_code == 400


def test_create_invalid_mimetype() -> None:
    """Prueba que la creación con tipo de contenido inválido falle."""
    account = Account().create()
    title = "Llamado de prueba"
    description = "Descripción de prueba"
    call_id = make_call_id(title, description)
    factory, _ = get_factory_contract()
    signature = sign_bytes(make_create_message(factory.address, call_id), account)
    response = requests.post(
        url("create"),
        data={
            "callId": call_id,
            "title": title,
            "description": description,
            "signature": signature,
        },
        timeout=10,
    )
    assert APPLICATION_JSON in response.headers["Content-type"]
    validate(instance=response.json(), schema=message_schema)
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_MIMETYPE)


def test_create_missing_field() -> None:
    """Prueba que la creación falle si falta algún campo requerido."""
    title = "Llamado de prueba"
    description = "Descripción de prueba"
    call_id = make_call_id(title, description)
    signature = random_signature()
    cases = [
        {"title": title, "description": description, "signature": signature},
        {"callId": call_id, "description": description, "signature": signature},
        {"callId": call_id, "title": title, "signature": signature},
        {"callId": call_id, "title": title, "description": description},
        {},
    ]
    for body in cases:
        response = requests.post(url("create"), json=body, timeout=10)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.status_code == 400
        assert response.json()["message"] == messages.MISSING_FIELD


def test_create() -> None:
    """Prueba que una cuenta autorizada pueda registrar un llamado y que el contrato lo confirme."""
    assert len(accounts) > 0
    for i, account in enumerate(accounts):
        title = f"Llamado {_run_id}-{i}"
        description = f"Descripción {_run_id}-{i}"
        closing_time = get_closing_time()
        response = post_create(account, title, description)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"] == messages.OK
        assert response.status_code == 201
        call_id = make_call_id(title, description)
        send_create_tx(account, call_id, closing_time)
        assert wait_for_call_status(
            call_id, "created"
        ), f"El llamado {call_id} no alcanzó estado 'created'"
        calls[call_id] = {
            "account": account,
            "title": title,
            "description": description,
            "closingTime": closing_time,
        }


def test_create_invalid_call_id() -> None:
    """Prueba que un callId con formato inválido sea rechazado."""
    title = "Título de prueba"
    description = "Descripción de prueba"
    invalid = [
        "00ab",
        "0xab",
        "0x00",
        random_hash()[:-2],
        random_address(),
        random_hash() + "ab",
    ]
    for call_id in invalid:
        response = requests.post(
            url("create"),
            json={
                "callId": call_id,
                "title": title,
                "description": description,
                "signature": random_signature(),
            },
            timeout=10,
        )
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_CALLID)
        assert response.status_code == 400


def test_create_pending_status() -> None:
    """Prueba que un llamado recién registrado en la API tenga estado 'pending'."""
    assert len(accounts) > 0
    title = f"Pendiente {_run_id}"
    description = f"Sin blockchain {_run_id}"
    response = post_create(accounts[0], title, description)
    assert response.status_code == 201
    call_id = make_call_id(title, description)
    resp = requests.get(url("calls", call_id), timeout=3)
    assert resp.status_code == 200
    validate(instance=resp.json(), schema=calls_pending_schema)
    assert resp.json()["status"] == "pending"
    assert resp.json()["title"] == title
    assert resp.json()["description"] == description


def test_create_call_id_mismatch() -> None:
    """Prueba que un callId válido pero que no coincide con título/descripción sea rechazado."""
    title = "Título"
    description = "Descripción"
    correct_call_id = make_call_id(title, description)
    wrong_call_id = random_hash()
    while wrong_call_id == correct_call_id:
        wrong_call_id = random_hash()
    response = requests.post(
        url("create"),
        json={
            "callId": wrong_call_id,
            "title": title,
            "description": description,
            "signature": random_signature(),
        },
        timeout=10,
    )
    assert APPLICATION_JSON in response.headers["Content-type"]
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.INVALID_CALLID)
    assert response.status_code == 400


def test_already_created() -> None:
    """Prueba que un llamado ya registrado en la API no pueda registrarse de nuevo."""
    assert len(calls) > 0
    for _, data in calls.items():
        response = post_create(data["account"], data["title"], data["description"])
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.ALREADY_CREATED)
        assert response.status_code == 403


def test_calls() -> None:
    """Prueba que los datos de un llamado creado sean correctos."""
    assert len(calls) > 0
    for call_id, data in calls.items():
        response = requests.get(url("calls", call_id), timeout=3)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 200
        validate(instance=response.json(), schema=calls_created_schema)
        assert response.json()["creator"] == data["account"].address
        assert response.json()["title"] == data["title"]
        assert response.json()["description"] == data["description"]
        assert response.json()["status"] == "created"
        data["cfp"] = response.json()["cfp"]
    response = requests.get(url("calls", random_hash()), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 404
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.CALLID_NOT_FOUND)
    invalid = [
        "00ab",
        "0xab",
        "0x00",
        random_hash()[:-2],
        random_address(),
        random_hash() + "ab",
    ]
    for call_id in invalid:
        response = requests.get(url("calls", call_id), timeout=3)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 400
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_CALLID)


def test_calls_not_in_api() -> None:
    """Prueba que un llamado creado on-chain sin pasar por POST /create devuelva 404."""
    assert len(accounts) > 0
    title = f"Directo {_run_id}"
    description = f"Sin API {_run_id}"
    call_id = make_call_id(title, description)
    closing_time = get_closing_time()
    send_create_tx(accounts[0], call_id, closing_time)
    response = requests.get(url("calls", call_id), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 404
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.CALLID_NOT_FOUND)


def test_get_calls_list_empty() -> None:
    """Verifica que GET /calls devuelva lista vacia antes de crear llamados."""
    response = requests.get(url("calls"), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    assert isinstance(response.json()["calls"], list)
    # La lista vacia es valida si no hay llamados creados on-chain.
    # Los llamados en estado 'pending' (sin confirmar on-chain) no aparecen.


def test_get_calls_list_after_creation() -> None:
    """Verifica que GET /calls incluya los llamados creados tras confirmacion on-chain."""
    assert len(calls) > 0
    response = requests.get(url("calls"), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["calls"], list)
    call_ids_on_chain = set()
    for c in body["calls"]:
        call_ids_on_chain.add(c["call_id"])
        assert c["status"] == "created"
        assert "creator" in c
        assert "cfp_address" in c
    # Todos los llamados creados via fixture deberian estar en la lista
    for call_id in calls:
        assert call_id in call_ids_on_chain


def test_get_calls_filtered_by_creator() -> None:
    """Verifica que GET /calls?creator=0x... filtre correctamente por creador."""
    assert len(accounts) > 0
    creator_address = accounts[0].address
    response = requests.get(
        f"{SERVER}/calls?creator={creator_address}", timeout=3
    )
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["calls"], list)
    for c in body["calls"]:
        assert c["creator"].lower() == creator_address.lower()
    # Llamados de otro creador no deberian aparecer
    other_creator = accounts[1].address if len(accounts) > 1 else creator_address
    response2 = requests.get(
        f"{SERVER}/calls?creator={other_creator}", timeout=3
    )
    assert response2.status_code == 200
    for c in response2.json()["calls"]:
        assert c["creator"].lower() == other_creator.lower()


def test_created_closing_time() -> None:
    """Prueba que el tiempo de cierre de una llamada creada sea correcto."""
    assert len(calls) > 0
    for call_id, data in calls.items():
        response = requests.get(url("closing-time", call_id), timeout=3)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 200
        validate(instance=response.json(), schema=closing_time_schema)
        closing_time = isoparse(response.json()["closingTime"])
        assert closing_time == data["closingTime"]
    response = requests.get(url("closing-time", random_hash()), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 404
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.CALLID_NOT_FOUND)
    invalid = [
        "00ab",
        "0xab",
        "0x00",
        random_hash()[:-2],
        random_address(),
        random_hash() + "ab",
    ]
    for call_id in invalid:
        response = requests.get(url("closing-time", call_id), timeout=3)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 400
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_CALLID)


def test_contract_address() -> None:
    """Prueba que devuelva la dirección del contrato."""
    get_contract_address()


def test_contract_owner() -> None:
    """Prueba que devuelva la dirección del propietario del contrato."""
    get_contract_owner()


def test_register_proposal() -> None:
    """Prueba que una dirección registrada pueda registrar una propuesta una sola vez."""
    assert len(calls) > 0
    block_number = 0
    timestamp = 0
    for call_id in calls:
        title = f"Propuesta {_run_id}"
        description = f"Descripción {_run_id}"
        files = [random_hash(), random_hash()]
        proposal_id = compute_proposal_id(call_id, title, description, files)
        response = post_register_proposal(call_id, title, description, files)
        assert APPLICATION_JSON in response.headers["Content-type"]
        assert response.status_code == 201
        validate(instance=response.json(), schema=register_proposal_schema)
        assert response.json()["message"] == messages.OK
        assert response.json()["proposalId"] == proposal_id
        proof = response.json()["proof"]
        expected_proofs = compute_proposal_proofs(call_id, title, description, files)
        assert proof == expected_proofs
        for leaf_hex, siblings in proof.items():
            assert verify_merkle_proof(siblings, proposal_id, leaf_hex)
        response = get_proposal_data(call_id, proposal_id)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=proposal_data_schema)
        assert response.status_code == 200
        pd = response.json()
        assert pd["sender"] == get_contract_owner()
        new_block_number = pd["blockNumber"]
        assert isinstance(new_block_number, int)
        assert new_block_number > 0 and new_block_number > block_number
        block_number = new_block_number
        new_timestamp = isoparse(pd["timestamp"]).timestamp()
        assert new_timestamp > 0 and new_timestamp >= timestamp
        timestamp = new_timestamp
        assert pd["estado"] in ("open", "closed")
        assert pd["title"] == title
        assert pd["description"] == description
        call_key = call_id.lower()
        title_key = "0x" + bytes(Web3.keccak(text=title)).hex()
        desc_key = "0x" + bytes(Web3.keccak(text=description)).hex()
        assert set(pd["proof"].keys()) == {call_key, title_key, desc_key}
        for leaf_hex, siblings in pd["proof"].items():
            assert verify_merkle_proof(siblings, proposal_id, leaf_hex)
        response = post_register_proposal(call_id, title, description, files)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.status_code == 403
        assert response.json()["message"].startswith(messages.ALREADY_REGISTERED)


def test_register_proposal_invalid_mimetype() -> None:
    """Prueba que el registro de propuesta falle con un mimetype inválido."""
    assert len(calls) > 0
    for call_id in calls:
        response = requests.post(
            url("register-proposal"),
            data={"callId": call_id, "title": "t", "description": "d", "files": []},
            timeout=10,
        )
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"].startswith(messages.INVALID_MIMETYPE)
        assert response.status_code == 400


def test_register_proposal_missing_field() -> None:
    """Prueba que el registro de propuesta falle si falta algún campo requerido."""
    call_id = random_hash()
    cases = [
        {"title": "t", "description": "d", "files": []},
        {"callId": call_id, "description": "d", "files": []},
        {"callId": call_id, "title": "t", "files": []},
        {"callId": call_id, "title": "t", "description": "d"},
        {},
    ]
    for body in cases:
        response = requests.post(url("register-proposal"), json=body, timeout=10)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.status_code == 400
        assert response.json()["message"] == messages.MISSING_FIELD


def test_register_proposal_invalid_call() -> None:
    """Prueba que el registro de propuesta falle con un callId inexistente o inválido."""
    title, description = "t", "d"
    call_id = random_hash()
    response = post_register_proposal(call_id, title, description)
    assert APPLICATION_JSON in response.headers["Content-type"]
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.CALLID_NOT_FOUND)
    assert response.status_code == 404
    invalid = [
        "x",
        "0x",
        "0x0",
        random_hash()[:-2],
        random_address(),
        random_hash() + "ab",
    ]
    for call_id in invalid:
        response = post_register_proposal(call_id, title, description)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.status_code == 400
        assert response.json()["message"].startswith(messages.INVALID_CALLID)


def test_register_proposal_invalid_proposal() -> None:
    """Prueba que el registro de propuesta falle si files no es una lista
    o contiene hashes inválidos."""
    assert len(calls) > 0
    title, description = "t", "d"
    invalid_files_cases = [
        "not-a-list",
        42,
        {"key": random_hash()},
        ["x", random_hash()],
        ["0x", random_hash()],
        [random_hash()[:-2], random_hash()],
        [random_hash() + "ab"],
    ]
    for call_id in calls:
        for bad_files in invalid_files_cases:
            response = requests.post(
                url("register-proposal"),
                json={
                    "callId": call_id,
                    "title": title,
                    "description": description,
                    "files": bad_files,
                },
                timeout=10,
            )
            assert APPLICATION_JSON in response.headers["Content-type"]
            validate(instance=response.json(), schema=message_schema)
            assert response.status_code == 400
            assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)


def test_register_proposal_duplicate_files() -> None:
    """Prueba que /register-proposal rechace listas de files con hashes duplicados."""
    assert len(calls) > 0
    call_id = next(iter(calls))
    # Dos hashes iguales → rechazado
    dup = random_hash()
    response = post_register_proposal(call_id, "t", "d", [dup, dup])
    assert APPLICATION_JSON in response.headers["Content-type"]
    validate(instance=response.json(), schema=message_schema)
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)
    # Duplicado en posición no adyacente → rechazado
    h1, h2 = random_hash(), random_hash()
    response = post_register_proposal(call_id, "t", "d", [h1, h2, h1])
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)
    # Un solo hash repetido tres veces → rechazado
    h = random_hash()
    response = post_register_proposal(call_id, "t", "d", [h, h, h])
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)
    # Lista sin duplicados con varios archivos → aceptado
    h1, h2, h3 = random_hash(), random_hash(), random_hash()
    response = post_register_proposal(
        call_id, f"Sin-dup-{_run_id}", f"Sin duplicados {_run_id}", [h1, h2, h3]
    )
    assert response.status_code == 201


def test_proposal_data_invalid_input() -> None:
    """Prueba que no se pueda obtener la información de una propuesta con un input inválido."""
    assert len(calls) > 0
    for call_id in calls:
        proposal = random_hash()
        response = get_proposal_data(call_id, proposal)
        assert APPLICATION_JSON in response.headers["Content-type"]
        validate(instance=response.json(), schema=message_schema)
        assert response.json()["message"] == messages.PROPOSAL_NOT_FOUND
        assert response.status_code == 404
        invalid = [
            "x",
            "0x",
            "0x0",
            random_hash()[:-2],
            random_address(),
            random_hash() + "ab",
        ]
        for invalid_hash in invalid:
            response = get_proposal_data(call_id, invalid_hash)
            assert APPLICATION_JSON in response.headers["Content-type"]
            validate(instance=response.json(), schema=message_schema)
            assert response.status_code == 400
            assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)
            response = get_proposal_data(invalid_hash, random_hash())
            assert APPLICATION_JSON in response.headers["Content-type"]
            validate(instance=response.json(), schema=message_schema)
            assert response.status_code == 400
            assert response.json()["message"].startswith(messages.INVALID_CALLID)
    response = get_proposal_data(random_hash(), random_hash())
    assert APPLICATION_JSON in response.headers["Content-type"]
    validate(instance=response.json(), schema=message_schema)
    assert response.status_code == 404
    assert response.json()["message"].startswith(messages.CALLID_NOT_FOUND)


def test_update_registration_name_limit() -> None:
    """Prueba que PATCH /registrations acepte nombres de exactamente 512 bytes en UTF-8."""
    assert len(accounts) > 0
    account = accounts[0]
    contract_address = get_contract_address()
    nonce = get_registration(account.address).json()["nonce"]
    # 512 bytes ASCII → aceptado
    name_512 = "a" * 512
    msg = make_update_message(contract_address, nonce, name_512)
    response = patch_registration(account.address, name_512, sign_bytes(msg, account))
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    assert response.json()["message"] == messages.OK
    nonce = get_registration(account.address).json()["nonce"]
    # 256 chars de 'é' = 512 bytes → aceptado
    name_512_multibyte = "é" * 256
    msg = make_update_message(contract_address, nonce, name_512_multibyte)
    response = patch_registration(
        account.address, name_512_multibyte, sign_bytes(msg, account)
    )
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    assert response.json()["message"] == messages.OK


def test_closing_time_pending_call() -> None:
    """Prueba que /closing-time devuelva 404 para un callId solo registrado en la API (pending)."""
    assert len(accounts) > 0
    title = f"Pendiente-CT-{_run_id}"
    description = f"Sin blockchain CT {_run_id}"
    response = post_create(accounts[0], title, description)
    assert response.status_code == 201
    call_id = make_call_id(title, description)
    # Verificar que el llamado está en estado pending (no está en el contrato)
    resp = requests.get(url("calls", call_id), timeout=3)
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"
    # /closing-time consulta el contrato directamente: debe devolver 404
    response = requests.get(url("closing-time", call_id), timeout=3)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 404
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"].startswith(messages.CALLID_NOT_FOUND)


def test_create_title_and_description_limits() -> None:
    """Prueba los límites de longitud de título (512 bytes) y descripción (4096 bytes)
    en /create."""
    assert len(accounts) > 0
    account = accounts[0]
    # _run_id son 8 bytes ASCII (4 bytes de urandom en hex)
    # Título de exactamente 512 bytes ASCII → aceptado
    title_512 = "a" * 504 + _run_id  # 504 + 8 = 512 bytes
    description = "d"
    response = post_create(account, title_512, description)
    assert response.status_code == 201, f"512-byte title rejected: {response.json()}"
    # Título de 513 bytes → rechazado
    title_513 = "a" * 513
    call_id_bad = make_call_id(title_513, description)
    factory, _ = get_factory_contract()
    sig = sign_bytes(make_create_message(factory.address, call_id_bad), account)
    response = requests.post(
        url("create"),
        json={
            "callId": call_id_bad,
            "title": title_513,
            "description": description,
            "signature": sig,
        },
        timeout=10,
    )
    assert response.status_code == 400
    assert response.json()["message"] == messages.TITLE_TOO_LONG
    # Título multibyte: 252 × 'é' (2 bytes c/u) + _run_id (8 bytes) = 512 bytes → aceptado
    title_512_mb = "é" * 252 + _run_id
    response = post_create(account, title_512_mb, description)
    assert (
        response.status_code == 201
    ), f"512-byte multibyte title rejected: {response.json()}"
    # Descripción de exactamente 4096 bytes ASCII → aceptada
    title = f"t-{_run_id}"
    desc_4096 = "d" * 4096
    response = post_create(account, title, desc_4096)
    assert (
        response.status_code == 201
    ), f"4096-byte description rejected: {response.json()}"
    # Descripción de 4097 bytes → rechazada
    desc_4097 = "d" * 4097
    call_id_bad = make_call_id(title, desc_4097)
    sig = sign_bytes(make_create_message(factory.address, call_id_bad), account)
    response = requests.post(
        url("create"),
        json={
            "callId": call_id_bad,
            "title": title,
            "description": desc_4097,
            "signature": sig,
        },
        timeout=10,
    )
    assert response.status_code == 400
    assert response.json()["message"] == messages.DESCRIPTION_TOO_LONG


def test_create_whitespace_title_description() -> None:
    """Prueba que /create elimine trailing whitespace de título y descripción."""
    assert len(accounts) > 0
    account = accounts[0]
    factory, _ = get_factory_contract()
    # Título solo con espacios → INVALID_TITLE
    call_id = make_call_id("", "desc")
    sig = sign_bytes(make_create_message(factory.address, call_id), account)
    response = requests.post(
        url("create"),
        json={
            "callId": call_id,
            "title": "   ",
            "description": "desc",
            "signature": sig,
        },
        timeout=10,
    )
    assert response.status_code == 400
    assert response.json()["message"] == messages.INVALID_TITLE
    # Título con trailing spaces → aceptado; callId calculado con título sin espacios
    raw_title = f"WS-create-{_run_id}   "
    stripped_title = raw_title.rstrip()
    call_id = make_call_id(stripped_title, "desc")
    sig = sign_bytes(make_create_message(factory.address, call_id), account)
    response = requests.post(
        url("create"),
        json={
            "callId": call_id,
            "title": raw_title,
            "description": "desc",
            "signature": sig,
        },
        timeout=10,
    )
    assert response.status_code == 201
    # Descripción solo con espacios → aceptado (descripción vacía es válida)
    title = f"WS-desc-{_run_id}"
    call_id = make_call_id(title, "")
    sig = sign_bytes(make_create_message(factory.address, call_id), account)
    response = requests.post(
        url("create"),
        json={
            "callId": call_id,
            "title": title,
            "description": "   ",
            "signature": sig,
        },
        timeout=10,
    )
    assert response.status_code == 201


def test_register_proposal_limits() -> None:
    """Prueba los límites de título, descripción, cantidad de archivos y prueba
    en /register-proposal."""
    assert len(calls) > 0
    call_id = next(iter(calls))
    # Título de 513 bytes → rechazado
    response = post_register_proposal(call_id, "a" * 513, "d", [])
    assert response.status_code == 400
    assert response.json()["message"] == messages.TITLE_TOO_LONG
    # Descripción de 4097 bytes → rechazada
    response = post_register_proposal(call_id, "t", "d" * 4097, [])
    assert response.status_code == 400
    assert response.json()["message"] == messages.DESCRIPTION_TOO_LONG
    # 126 archivos (> 125) → rechazado
    too_many = [random_hash() for _ in range(126)]
    response = post_register_proposal(call_id, "t", "d", too_many)
    assert response.status_code == 400
    assert response.json()["message"] == messages.TOO_MANY_FILES
    # 125 archivos → aceptado (128 hojas en total)
    title = f"Max-files-{_run_id}"
    description = f"125 archivos {_run_id}"
    max_files = [random_hash() for _ in range(125)]
    response = post_register_proposal(call_id, title, description, max_files)
    assert response.status_code == 201, f"125 files rejected: {response.json()}"
    # Todas las pruebas deben tener como máximo 7 elementos (log2(128) = 7)
    proof = response.json()["proof"]
    assert len(proof) == 128  # 125 archivos + callId + title + description
    for leaf_hex, siblings in proof.items():
        assert (
            len(siblings) <= 7
        ), f"Prueba de hoja {leaf_hex} tiene {len(siblings)} elementos (máximo 7)"


def test_register_proposal_whitespace() -> None:
    """Prueba que /register-proposal elimine trailing whitespace de título y descripción."""
    assert len(calls) > 0
    call_id = next(iter(calls))
    # Título solo con espacios → INVALID_TITLE
    response = post_register_proposal(call_id, "   ", "desc", [])
    assert response.status_code == 400
    assert response.json()["message"] == messages.INVALID_TITLE
    # Título con trailing spaces → aceptado; proposalId calculado con título sin espacios
    raw_title = f"WS-prop-{_run_id}   "
    stripped_title = raw_title.rstrip()
    response = post_register_proposal(call_id, raw_title, "desc", [])
    assert response.status_code == 201
    expected_id = compute_proposal_id(call_id, stripped_title, "desc", [])
    assert response.json()["proposalId"] == expected_id
    # Descripción solo con espacios → aceptado (descripción vacía es válida)
    title = f"WS-prop-desc-{_run_id}"
    response = post_register_proposal(call_id, title, "   ", [])
    assert response.status_code == 201
    expected_id = compute_proposal_id(call_id, title, "", [])
    assert response.json()["proposalId"] == expected_id


def test_verify_proof_too_long() -> None:
    """Prueba que /verify-proof rechace una prueba con más de 7 elementos."""
    response = post_verify_proof(
        random_hash(), random_hash(), [random_hash() for _ in range(8)]
    )
    assert response.status_code == 400
    assert response.json()["message"] == messages.PROOF_TOO_LONG
    # 7 elementos → no rechazado por longitud (puede ser inválido, pero no TOO_LONG)
    response = post_verify_proof(
        random_hash(), random_hash(), [random_hash() for _ in range(7)]
    )
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_register_proposal_no_files() -> None:
    """Prueba que una propuesta sin archivos se registre correctamente
    (árbol de Merkle con 3 hojas)."""
    assert len(calls) > 0
    call_id = next(iter(calls))
    title = f"Sin-archivos-{_run_id}"
    description = f"Sin archivos adjuntos {_run_id}"
    files = []
    proposal_id = compute_proposal_id(call_id, title, description, files)
    response = post_register_proposal(call_id, title, description, files)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 201
    validate(instance=response.json(), schema=register_proposal_schema)
    assert response.json()["message"] == messages.OK
    assert response.json()["proposalId"] == proposal_id
    proof = response.json()["proof"]
    expected_proofs = compute_proposal_proofs(call_id, title, description, files)
    assert proof == expected_proofs
    # Con files=[] el proof tiene exactamente 3 claves
    title_key = "0x" + bytes(Web3.keccak(text=title)).hex()
    desc_key = "0x" + bytes(Web3.keccak(text=description)).hex()
    assert set(proof.keys()) == {call_id.lower(), title_key, desc_key}
    for leaf_hex, siblings in proof.items():
        assert verify_merkle_proof(siblings, proposal_id, leaf_hex)


def test_proposal_data_direct_registration() -> None:
    """Prueba que una propuesta registrada directamente en el contrato (sin pasar por la API)
    devuelva sender/blockNumber/timestamp/estado, pero no title, description ni proof.
    """
    assert len(calls) > 0
    w3 = get_w3()
    factory, _ = get_factory_contract()
    funder = get_funder_account()
    call_id = next(iter(calls))
    call_id_bytes = bytes.fromhex(call_id[2:])
    proposal = random_hash()
    proposal_bytes = bytes.fromhex(proposal[2:])
    tx = factory.functions.registerProposal(
        call_id_bytes, proposal_bytes
    ).build_transaction(
        {
            "from": funder.address,
            "nonce": w3.eth.get_transaction_count(funder.address),
            "gas": 200000,
            "gasPrice": w3.to_wei("1", "gwei"),
        }
    )
    signed = funder.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    w3.eth.wait_for_transaction_receipt(tx_hash)
    response = get_proposal_data(call_id, proposal)
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 200
    validate(instance=response.json(), schema=proposal_data_schema)
    pd = response.json()
    assert "sender" in pd
    assert "blockNumber" in pd
    assert "timestamp" in pd
    assert "estado" in pd
    # Sin registro en la API: no debe haber title, description ni proof
    assert "title" not in pd
    assert "description" not in pd
    assert "proof" not in pd


def post_verify_proof(proposal_id, leaf, proof):
    """Llama a POST /verify-proof y retorna la respuesta."""
    return requests.post(
        url("verify-proof"),
        json={"proposalId": proposal_id, "leaf": leaf, "proof": proof},
        timeout=10,
    )


def test_verify_proof_invalid_input() -> None:
    """Prueba que /verify-proof rechace entradas con formato incorrecto."""
    valid_hash = random_hash()
    valid_proof = [random_hash()]
    # MIME type incorrecto
    response = requests.post(
        url("verify-proof"),
        data={"proposalId": valid_hash, "leaf": valid_hash, "proof": []},
        timeout=10,
    )
    assert response.status_code == 400
    assert response.json()["message"].startswith(messages.INVALID_MIMETYPE)
    # Campos faltantes
    for body in [
        {"leaf": valid_hash, "proof": valid_proof},
        {"proposalId": valid_hash, "proof": valid_proof},
        {"proposalId": valid_hash, "leaf": valid_hash},
        {},
    ]:
        response = requests.post(url("verify-proof"), json=body, timeout=10)
        assert response.status_code == 400
        assert response.json()["message"] == messages.MISSING_FIELD
    # proposalId inválido
    for bad in ["x", "0x", "0x0", random_hash()[:-2], random_hash() + "ab"]:
        response = post_verify_proof(bad, valid_hash, valid_proof)
        assert response.status_code == 400
        assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)
    # leaf inválido
    for bad in ["x", "0x", "0x0", random_hash()[:-2], random_hash() + "ab"]:
        response = post_verify_proof(valid_hash, bad, valid_proof)
        assert response.status_code == 400
        assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)
    # proof con elemento inválido o no es lista
    for bad_proof in [
        "not-a-list",
        42,
        [random_hash()[:-2]],
        [random_hash() + "ab"],
    ]:
        response = post_verify_proof(valid_hash, valid_hash, bad_proof)
        assert response.status_code == 400
        assert response.json()["message"].startswith(messages.INVALID_PROPOSAL)


def test_verify_proof_via_api() -> None:
    """Registra una propuesta con múltiples archivos y verifica cada hoja vía /verify-proof."""
    assert len(calls) > 0
    call_id = next(iter(calls))
    title = f"Verify-API-{_run_id}"
    description = f"Verificación vía API {_run_id}"
    files = [random_hash(), random_hash(), random_hash()]
    proposal_id = compute_proposal_id(call_id, title, description, files)
    reg_response = post_register_proposal(call_id, title, description, files)
    assert reg_response.status_code == 201
    assert reg_response.json()["proposalId"] == proposal_id
    proof = reg_response.json()["proof"]
    # Debe haber una entrada por cada hoja: callId + title + description + 3 files
    assert len(proof) == 6
    # Cada hoja debe verificar correctamente
    for leaf_hex, siblings in proof.items():
        response = post_verify_proof(proposal_id, leaf_hex, siblings)
        assert response.status_code == 200
        assert (
            response.json()["valid"] is True
        ), f"/verify-proof devolvió False para hoja {leaf_hex}"
    # Una hoja incorrecta debe devolver valid: false
    first_siblings = next(iter(proof.values()))
    response = post_verify_proof(proposal_id, random_hash(), first_siblings)
    assert response.status_code == 200
    assert response.json()["valid"] is False
    # Una prueba incorrecta para una hoja válida también debe devolver valid: false
    first_leaf = next(iter(proof))
    response = post_verify_proof(proposal_id, first_leaf, [random_hash()])
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_verify_proof_empty_proof() -> None:
    """Prueba que /verify-proof con proof vacío sea válido solo si proposalId == leaf."""
    h = random_hash()
    response = post_verify_proof(h, h, [])
    assert response.status_code == 200
    assert response.json()["valid"] is True
    # Con hoja diferente → inválido
    response = post_verify_proof(h, random_hash(), [])
    assert response.status_code == 200
    assert response.json()["valid"] is False


def test_verify_proposal_proofs_onchain() -> None:
    """Despliega MerkleVerifier (OpenZeppelin) y verifica on-chain las pruebas
    devueltas por la API."""
    assert len(calls) > 0
    verifier = get_verifier_contract()
    call_id = next(iter(calls))
    title = f"Merkle-OZ-{_run_id}"
    description = f"Verificación on-chain {_run_id}"
    files = [random_hash(), random_hash()]
    proposal_id = compute_proposal_id(call_id, title, description, files)
    response = post_register_proposal(call_id, title, description, files)
    assert response.status_code == 201
    assert response.json()["proposalId"] == proposal_id
    proof = response.json()["proof"]
    root = bytes.fromhex(proposal_id[2:])
    for leaf_hex, siblings in proof.items():
        leaf = bytes.fromhex(leaf_hex[2:])
        proof_bytes32 = [bytes.fromhex(s[2:]) for s in siblings]
        assert verifier.functions.verify(
            proof_bytes32, root, leaf
        ).call(), f"OZ verify falló para hoja {leaf_hex}"
    # Una prueba con hoja incorrecta debe fallar
    wrong_leaf = bytes.fromhex(random_hash()[2:])
    first_siblings = next(iter(proof.values()))
    wrong_proof_bytes32 = [bytes.fromhex(s[2:]) for s in first_siblings]
    assert not verifier.functions.verify(
        wrong_proof_bytes32, root, wrong_leaf
    ).call(), "OZ verify no debe pasar con una hoja incorrecta"


# ---------------------------------------------------------------------------
# Estado archived y re-registro
# ---------------------------------------------------------------------------

def test_api_unauthorize_not_registered() -> None:
    """Prueba que /unauthorize falle con 404 si la dirección nunca se registró en la API."""
    contract_address = get_contract_address()
    admin = get_admin_account()
    nonce = get_admin_nonce()
    account = Account().create()  # nunca llamó a POST /register
    msg = make_unauthorize_message(contract_address, nonce, account.address)
    response = post_unauthorize(account.address, sign_bytes(msg, admin))
    assert APPLICATION_JSON in response.headers["Content-type"]
    assert response.status_code == 404
    validate(instance=response.json(), schema=message_schema)
    assert response.json()["message"] == messages.NOT_REGISTERED
    # El nonce no debe haber cambiado
    assert get_admin_nonce() == nonce


def test_api_unauthorize_preserves_db() -> None:
    """Prueba que tras desautorizar los datos en DB se preservan y el estado vuelve a pending."""
    contract_address = get_contract_address()
    admin = get_admin_account()

    # Registrar y autorizar
    account = Account().create()
    fund_account(account.address)
    send_register_tx(account)
    msg = make_register_message(contract_address, "DB Preserved Creator")
    post_register(account.address, sign_bytes(msg, account), "DB Preserved Creator")
    assert wait_for_registration_status(
        account.address, "registered"
    ), "El estado no llegó a 'registered'"
    auth_nonce = get_admin_nonce()
    auth_msg = make_authorize_message(contract_address, auth_nonce, account.address)
    assert post_authorize(account.address, sign_bytes(auth_msg, admin)).status_code == 200
    assert wait_for_registration_status(
        account.address, "authorized"
    ), "El estado no llegó a 'authorized'"

    # Crear un llamado on-chain
    send_create_tx(account, random_hash(), get_closing_time())

    # Desautorizar
    nonce = get_admin_nonce()
    unauth_msg = make_unauthorize_message(contract_address, nonce, account.address)
    response = post_unauthorize(account.address, sign_bytes(unauth_msg, admin))
    assert response.status_code == 200
    assert response.json()["message"] == messages.OK
    assert get_admin_nonce() == nonce + 1

    # DB preservada, estado computado = pending
    reg = get_registration(account.address)
    assert reg.status_code == 200
    assert reg.json()["status"] == "pending"
    assert reg.json()["name"] == "DB Preserved Creator"
    assert "nonce" in reg.json()

    # Intentar desautorizar de nuevo → 404 (no está registrado on-chain)
    nonce2 = get_admin_nonce()
    unauth_msg2 = make_unauthorize_message(contract_address, nonce2, account.address)
    response2 = post_unauthorize(account.address, sign_bytes(unauth_msg2, admin))
    assert response2.status_code == 404
    assert response2.json()["message"] == messages.NOT_REGISTERED
    assert get_admin_nonce() == nonce2


def test_api_authorize_not_registered_onchain() -> None:
    """Prueba que /authorize falle con 404 si la dirección no está registrada on-chain."""
    contract_address = get_contract_address()
    admin = get_admin_account()

    # Solo en DB (POST /register), sin registro on-chain
    account = Account().create()
    fund_account(account.address)
    msg = make_register_message(contract_address, "DB only")
    response = post_register(account.address, sign_bytes(msg, account), "DB only")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"

    # Intentar autorizar una cuenta sin registro on-chain → 404
    nonce = get_admin_nonce()
    response = post_authorize(
        account.address,
        sign_bytes(make_authorize_message(contract_address, nonce, account.address), admin)
    )
    assert response.status_code == 404
    assert response.json()["message"] == messages.NOT_REGISTERED
    assert get_admin_nonce() == nonce


def test_reregister_onchain_after_unauthorize() -> None:
    """Prueba que tras desautorizar, re-registrarse on-chain restaura el estado 'registered'."""
    contract_address = get_contract_address()
    admin = get_admin_account()

    # Llevar la cuenta a pending (registrar, autorizar, crear llamado, desautorizar)
    account = Account().create()
    fund_account(account.address)
    send_register_tx(account)
    msg = make_register_message(contract_address, "Re-register Me")
    post_register(account.address, sign_bytes(msg, account), "Re-register Me")
    assert wait_for_registration_status(account.address, "registered"), \
        "El estado no llegó a 'registered'"
    auth_nonce = get_admin_nonce()
    assert post_authorize(
        account.address,
        sign_bytes(make_authorize_message(contract_address, auth_nonce, account.address), admin)
    ).status_code == 200
    assert wait_for_registration_status(account.address, "authorized"), \
        "El estado no llegó a 'authorized'"
    send_create_tx(account, random_hash(), get_closing_time())
    nonce = get_admin_nonce()
    assert post_unauthorize(
        account.address,
        sign_bytes(make_unauthorize_message(contract_address, nonce, account.address), admin)
    ).status_code == 200
    # DB preservada, estado = pending
    assert wait_for_registration_status(account.address, "pending"), \
        "El estado no llegó a 'pending' tras desautorizar"

    # Re-registrarse on-chain (sin POST /register, los datos en DB se preservan)
    send_register_tx(account)

    # Estado computado = registered (isRegistered=true + DB existe)
    assert wait_for_registration_status(account.address, "registered"), \
        "El estado no llegó a 'registered' tras re-registro on-chain"

    # Nombre y nonce originales preservados
    reg = get_registration(account.address)
    assert reg.status_code == 200
    assert reg.json()["name"] == "Re-register Me"
    assert reg.json()["nonce"] >= 1
    assert reg.json()["status"] == "registered"

    # POST /register debe rechazar (ya existe en DB)
    new_msg = make_register_message(contract_address, "Should Fail")
    response = post_register(account.address, sign_bytes(new_msg, account), "Should Fail")
    assert response.status_code == 403
    assert response.json()["message"] == messages.ALREADY_IN_SYSTEM
