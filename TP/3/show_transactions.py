#!/usr/bin/env python3
"""Este programa muestra las transacciones ocurridas en un determinado rango de bloques,
eventualmente restringidas a las que corresponden a una o más direcciones.
Sólo deben considerarse las transacciones que implican transferencia de ether.
Los bloques analizados son todos aquellos comprendidos entre los argumentos first-block
y last-block, ambos incluidos.
Si se omite first-block, se comienza en el bloque 0.
Si se omite last-block, se continúa hasta el último bloque.
Se pueden especificar una o más direcciones para restringir la búsqueda a las transacciones
en las que dichas direcciones son origen o destino.
Si se especifica la opción add, cada vez que se encuentra una transacción que responde a
los criterios de búsqueda, se agregan las cuentas intervinientes a la lista de direcciones
a reportar.
La opción "--short" trunca las direcciones a los 8 primeros caracteres.
La salida debe producirse en al menos los dos formatos siguientes:
'plain': <origen> -> <destino>: <monto> (bloque)
'graphviz': Debe producir un grafo representable por graphviz. Ejemplo (con opcion --short)
digraph Transfers {
"8ffD013B" -> "9F4BA634" [label="1 Gwei (1194114)"]
"8ffD013B" -> "9F4BA634" [label="1 ether (1194207)"]
"9F4BA634" -> "8ffD013B" [label="1 wei (1194216)"]
"8ffD013B" -> "46e2a9e9" [label="2000 ether (1195554)"]
"8ffD013B" -> "8042435B" [label="1000 ether (1195572)"]
"8042435B" -> "8ffD013B" [label="1 ether (1195584)"]
"8ffD013B" -> "55C37a7E" [label="1000 ether (1195623)"]
"8ffD013B" -> "fD52f36a" [label="1000 ether (1195644)"]
}
"""

import os
import sys
import argparse
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

def formatear_dir(direccion, short):
    """Formatea una dirección según la opción --short.
        :param direccion: La dirección a formatear.
        :param short: Si es True, trunca la dirección a los 8 primeros caracteres (sin '0x').
        :return: La dirección formateada.
    """
    if short:
        return direccion[2:10]  # saca '0x' y toma 8 caracteres
    return direccion

def formatear_monto(valor_wei):
    """Convierte wei a la unidad más legible que dé un número entero exacto.
        :param valor_wei: El monto en wei a formatear.
        :return: Una cadena con el monto formateado y su unidad (ether, Gwei, Kwei o wei).
    """
    if valor_wei == 0:
        return "0 wei"

    # Lista de unidades ordenada de mayor a menor, ya que si si se lo ordena de menor a mayor,
    # el resultado siempre va a ser en wei (porque es múltiplo de sí mismo). En cambio,
    # ordenando de mayor a menor, se obtiene la unidad más grande posible que dé un número entero.
    unidades = [
        (10**18, "ether"),
        (10**9,  "Gwei"),
        (10**3,  "Kwei"),
        (1,      "wei"),
    ]

    # Iterar sobre las unidades y devolver la primera que sea un divisor exacto del valor en wei.
    for factor, nombre in unidades:
        # Si el valor en wei es exactamente divisible por el factor, se puede expresar en esa
        # unidad sin decimales.
        if valor_wei % factor == 0:
            # Dividir el valor en wei por el factor para obtener la cantidad en la unidad
            # correspondiente, y devolverla formateada.
            return f"{valor_wei // factor} {nombre}"

def es_relevante(tx, direcciones):
    """
    Devuelve True si la transacción involucra alguna de las direcciones buscadas.
    Si el conjunto está vacío, todas las transacciones son relevantes.
    :param tx: La transacción a evaluar, con campos 'from', 'to' y 'value'.
    :param direcciones: Un conjunto de direcciones (en minúsculas) a buscar.
    :return: True si la transacción es relevante, False si no lo es.
    """
    if not direcciones:
        return True  # sin filtro, todas pasan

    # Normalizar las direcciones de origen y destino a minúsculas para comparación
    origen  = tx['from'].lower()
    destino = tx['to'].lower()

    # La transacción es relevante si el origen o el destino coincide con
    # alguna de las direcciones buscadas. Se usa una expresión generadora
    # con any() para verificar si alguna dirección en el conjunto coincide.
    # any() devuelve True si al menos una de las comparaciones es True,
    # es decir, si el origen o el destino coincide con alguna de las
    # direcciones buscadas. Si ninguna coincide, devuelve False.
    return any(d.lower() in (origen, destino) for d in direcciones)

def imprimir_plain(transacciones, short):
    """Imprime las transacciones en formato plain"""
    for tx in transacciones:
        origen  = formatear_dir(tx['from'],  short)
        destino = formatear_dir(tx['to'],    short)
        monto   = formatear_monto(tx['value'])
        bloque  = tx['blockNumber']
        print(f"{origen} -> {destino}: {monto} ({bloque})")

def imprimir_graphviz(transacciones, short):
    """Imprime las transacciones en formato graphviz"""
    print("digraph Transfers {")
    for tx in transacciones:
        origen  = formatear_dir(tx['from'],  short)
        destino = formatear_dir(tx['to'],    short)
        monto   = formatear_monto(tx['value'])
        bloque  = tx['blockNumber']
        print(f'"{origen}" -> "{destino}" [label="{monto} ({bloque})"]')
    print("}")

def address(x):
    """Verifica si su argumento tiene forma de dirección ethereum válida"""

    # Una dirección Ethereum válida tiene 42 caracteres, empieza con '0x' y
    # el resto son dígitos hexadecimales. Si el formato es correcto, devuelve
    # la dirección. Si no, lanza un error.
    if x[:2] == "0x" or x[:2] == "0X":
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

    DEFAULT_WEB3_URI = "̣̣~/blockchain-iua/bfatest/node/geth.ipc"

    # Configurar un parser de argumentos para manejar la entrada por consola del usuario.
    parser = argparse.ArgumentParser()

    # Descripción del programa que se muestra al usar --help.
    parser.description = f"""Maneja los fondos de una cuenta en una red ethereum.
                            Permite consultar el balance y realizar transferencias.
                            Por defecto, intenta conectarse mediante '{DEFAULT_WEB3_URI}'
                            """
    parser.add_argument(
        "addresses",
        metavar="ADDRESS",
        type=address,
        nargs="*",
        help="Direcciones a buscar",
    )
    parser.add_argument(
        "--add",
        help="Agrega las direcciones encontradas a la búsqueda",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--first-block",
        "-f",
        help="Primer bloque del rango en el cual buscar",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--last-block",
        "-l",
        help="Último bloque del rango en el cual buscar",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--format",
        help="Formato de salida",
        choices=["plain", "graphviz"],
        default="plain",
    )
    parser.add_argument(
        "--short",
        help="Trunca las direcciones a los 8 primeros caracteres",
        action="store_true",
    )
    parser.add_argument(
        "--uri", help="URI para la conexión con geth", default=DEFAULT_WEB3_URI
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
        print(f"Error: no se pudo conectar al nodo en {args.uri}",
              file=sys.stderr)
        sys.exit(1)

    # Resolver el último bloque si no se especificó. Si se especificó, usar el valor dado
    # por el usuario. Si se omite last-block, se continúa hasta el último bloque. Esto se
    # hace de esta manera para evitar que el programa intente analizar bloques futuros si
    # el usuario se equivocó al ingresar un número de bloque demasiado alto.
    # w3.eth.block_number devuelve el número del último bloque actual en la cadena.
    ultimo_bloque = w3.eth.block_number if args.last_block is None \
                    else args.last_block
    primer_bloque = args.first_block

    # Convertir la lista de direcciones a un set normalizado en minúsculas
    # Usamos set para búsqueda rápida y para que --add no duplique entradas
    # Set es una colección sin orden de elementos únicos (irrepetibles).
    direcciones = set(d.lower() for d in args.addresses)

    # Lista para almacenar las transacciones que cumplen los criterios de búsqueda.
    transacciones_encontradas = []

    # Iterar bloques y recolectar transacciones relevantes
    for numero in range(primer_bloque, ultimo_bloque + 1):
        # mostrar progreso cada 100 bloques para que el usuario sepa que funciona
        if (numero - primer_bloque) % 100 == 0:
            print(
                f"Procesando bloque {numero}/{ultimo_bloque}...",
                file=sys.stderr, end='\r'
            )

        # Devuelve un diccionario con la información del bloque, incluyendo una
        # lista de transacciones completas (con campos 'from', 'to', 'value', etc)
        # en cada transacción. Esto es más lento que obtener solo los hashes de las
        # transacciones, pero ahorra tener que hacer una consulta adicional por cada
        # transacción para obtener su información.
        bloque = w3.eth.get_block(numero, full_transactions=True)

        # Iterar sobre las transacciones del bloque y verificar si cumplen los criterios
        # de búsqueda
        for tx in bloque.transactions:
            # Si el campo 'to' es None, es una transacción de creación de contrato,no una
            # transferencia de ether, así que se ignora.
            if tx['to'] is None:
                continue
            # Si el campo 'value' es 0, no hay transferencia de ether, así que se ignora.
            if tx['value'] == 0:
                continue
            # Si la transacción involucra alguna de las direcciones buscadas (o si no se
            # especificaron direcciones), se considera relevante y se agrega a la lista de
            # transacciones encontradas. Si se especificó la opción --add, también se agregan
            # las direcciones de origen y destino de esta transacción al conjunto de direcciones
            # buscadas, para que las próximas transacciones que involucren estas nuevas direcciones
            # también sean consideradas relevantes.
            if es_relevante(tx, direcciones):
                if args.add:
                    direcciones.add(tx['from'].lower())
                    direcciones.add(tx['to'].lower())
                transacciones_encontradas.append(tx)

    # Después de imprimir, agregar:
    if not transacciones_encontradas:
        print("No se encontraron transacciones.", file=sys.stderr)

    # Imprimir según el formato elegido
    if args.format == "plain":
        imprimir_plain(transacciones_encontradas, args.short)
    else:
        imprimir_graphviz(transacciones_encontradas, args.short)

# El bloque principal del programa. Se ejecuta solo si el script es corrido directamente.
if __name__ == "__main__":
    main()
