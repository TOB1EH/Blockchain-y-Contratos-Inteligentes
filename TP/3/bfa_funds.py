#!/usr/bin/env python3

"""
Script para manejar fondos en una red Ethereum.
Permite consultar el balance de una cuenta y realizar transferencias de ether entre cuentas.
Se conecta a un nodo geth mediante IPC. BFA significa "Blockchain For All", es una red de
pruebas local que se puede correr en la misma máquina.
"""

import argparse
import sys
import os
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# URI por defecto para conectarse al nodo geth de BFA. Se puede cambiar con --uri
DEFAULT_WEB3_URI = "̣~/blockchain-iua/bfatest/node/geth.ipc"

def balance(w3, account, unit):
    """Imprime el balance de una cuenta
        :param w3: La instancia de Web3 conectada al nodo.
        :param account: La dirección de la cuenta
        :param unit: Las unidades en las que se desea el resultado. (wei, Kwei, Mwei,
        Gwei, microether, milliether, ether)
    """
    # Obtener el balance en wei, que es la unidad mínima de ether.
    # Es un número entero que representa la cantidad de wei que tiene la cuenta.
    balance_wei = w3.eth.get_balance(account)

    # Convertir el balance a las unidades deseadas o ingresadas por el usuario
    # para mostrarlo por consola.
    balance_convertido = w3.from_wei(balance_wei, unit)
    print(f"{balance_convertido} {unit}")

def transfer(w3, src, dst, amount, unit):
    """Transfiere ether de una cuenta a otra.

    :param w3: La instancia de Web3 conectada al nodo.
    :param src: La dirección de la cuenta de origen.
    :param dst: La dirección de la cuenta de destino.
    :param amount: Monto que se desea transferir.
    :param unit: Unidades en las que está expresado el monto.
    Si la transacción es exitosa, imprime "Transferencia exitosa".
    Si la transacción falla, termina el programa con error e indica la causa.
    """

    # Convertir el monto a wei para enviarlo, porque
    # send_transaction siempre trabaja en wei internamente
    cantidad_wei = w3.to_wei(amount, unit)

    # Nota: El desbloqueo de cuenta via w3.geth.personal fue deprecado en web3.py.
    # En su lugar, desbloquea la cuenta desde geth directamente:
    # geth attach <ruta> personal.unlockAccount("<dirección>", "contraseña", 0)

    # Armar y enviar la transacción
    tx_hash = w3.eth.send_transaction({
        "from":  src,
        "to":    dst,
        "value": cantidad_wei
    })

    # Esperar a que la transacción sea incluida en un bloque
    # Esto bloquea el programa hasta tener confirmación
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

    if receipt.status == 1:
        print("Transferencia exitosa")
        # Mostrar el hash de la transacción para referencia futura
        print(f"Hash: {tx_hash.hex()}")
        # Otros datos
        print(f"Bloque: {receipt.blockNumber}")
        print(f"Gas usado: {receipt.gasUsed}")
    else:
        print("Error: la transacción falló", file=sys.stderr)
        sys.exit(1)

def accounts(w3):
    """Lista las cuentas asociadas con un nodo"""
    for account in w3.eth.accounts:
        print(account)

def address(x):
    """Verifica si su argumento tiene forma de dirección ethereum válida"""

    # Una dirección Ethereum válida tiene 42 caracteres, empieza con '0x' y
    # el resto son dígitos hexadecimales. Si el formato es correcto, devuelve
    # la dirección. Si no, lanza un error.
    if x[:2] == '0x' or x[:2] == '0X':
        try:
            b = bytes.fromhex(x[2:])
            if len(b) == 20:
                return x
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(f"Invalid address: '{x}'")

def main():
    """
    Función principal del programa. Maneja la conexión al nodo y el flujo de ejecución
    según los comandos ingresados por el usuario.
    """

    # Configurar un parser de argumentos para manejar la entrada por consola del usuario.
    # Es un analizador de argumentos de linea de comandos con multiples subcomandos.
    parser = argparse.ArgumentParser(description=
        f"""Maneja los fondos de una cuenta en una red ethereum.
        Permite consultar el balance y realizar transferencias.
        Por defecto, intenta conectarse mediante '{DEFAULT_WEB3_URI}'""")
    parser.add_argument(
        "--uri",
        help="URI para la conexión con geth",
        default=DEFAULT_WEB3_URI
    )
    subparsers = parser.add_subparsers(
        title="command",
        dest="command"
    )
    subparsers.required=True
    parser_balance = subparsers.add_parser(
        "balance",
        help="Obtiene el balance de una cuenta"
    )
    parser_balance.add_argument(
        "--unit",
        help="Unidades en las que está expresado el monto",
        choices=['wei', 'Kwei', 'Mwei', 'Gwei', 'microether', 'milliether','ether'],
        default='wei'
    )
    parser_balance.add_argument(
        "--account",
        "-a",
        help="Cuenta de la que se quiere obtener el balance",
        type=address,
        required=True
    )
    parser_transfer = subparsers.add_parser(
        "transfer",
        help="Transfiere fondos de una cuenta a otra"
    )
    parser_transfer.add_argument(
        "--from",
        help="Cuenta de origen",
        type=address,
        required=True,
        dest='src'
    )
    parser_transfer.add_argument(
        "--to",
        help="Cuenta de destino",
        type=address,
        required=True,
        dest='dst'
    )
    parser_transfer.add_argument(
        "--amount",
        help="Monto a transferir",
        type=int,
        required=True
    )
    parser_transfer.add_argument(
        "--unit",
        help="Unidades en las que está expresado el monto",
        choices=['wei', 'Kwei', 'Mwei', 'Gwei', 'microether', 'milliether','ether'],
        default='wei'
    )
    subparsers.add_parser(
        "accounts",
        help="Lista las cuentas de un nodo"
    )
    # Parsear los argumentos ingresados por el usuario en la consola. Esto convierte la entrada
    # de texto en un objeto con atributos correspondientes a cada argumento.
    args = parser.parse_args()

    # expande el ~ a la ruta completa en caso de que el usuario lo haya usado
    # en la URI o lo ingrese por consola.
    # Funciona de la siguiente manera:
    # si el argumento es "~/blockchain-iua/bfatest/node/geth.ipc", lo convierte
    # a "/home/usuario/blockchain-iua/bfatest/node/geth.ipc"
    uri = os.path.expanduser(args.uri)

    # Conectarse al nodo geth usando IPC. Si el nodo está corriendo en la misma
    # máquina, esta es la forma más rápida de conexión.
    # Si el nodo estuviera en otra máquina, habría que usar HTTPProvider o WebsocketProvider
    # y cambiar la URI a algo como "http://ip_del_nodo:8545" o "ws://ip_del_nodo:8546"
    w3 = Web3(Web3.IPCProvider(uri))

    # BFA usa Proof of Authority: los bloques tienen un extraData más largo
    # que el permitido por el estándar Ethereum. Sin este middleware web3.py
    # lanza ExtraDataLengthError.
    # Esto funciona de la siguiente manera: cuando web3.py recibe un bloque,
    # pasa su extraData por este middleware. Si el extraData es más largo de lo
    # permitido por el estándar, el middleware lo recorta a 32 bytes y lo devuelve.
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    if not w3.is_connected():
        print(f"Error: no se pudo conectar al nodo en {args.uri}", file=sys.stderr)
        sys.exit(1)

    # Ejecutar la función correspondiente al comando indicado por el usuario
    if args.command == "balance":
        balance(w3, args.account, args.unit)
    elif args.command == "transfer":
        transfer(w3, args.src, args.dst, args.amount, args.unit)
    elif args.command == "accounts":
        accounts(w3)

# El bloque principal del programa. Se ejecuta solo si el script es corrido directamente.
if __name__ == "__main__":
    main()
