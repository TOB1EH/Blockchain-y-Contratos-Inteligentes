"""
Con este archivo se espera que sea capaz de construir dinamicamente el proximo
bloque valido de la red blockchain ficticia propuesta en el desafio.
"""

import base64
import hashlib
import time
import requests

def obtener_ultimo_bloque(email: str) -> bytes:
    """
    Se conecta al servidor y obtiene el ultimo bloque de la cadena.
    Decodifica el bloque de base64 a bytes y lo retorna.
    """

    # Se obtiene el ultimo bloque gracias al 'latest'
    url = f"https://cripto.iua.edu.ar/blockchain/pow/{email}/blocks/latest"

    print(f"Obteniendo ultimo bloque de: {url}...\n")

    try:
        # Se realiza una solicitud GET a la URL especificada para obtener el
        # último bloque de la cadena.
        respuesta = requests.get(url, timeout=10)

        if respuesta.status_code == 200:
            print("Ultimo bloque obtenido exitosamente!")
            contenido = respuesta.content

            # Se decodifica el bloque de base64 a bytes y se retorna
            return base64.b64decode(contenido)
        else:
            print("El servidor no acepto la solucion.")
            print("Verifique el bloque minado y vuelva a intentarlo.")
            print(f"Codigo de estado: {respuesta.status_code}")

    except requests.exceptions.RequestException as e:
        print(f"Ocurrió un error al obtener el último bloque del servidor: {e}")

def preparar_nuevo_bloque(bloque_anterior: bytes, email: str) -> bytearray:
    """
    Desarma el bloque anterior para construir el esqueleto del nuevo bloque.
    Retorna un bytearray que es mutable, de 96 bytes.
    """

    # 1. Numero de bloque: se lee los primeros 8 bytes (64 bits)
    # Se lo convierte a entero y se le suma 1 para obtener el numero del nuevo
    # bloque que se va a crear. Siguiendo el formato big-endian (el byte mas
    # significativo primero).
    num_bloque_anterior = int.from_bytes(bloque_anterior[0:8], byteorder='big')

    # Se incrementa el numero del bloque para el nuevo bloque
    num_bloque_nuevo = num_bloque_anterior + 1

    # 2. Timestamp: se obtiene la hora actual en segundos
    # Seria mas conveniente obtener la hora actual dentro del bucle infinito cada cierto tiempo
    # para que no se quede con un timestamp muy viejo, pero por simplicidad se lo obtiene una
    # sola vez al preparar el bloque, lo cual es menos costoso computacionalmente hablando.
    nuevo_timestamp = int(time.time())

    # 3. Target: se copia exactamente los 8 bytes del objetivo del bloque anterior
    nuevo_target = bloque_anterior[16:24]

    # 4. Hash del bloque anterior: aplica SHA-256 a todo el bloque descargado
    # Nota: se usa .digest() en lugar de .hexdigest() para que devuelva bytes crudos
    hash_bloque_anterior = hashlib.sha256(bloque_anterior).digest()

    # 5. Hash del email: se aplica SHA-256 al email (en bytes) para obtener un hash de 32 bytes
    hash_email = hashlib.sha256(email.encode()).digest()

    # ---------------------------------------------------------------------
    # Crear el Nuevo Bloque:
    nuevo_bloque = bytearray(96) # Se crea un arreglo de 96 bytes llenos de ceros

    # Arma el bloque
    nuevo_bloque[0:8] = num_bloque_nuevo.to_bytes(8, byteorder='big')
    nuevo_bloque[8:16] = nuevo_timestamp.to_bytes(8, byteorder='big')
    nuevo_bloque[16:24] = nuevo_target

    # Por el momento a los bytes del Nonce se lo deja en 0.

    nuevo_bloque[32:64] = hash_bloque_anterior
    nuevo_bloque[64:96] = hash_email

    return nuevo_bloque

def minar_bloque(bloque: bytearray) -> bytearray:
    """
    Realiza la Prueba de Trabajo (Proof of Work) iterando sobre el nonce
    hasta que el hash del bloque sea menor al target establecido.
    """

    # Se extrae el target del nuevo bloque creado y se lo convierte a entero
    msb_64_target = int.from_bytes(bloque[16:24], "big")

    # Se obtiene el objetivo (target) desplazando el valor obtenido 192 bits a la izquierda
    target = msb_64_target << 192

    print("\nIniciando minería...")
    print(f"Target (hex): {target:064x}")

    nonce = 0 # Se inicia el nonce en 0 y se va a ir incrementando hasta encontrar un bloque valido

    while True:
        # Se convierte el nonce actual a 8 bytes y lo inyectamos en el bloque
        bloque[24:32] = nonce.to_bytes(8, "big")

        # Se calcula el hash SHA-26 de todo el bloque candidato
        hash_resultado = hashlib.sha256(bloque).digest()

        # Se convierte el hash a un entero para compararlo con el target
        hash_int = int.from_bytes(hash_resultado, "big")

        # Condicion de corte: el hash tiene que ser menor al target para que el bloque sea valido
        if hash_int < target:
            print("\nBloque valido encontrado!")
            print(f"\nNonce encontrado: {nonce}")
            print(f"Hash del bloque candidato (hex): {hash_resultado.hex()}")
            break

        nonce += 1 # Incrementamos el nonce para probar el siguiente valor

        # # Se imprime un aviso cada 500,000 nonces para ver si no se quedo trabado el prgrama
        # if nonce % 500000 == 0:
        #     print(f"Probados {nonce} nonces...")

    return bloque

def enviar_bloque(email: str, bloque_minado: bytearray):
    """
    Codifica el bloque minado en base64 y lo envia al servidor para su validacion.
    """

    url = f"https://cripto.iua.edu.ar/blockchain/pow/{email}/blocks"

    # El servidor espera el bloque codificado en base64
    bloque_minado_base64 = base64.b64encode(bloque_minado)

    print(f"\nEnviando bloque minado a: {url}...\n")

    try:
        respuesta = requests.post(url, files = {"block": bloque_minado_base64}, timeout=10)

        if respuesta.status_code == 200:
            print("Bloque enviado exitosamente!")
            print(f"Respuesta del servidor: {respuesta.text}")
        else:
            print("El servidor no acepto el bloque.")
            print("Verifique el bloque minado y vuelva a intentarlo.")
            print(f"Codigo de estado: {respuesta.status_code}")
            print(f"Respuesta del servidor: {respuesta.text}")

    except requests.exceptions.RequestException as e:
        print(f"Ocurrió un error de red al intentar conectarse: {e}")


if __name__ == "__main__":

    MI_EMAIL = "tfunes744@alumnos.iua.edu.ar"

    ultimo_bloque = obtener_ultimo_bloque(MI_EMAIL)

    print(f"\nLongitud del bloque: {len(ultimo_bloque)} bytes (se esperan 96).")
    print(f"\nContenido del bloque (en bytes): {ultimo_bloque}")
    print(f"\nBloque raw (hex): {ultimo_bloque.hex()[:32]}...")

    # Preparar el nuevo bloque usando el bloque anterior y el email.
    # Se obtiene un bloque candidato con el nonce en 0.
    bloque_candidato = preparar_nuevo_bloque(ultimo_bloque, MI_EMAIL)
    print(f"\nCandidato armado (hex): {bloque_candidato.hex()}")

    # Minar el bloque candidato iterando sobre el nonce hasta encontrar un bloque valido
    bloque_minado_final = minar_bloque(bloque_candidato)

    # Enviar al servidor
    enviar_bloque(MI_EMAIL, bloque_minado_final)
