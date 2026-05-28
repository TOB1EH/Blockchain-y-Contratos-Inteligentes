"""Event listener que sincroniza la base de datos con los eventos del contrato."""

import threading
import time
import logging

import database

logger = logging.getLogger(__name__)


def start_listener(factory, w3) -> None:
    """
    Lanza el event listener en un hilo daemon.
    w3 se pasa como closure, no se adjunta al factory.
    """

    def _handle_creator_registered(evt) -> None:
        """
        Maneja el evento CreatorRegistered.
        """
        address = evt["args"]["creator"].lower()
        reg = database.get_registration(address)
        if reg and reg["status"] == "pending":
            database.update_registration_status(address, "registered")
            logger.info("CreatorRegistered: %s → registered", address)

    def _handle_creator_authorized(evt) -> None:
        """
        Maneja el evento CreatorAuthorized.
        """
        address = evt["args"]["creator"].lower()
        reg = database.get_registration(address)
        if reg:
            database.update_registration_status(address, "authorized")
            logger.info("CreatorAuthorized: %s → authorized", address)

    def _handle_creator_unauthorized(evt) -> None:
        """
        Maneja el evento CreatorUnauthorized.
        """
        address = evt["args"]["creator"].lower()
        reg = database.get_registration(address)
        if not reg:
            return
        try:
            count = factory.functions.createdByCount(
                w3.to_checksum_address(address)   # w3 viene del closure
            ).call()
        except Exception as e:
            logger.error("Error en createdByCount para %s: %s", address, e)
            count = 0

        if count > 0:
            database.update_registration_status(address, "archived")
            logger.info("CreatorUnauthorized: %s → archived", address)
        else:
            database.delete_registration(address)
            logger.info("CreatorUnauthorized: %s eliminado", address)

    def _handle_cfp_created(evt) -> None:
        """
        Maneja el evento CFPCreated.
        """
        call_id     = "0x" + evt["args"]["callId"].hex()
        creator     = evt["args"]["creator"]
        cfp_address = evt["args"]["cfp"]
        call = database.get_call(call_id)
        if call and call["status"] == "pending":
            database.update_call_created(call_id, creator, cfp_address)
            logger.info("CFPCreated: %s → created", call_id)

    def _loop():
        """
        Loop principal del event listener.
        """
        last_block = w3.eth.block_number
        logger.info("Event listener iniciado en bloque %d", last_block)

        while True:
            try:
                time.sleep(0.5) # Espera medio segundo entre iteraciones para no sobrecargar el nodo
                current_block = w3.eth.block_number

                # Si no hay nuevos bloques, continúa al siguiente ciclo
                if current_block <= last_block:
                    continue

                # Consulta los eventos desde el último bloque procesado hasta el bloque actual
                from_b = last_block + 1
                to_b   = current_block

                for evt in factory.events.CreatorRegistered.get_logs(
                    from_block=from_b, to_block=to_b
                ):
                    _handle_creator_registered(evt)

                for evt in factory.events.CreatorAuthorized.get_logs(
                    from_block=from_b, to_block=to_b
                ):
                    _handle_creator_authorized(evt)

                for evt in factory.events.CreatorUnauthorized.get_logs(
                    from_block=from_b, to_block=to_b
                ):
                    _handle_creator_unauthorized(evt)

                for evt in factory.events.CFPCreated.get_logs(
                    from_block=from_b, to_block=to_b
                ):
                    _handle_cfp_created(evt)

                last_block = current_block

            except Exception as e:
                logger.error("Error en el event listener: %s", e, exc_info=True)

    # Lanza el loop en un hilo daemon para que se ejecute en segundo plano
    thread = threading.Thread(target=_loop, daemon=True)
    thread.start()
    return thread
