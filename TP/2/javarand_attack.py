"""
Programa para adivinar el siguiente número de 32 bits a ser producido por un
generador de números pseudoaleatorios compatibles con el utilizado en Java.
"""

import requests

# Constantes del LCG de Java
MULT = 0x5DEECE66D # 25214903917 en hexadecimal
INC = 0xB # 11 en hexadecimal
MASK_48 = (1 << 48) - 1 # Esto es el equivalente a módulo 2^48

def lcg_next(seed: int) -> int:
    """
    Aplica la fórmula del LCG para generar el siguiente número pseudoaleatorio.
    Retorna la nueva semilla de 48 bits.
    """
    return (seed * MULT + INC) & MASK_48

def seed_to_int(seed: int) -> int:
    """
    Convierte la semilla interna de 48 bits a un número entero de 32 bits
    que es lo que Java devuelve como número pseudoaleatorio.
    """

    # Desplaza 16 bits a la derecha para obtener los 32 bits más significativos
    valor = seed >> 16

    # Se fuerza a Python a tratar esto como un entero con signo de 32 bits
    # Si el número es mayor o igual a 2^31, significa que en Java sería negativo
    if valor & (1 << 31):
        valor -= (1 << 32) # Convertir a negativo

    return valor

def encontrar_seed_objetivo(v1: int, v2: int) -> int:
    """
    Dado dos números pseudoaleatorios consecutivos (v1 y v2), encuentra la semilla interna
    de 48 bits que los generó.
    """
    # Se convierte v1 y v2 a su representación sin signo de 32 bits
    v1_unsigned = v1 & 0xFFFFFFFF
    v2_unsigned = v2 & 0xFFFFFFFF

    # Se prueban los 65536 valores posibles para los 16 bits ocultos
    # for i in range(65536):
    for i in range(1 << 16):
        # Arma la semilla candidata: 32 bits de v1 y 16 bits que se estan probando (i)
        seed_candidata = (v1_unsigned << 16) | i

        # Se avanza un paso en el LCG para ver si se obtiene v2
        seed_siguiente = lcg_next(seed_candidata)

        # Se extrae los 32 bits más significativos del siguiente_seed para compararlos con v2
        # Si son iguales, se encontró la semilla correcta
        if (seed_siguiente >> 16) == v2_unsigned:
            # Se encontro la semilla que produce v1 y luego v2
            # Se retorna la semilla interna de 48 bits que se uso para calcular v1
            return seed_siguiente
    # Si se recorrieron todas las posibilidades y no se encontró la semilla, se retorna None
    return None

if __name__ == "__main__":
    SERVER = "https://cripto.iua.edu.ar/blockchain"
    EMAIL = "tfunes744@alumnos.iua.edu.ar"

    # Pedir dos números pseudoaleatorios consecutivos al servidor
    print("Pidiendo n1 al servidor...")
    r1 = requests.get(f"{SERVER}/javarand/{EMAIL}/challenge", timeout=5)
    n1 = int(r1.text.strip())
    print(f"  n1 = {n1}")

    print("Pidiendo n2 al servidor...")
    r2 = requests.get(f"{SERVER}/javarand/{EMAIL}/challenge", timeout=5)
    n2 = int(r2.text.strip())
    print(f"  n2 = {n2}")

    # Buscar el estado interno
    print("\nBuscando seed por fuerza bruta...")
    seed_encontrada = encontrar_seed_objetivo(n1, n2)

    # Manejar el resultado de la busqueda
    if seed_encontrada is None:
        print("No se encontró una semilla que genere los números dados.")
    else:
        print("¡Semilla encontrada!")

        # Predecir el proximo número pseudoaleatorio usando la semilla encontrada
        siguiente_seed = lcg_next(seed_encontrada)
        prediccion = seed_to_int(siguiente_seed)
        print(f"Predicción del próximo número pseudoaleatorio: {prediccion}")

        # Enviar la predicción al servidor (respuesta)
        print("\nEnviando predicción al servidor...")
        response = requests.post(
            f"{SERVER}/javarand/{EMAIL}/answer",
            files={"number": str(prediccion).encode('ascii')},
            timeout=5
        )
        print(f"Respuesta del servidor: {response.text.strip()}")
