# stamper_cli.py

"""
Cliente CLI para interactuar con la API REST del apiserver.py
Uso: python3 stamper_cli.py [verify|stamp] <archivo1> [<archivo2> ...]
"""

import sys
import hashlib
import requests

API_URL = "http://localhost:5000"

# lee el archivo y devuelve "0xabc..."
def calcular_hash(ruta):
    """
    Calcula el hash SHA-256 de un archivo y lo devuelve en
    formato hexadecimal con prefijo '0x'.
    """

    # Crear un objeto sha256
    sha256_hash = hashlib.sha256()

    # Abrir el archivo en modo binario y leerlo en bloques para no cargarlo todo en memoria
    try:
        with open(ruta, "rb") as f:
            # Leer el archivo en bloques para no cargarlo todo en memoria
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        # Devolver el hash en formato hexadecimal con prefijo '0x'
        return "0x" + sha256_hash.hexdigest()
    except FileNotFoundError:
        print(f"Error: El archivo '{ruta}' no existe.")
        return None
    except PermissionError:
        print(f"Error: No se tienen permisos para leer el archivo '{ruta}'.")
        return None

# GET /stamped/{hash} e imprime resultado
def verificar(ruta):
    """
    Consulta la API para verificar si el hash del archivo ya fue sellado.
    """

    hash_value = calcular_hash(ruta)
    if not hash_value:
        return

    try:
        response = requests.get(f"{API_URL}/stamped/{hash_value}", timeout=5)

        if response.status_code == 200:
            data = response.json()
            print(f"Archivo: {ruta}")
            print(f"Hash: {hash_value}")
            print(f"Firmante: {data['signer']}")
            print(f"Número de bloque: {data['blockNumber']}")
        elif response.status_code == 404:
            print(f"Archivo: {ruta}")
            print(f"Hash: {hash_value}")
            print("No sellado")
        else:
            print(f"Error al consultar la API: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión con la API: {str(e)}")

# POST /stamp con el hash e imprime resultado
def sellar(ruta):
    """
    Envia el hash del archivo a la API para sellarlo, registrándolo en la "blockchain" simulada.
    """

    hash_value = calcular_hash(ruta)
    if not hash_value:
        return

    try:
        response = requests.post(f"{API_URL}/stamp", json={"hash": hash_value}, timeout=5)

        if response.status_code == 201:
            print(f"Archivo: {ruta}")
            print(f"Hash: {hash_value}")
            print("Sellado exitoso")
        elif response.status_code == 403:
            data = response.json()
            print(f"Archivo: {ruta}")
            print(f"Hash: {hash_value}")
            print(f"Hash ya sellado por {data['signer']} en bloque {data['blockNumber']}")
        else:
            print(f"Error al sellar el hash: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión con la API: {str(e)}")

def main():
    """
    Función principal que maneja los argumentos de línea de comandos
    y llama a las funciones correspondientes.
    """

    # Validar que se haya pasado al menos un subcomando y un archivo
    if len(sys.argv) < 3:
        print("Uso: python3 stamper_cli.py [verify|stamp] <archivo1> [<archivo2> ...]")
        sys.exit(1)

    # Obtener el subcomando y los archivos de los argumentos
    command = sys.argv[1].lower()
    archivos = sys.argv[2:]

    if command not in ["verify", "stamp"]:
        print("Comando no reconocido. Use 'verify' o 'stamp'.")
        sys.exit(1)

    print(f"Ejecutando comando '{command.upper()}' para los archivos: {', '.join(archivos)}")

    for archivo in archivos:
        if command == "verify":
            verificar(archivo)
        elif command == "stamp":
            sellar(archivo)

if __name__ == "__main__":
    main()
