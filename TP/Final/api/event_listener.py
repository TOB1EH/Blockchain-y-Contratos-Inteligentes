"""Event listener que sincroniza la base de datos con los eventos del contrato.
Ya no sincroniza estados de registro (fuente de verdad on-chain).
Solo escucha CFPCreated para Etapa 2."""

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
