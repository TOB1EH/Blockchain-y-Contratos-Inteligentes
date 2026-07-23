"""Event listener que sincroniza la base de datos con los eventos del contrato.
Ya no sincroniza estados de registro (fuente de verdad on-chain).
Escucha CFPCreated para Etapa 2 y registra nombres ENS para llamados."""

import threading
import time
import logging
from web3 import Web3

import database

logger = logging.getLogger(__name__)

ZERO = "0x0000000000000000000000000000000000000000"


def start_listener(factory, w3, send_tx=None, ens_registry_addr=None,
                   server_account_key=None) -> None:
    """
    Lanza el event listener en un hilo daemon.

    Args:
        factory: Contrato CFPFactory
        w3: Instancia Web3
        send_tx: Funcion para enviar transacciones (send_transaction de apiserver)
        ens_registry_addr: Direccion del ENSRegistry
        server_account_key: Clave privada del server_account para firmar txs
    """
    resolver_abi_cache = None

    def _load_resolver_abi():
        nonlocal resolver_abi_cache
        if resolver_abi_cache is not None:
            return resolver_abi_cache
        try:
            import json, os
            base = os.path.dirname(os.path.abspath(__file__))
            contracts_dir = os.environ.get("CFP_CONTRACTS_DIR", "../contracts")
            if contracts_dir.startswith("../"):
                resolved = os.path.normpath(os.path.join(base, contracts_dir))
            else:
                resolved = contracts_dir
            path = os.path.join(
                resolved,
                "artifacts/contracts/PublicResolver.sol/PublicResolver.json"
            )
            with open(path) as f:
                abi = json.load(f)["abi"]
            resolver_abi_cache = abi
            return abi
        except Exception as e:
            logger.error("Error cargando resolver ABI: %s", e)
            return None

    def _register_call_ens(call_id_hex, cfp_address, ens_name):
        """Registra ens_name.llamados.cfp apuntando al CFP contract."""
        if not send_tx or not ens_registry_addr:
            logger.warning("ENS no configurado, no se registra nombre para %s", call_id_hex)
            return

        try:
            ens_registry = w3.eth.contract(
                address=Web3.to_checksum_address(ens_registry_addr),
                abi=_load_resolver_abi()  # fallback, usamos ABI del registry en su lugar
            )

            import json, os
            base = os.path.dirname(os.path.abspath(__file__))
            contracts_dir = os.environ.get("CFP_CONTRACTS_DIR", "../contracts")
            if contracts_dir.startswith("../"):
                resolved = os.path.normpath(os.path.join(base, contracts_dir))
            else:
                resolved = contracts_dir
            path = os.path.join(
                resolved,
                "artifacts/contracts/ENSRegistry.sol/ENSRegistry.json"
            )
            with open(path) as f:
                registry_abi = json.load(f)["abi"]
            ens_registry = w3.eth.contract(
                address=Web3.to_checksum_address(ens_registry_addr),
                abi=registry_abi
            )

            # namehash y labelhash helpers
            from eth_utils import to_bytes, keccak as eth_keccak
            def _namehash(name):
                node = b'\x00' * 32
                if name:
                    labels = name.split(".")
                    for label in reversed(labels):
                        node = eth_keccak(node + eth_keccak(text=label))
                return node

            llamados_node = _namehash("llamados.cfp")
            ens_label = eth_keccak(text=ens_name)
            full_name = f"{ens_name}.llamados.cfp"
            full_node = _namehash(full_name)

            logger.info("Registrando ENS %s -> %s", full_name, cfp_address)

            # 1. Crear subnodo: setSubnodeOwner(llamados_node, label, cfp_address)
            # El caller debe ser owner de llamados.cfp (server_account = deployer)
            tx_fn = ens_registry.functions.setSubnodeOwner(
                llamados_node, ens_label,
                Web3.to_checksum_address(cfp_address)
            )
            send_tx(tx_fn)

            # 2. Consultar el resolver de llamados.cfp
            resolver_addr = ens_registry.functions.resolver(llamados_node).call()
            if resolver_addr == ZERO:
                logger.warning("llamados.cfp no tiene resolver configurado")
                return

            resolver_abi = _load_resolver_abi()
            if not resolver_abi:
                return
            resolver = w3.eth.contract(
                address=Web3.to_checksum_address(resolver_addr),
                abi=resolver_abi
            )

            # 3. Configurar resolver para el nuevo nombre
            tx_fn = ens_registry.functions.setResolver(
                full_node, Web3.to_checksum_address(resolver_addr)
            )
            send_tx(tx_fn)

            # 4. Configurar addr
            tx_fn = resolver.functions.setAddr(
                full_node, Web3.to_checksum_address(cfp_address)
            )
            send_tx(tx_fn)

            logger.info("ENS %s registrado exitosamente", full_name)

        except Exception as e:
            logger.error("Error registrando ENS para %s: %s", call_id_hex, e, exc_info=True)

    def _handle_cfp_created(evt) -> None:
        call_id     = "0x" + evt["args"]["callId"].hex()
        creator     = evt["args"]["creator"]
        cfp_address = evt["args"]["cfp"]
        call = database.get_call(call_id)
        if call and call["status"] == "pending":
            database.update_call_created(call_id, creator, cfp_address)
            logger.info("CFPCreated: %s -> created", call_id)
            # Si el llamado tiene nombre ENS, registrarlo en llamados.cfp
            ens_name = call.get("ens_name") if call else None
            if ens_name:
                _register_call_ens(call_id, cfp_address, ens_name)

    def _loop():
        last_block = w3.eth.block_number
        logger.info("Event listener iniciado en bloque %d", last_block)

        while True:
            try:
                time.sleep(0.5)
                current_block = w3.eth.block_number

                if current_block <= last_block:
                    continue

                from_b = last_block + 1
                to_b   = current_block

                for evt in factory.events.CFPCreated.get_logs(
                    from_block=from_b, to_block=to_b
                ):
                    _handle_cfp_created(evt)

                last_block = current_block

            except Exception as e:
                logger.error("Error en el event listener: %s", e, exc_info=True)

    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread
