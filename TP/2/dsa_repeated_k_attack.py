"""
Ataque a DSA por reutilización de k.
Si el servidor firma dos mensajes distintos con el mismo k,
el valor r se repite y es posible recuperar la clave privada x.
"""

import hashlib
import base64
import requests

def hash_mensaje(mensaje: str) -> int:
    """
    Calcula el SHA-256 del mensaje y lo convierte a un número entero.
    Eso es lo que DSA usa internamente como H(m).
    """
    # encode() convierte el string a bytes, luego se calcula el hash SHA-256 y se
    # obtiene el digest en bytes.
    digest = hashlib.sha256(mensaje.encode()).digest()

    # digest es una secuencia de bytes. from_bytes lo convierte a entero.
    # 'big' indica que el byte más significativo va primero (convencion estándar)
    return int.from_bytes(digest, byteorder='big')

def obtener_clave_publica(server: str, email: str) -> dict:
    """
    Obtiene los parametros publicos DSA del servidor.
    Devuelve un diccionario con las claves 'p', 'q', 'g' y 'y' como enteros.
    """

    url = f"{server}/dsa/{email}/public-key"
    response = requests.get(url, timeout=15)
    datos = response.json()

    # El servidor devuelve las claves en mayúsculas.
    # Se las convierte a enteros porque vienen como strings en el JSON.
    return {
        'p': int(datos['P']),
        'q': int(datos['Q']),
        'g': int(datos['G']),
        'y': int(datos['Y'])
    }

def firmar_mensaje(server:str, email: str, mensaje: str) -> dict:
    """
    Envia un mneasje al servidor para que lo firme con DSA.
    Devuelve un diccionario con r y s como enteros.
    """

    # El servidor espera el mensaje en base64
    mensaje_b64 = base64.b64encode(mensaje.encode()).decode()

    url = f"{server}/dsa/{email}/sign"
    respuesta = requests.post(
        url= url,
        files={'message': mensaje_b64},
        timeout=15
    )

    datos = respuesta.json()

    # r y s vienen como strings en el JSON, se convierten a enteros.
    return {
        'r': int(datos['r']),
        's': int(datos['s']),
        'mensaje': mensaje # se guarda el mensaje original para calcular H(m) luego
    }

def buscar_r_repetido(firmas: list) -> tuple:
    """
    Busca dos firmas en la lista que compartan el mismo valor de r.
    Si las encuentra, devuelve el par. Si no, devuelve None.
    """

    # Se comparan todos los pares posibles
    for i in range(len(firmas)):
        for j in range(i + 1, len(firmas)):
            if firmas[i]['r'] == firmas[j]['r']:
                print(f"\tr repetido encontrado entre firma {i} y firma {j}")
                return firmas[i], firmas[j]
    return None

def recuperar_clave_privada(firma1: dict, firma2: dict, q: int) -> int:
    """
    Dadas dos firmas con el mismo r, recupera la clava  privada x.
    """
    r = firma1['r']
    s1 = firma1['s']
    s2 = firma2['s']

    # Se calcula el hash H(m) para cada mensaje
    h1 = hash_mensaje(firma1['mensaje'])
    h2 = hash_mensaje(firma2['mensaje'])

    # Se calcula k usando la diferencia de s y h
    # k = (H(m1) - H(m2)) * (s1 - s2)^-1 mod q
    k = ((h1 - h2) * pow(s1 - s2, -1, q)) % q

    print(f"\tk recuperado: {k}")

    # Finalmente se recupera x usando k
    # x = r^-1 * (k*s1 - H(m1)) mod q
    x = (pow(r, -1, q) * (k * s1 - h1)) % q

    return x

if __name__ == "__main__":
    SERVER = "https://cripto.iua.edu.ar/blockchain"
    EMAIL = "tfunes744@alumnos.iua.edu.ar"

    # Obtener parámetros públicos
    print("Obteniendo clave pública del servidor...")
    clave_publica = obtener_clave_publica(SERVER, EMAIL)
    q = clave_publica['q']
    print(f"  q = {q}")

    # Pedir firmas con mensajes distintos (contador simple)
    # Se piden 10 para tener 45 pares posibles y maximizar chances de encontrar r repetido
    print("\nPidiendo firmas al servidor...")

    # Generar mensajes distintos con un contador simple
    mensajes = [f"mensaje_{i}" for i in range(10)]

    firmas = []
    for i, msg in enumerate(mensajes):
        firma = firmar_mensaje(SERVER, EMAIL, msg)
        firmas.append(firma)
        print(f"  Firma {i+1}: r = {firma['r']}")

    # Buscar un par de firmas con r repetido
    print("\nBuscando r repetido entre las firmas...")
    par = buscar_r_repetido(firmas)

    if par is None:
        print("No se encontró r repetido en este lote.")
        print("El servidor no reutilizó k esta vez. Volvé a correr el programa.")
    else:
        # Recuperar la clave privada
        print("\nRecuperando clave privada...")
        x = recuperar_clave_privada(par[0], par[1], q)
        print(f"\nClave privada encontrada: x = {x}")

        # Enviar la respuesta al servidor
        print("\nEnviando respuesta al servidor...")
        respuesta = requests.post(
            url=f"{SERVER}/dsa/{EMAIL}/answer",
            files={'private-key': str(x)},
            timeout=15
        )
        print(f"Respuesta del servidor: {respuesta.text.strip()}")
