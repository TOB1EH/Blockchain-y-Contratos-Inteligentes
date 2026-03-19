#!/usr/bin/env python3

import argparse
import sys

DEFAULT_WEB3_URI = "~/blockchain-iua/bfatest/node/geth.ipc"

def balance(account, unit):
    """Imprime el balance de una cuenta

    :param account: La dirección de la cuenta
    :param unit: Las unidades en las que se desea el resultado. (wei, Kwei, Mwei, Gwei, microether, milliether, ether)
    """
    print(f"balance({account},{unit}): No implementado")

def transfer(src, dst, amount, unit):
    """Transfiere ether de una cuenta a otra.

    :param src: La dirección de la cuenta de origen.
    :param dst: La dirección de la cuenta de destino.
    :param amount: Monto que se desea transferir.
    :param unit: Unidades en las que está expresado el monto.
    Si la transacción es exitosa, imprime "Transferencia exitosa".
    Si la transacción falla, termina el programa con error e indica la causa.
    """
    print(f"transfer({src},{dst},{amount},{unit}): No implementado")

def accounts():
    """Lista las cuentas asociadas con un nodo"""
    print("accounts(): No implementado")

def address(x):
    """Verifica si su argumento tiene forma de dirección ethereum válida"""
    
    if x[:2] == '0x' or x[:2] == '0X':
        try:
            b = bytes.fromhex(x[2:])
            if len(b) == 20:
                return x
        except ValueError:
            pass
    raise argparse.ArgumentTypeError(f"Invalid address: '{x}'")                                                                                                                                               



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
        f"""Maneja los fondos de una cuenta en una red ethereum.
        Permite consultar el balance y realizar transferencias. Por defecto, intenta conectarse mediante '{DEFAULT_WEB3_URI}'""")
    parser.add_argument("--uri", help="URI para la conexión con geth",default=DEFAULT_WEB3_URI)
    subparsers = parser.add_subparsers(title="command", dest="command")
    subparsers.required=True
    parser_balance = subparsers.add_parser("balance", help="Obtiene el balance de una cuenta")
    parser_balance.add_argument("--unit", help="Unidades en las que está expresado el monto", choices=['wei', 'Kwei', 'Mwei', 'Gwei', 'microether', 'milliether','ether'], default='wei')
    parser_balance.add_argument("--account", "-a", help="Cuenta de la que se quiere obtener el balance", type=address, required=True)
    parser_transfer = subparsers.add_parser("transfer", help="Transfiere fondos de una cuenta a otra")
    parser_transfer.add_argument("--from", help="Cuenta de origen", type=address, required=True, dest='src')
    parser_transfer.add_argument("--to", help="Cuenta de destino", type=address, required=True, dest='dst')
    parser_transfer.add_argument("--amount", help="Monto a transferir", type=int, required=True)
    parser_transfer.add_argument("--unit", help="Unidades en las que está expresado el monto", choices=['wei', 'Kwei', 'Mwei', 'Gwei', 'microether', 'milliether','ether'], default='wei')
    parser_accounts = subparsers.add_parser("accounts", help="Lista las cuentas de un nodo")
    args = parser.parse_args()
    # La URI elegida por el usuario está disponible como args.uri
    # Lo que sigue probablemente debería estar encerrado en un bloque try: ... except:
    if args.command == "balance":
        balance(args.account, args.unit)
    elif args.command == "transfer":
        transfer(args.src, args.dst, args.amount, args.unit)
    elif args.command == "accounts":
        accounts()
    else:
        print(f"Comando desconocido: {args.command}", file=sys.stderr)
        sys.exit(1)