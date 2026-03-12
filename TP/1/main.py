"""
Con este archivo se espera poder encontrar una colision de hash de 48 bits para
un email dado, y enviar la solucion al servidor correspondiente del desafio criptografico propuesto.
"""

import hashlib
import requests

def calcular_hash_48(mensaje: bytes) -> str:
    """
    Calcula el SHA-256 de un mensaje y retorna los primeros 12 caracteres hexadecimales (48 bits).
    """

    # Se calcula el hash SHA-256 del mensaje usando la función 'sha256'.
    # Luego se obtiene el hash en formato hexadecimal con 'hexdigest()'
    # y se recortan los primeros 12 caracteres.
    return hashlib.sha256(mensaje).hexdigest()[:12]

def encontrar_colision(email_base: bytes):
    """
    Busca dos mensajes distintos que comiencen con el email base y
    produzcan el mismo hash recortado de 48 bits.
    """

    # Se crea un diccionario vacio para almacenar los hashes ya vistos
    # y sus mensajes correspondientes
    hashes_vistos = {}

    # Se inicia un contador para generar las variaciones del email
    contador = 0

    print(f"Iniciando búsqueda de colision para el email: {email_base.decode()}...")
    # 'decode()' se usa para convertir bytes a string para una mejor visualización

    while True:
        # Se crea el sufijo variando el contador y se lo convierte a bytes
        sufijo = str(contador).encode()

        # Se construye el mensaje actual concatenando el email base con el sufijo
        mensaje_actual = email_base + sufijo

        # Se calcula el hash del mensaje actual usando la función definida anteriormente
        hash_actual = calcular_hash_48(mensaje_actual)

        # Se comprueba si el hash ya existe en el diccionario de hashes vistos
        if hash_actual in hashes_vistos:

            # Si el hash ya existe, se obtiene el mensaje anterior que produjo
            # el mismo hash. Se encontro una colision.
            mensaje_anterior = hashes_vistos[hash_actual]

            # Retorna ambos mensajes que producen la misma salida hash
            return mensaje_anterior, mensaje_actual

        else:
            # Si el hash no existe, se almacena el hash y su mensaje
            # correspondienteen el diccionario de hashes vistos
            # La CLAVE es el hash, el VALOR es el mensaje.
            hashes_vistos[hash_actual] = mensaje_actual

        contador += 1

def enviar_solicitud(email: str, msg1: bytes, msg2: bytes):
    """
    Envia los dos mensajes que colisionan al servidor correspondiente de desafios criptograficos.
    """

    url = f"https://cripto.iua.edu.ar/blockchain/collision/{email}/answer"

    print(f"Enviando solucion a: {url}...\n")

    # En los requerimientos se especifica que el contenido debe usar el
    # formato 'files' para el envio del formulario
    datos = {
        "message1": msg1,
        "message2": msg2
    }

    try:
        # Se realiza la solicitud POST al servidor con los datos del
        # formulario y se captura la respuesta del servidor
        respuesta = requests.post(url, files=datos, timeout=10)

        print(f"Codigo de estado: {respuesta.status_code}")
        print(f"Respuesta del servidor: {respuesta.text}")

        if respuesta.status_code == 200:
            print("¡Desafio completado exitosamente!")
        else:
            print("El servidor no acepto la solucion.")
            print("Verifique los mensajes y vuelva a intentarlo.")

    except requests.exceptions.RequestException as e:
        print(f"Ocurrió un error de red al intentar conectarse: {e}")

if __name__ == "__main__":

    # # Testing:se usa el ejemplo propuesto para verificar que la funcion funciona correctamente
    # mensaje_prueba = b'user@example.com'
    # resultado = calcular_hash_48(mensaje_prueba)

    # print(f"Hash calculado: {resultado}")
    # print(f"Hash esperado: b4c9a289323b")

    # Se define el email base como bytes gracias a la 'b' antes de las comillas
    MI_EMAIL = b"tfunes744@alumnos.iua.edu.ar"

    mensaje1, mensaje2 = encontrar_colision(MI_EMAIL)

    print("\nColision encontrada!\n")
    print(f"Mensaje 1: {mensaje1} - Hash: {calcular_hash_48(mensaje1)}\n")
    print(f"Mensaje 2: {mensaje2} - Hash: {calcular_hash_48(mensaje2)}\n")

    # Enviar automaticamente la solucion al servidor.
    enviar_solicitud(MI_EMAIL.decode(), mensaje1, mensaje2)
    # Se decodifica el email a string para el envio en la URL
