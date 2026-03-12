# Trabajo Práctico 1

Este directorio contiene la resolución de los desafíos criptográficos propuestos para la materia Blockchain y Contratos Inteligentes. Los desafíos resueltos son:

  * [Búsqueda de una colisión en una función de hash](https://cripto.iua.edu.ar/blockchain/doc/collision.html)
  * [Prueba de trabajo en una red blockchain ficticia](https://cripto.iua.edu.ar/blockchain/doc/blockchain.html)


___

## Desafío 1: Colisiones en una función de hash (SHA-256-48)

### Descripción de la tarea
El objetivo de este desafío fue encontrar una colisión en una función de hash truncada a 48 bits (los primeros 12 caracteres hexadecimales de SHA-256). 

Para lograrlo de manera eficiente, se implementó un script en Python que aplica el concepto matemático del **Ataque del Cumpleaños** (Birthday Attack). En lugar de buscar un hash específico (lo cual requeriría $2^{48}$ intentos), se generaron variaciones de un mensaje base (el email del alumno) buscando cualquier par de mensajes que resulten en el mismo hash. Esto redujo el esfuerzo computacional a aproximadamente $2^{24}$ intentos, permitiendo encontrar la colisión en pocos segundos.

El script automatiza todo el proceso:
1. Genera variaciones del mensaje concatenando el email con un contador.
2. Calcula el SHA-256 truncado a 48 bits.
3. Almacena los hashes en un diccionario nativo para optimizar drásticamente el tiempo de búsqueda.
4. Una vez encontrada la colisión, envía automáticamente los mensajes resultantes al servidor de la cátedra mediante una petición HTTP POST.

### Requisitos y Configuración del Entorno

El proyecto está desarrollado en Python 3 y requiere la creación de un entorno virtual para aislar las dependencias externas.

**1. Crear el entorno virtual:**
```bash
python3 -m venv venv
```

**2. Activar el entorno virtual:**

```bash
source venv/bin/activate
```

**3. Instalar las dependencias:**

```bash
pip install -r requirements.txt
```

**Ejecución**

Con el entorno virtual activado, ejecuta el script principal:

```bash
python3 main.py
```

El script imprimirá en consola el progreso de la búsqueda, los mensajes que colisionan, sus respectivos hashes, y la respuesta final del servidor de la materia.

___

## Desafío 2: Prueba de Trabajo en una red blockchain (Proof of Work)

### Descripción de la tarea
El objetivo de este segundo desafío fue interactuar con una blockchain ficticia administrada por la cátedra, construyendo dinámicamente un bloque válido y resolviendo un rompecabezas criptográfico (Proof of Work) para que la red lo acepte.

El script (`pow.py`) actúa como un nodo minero automatizado que realiza el ciclo de vida completo de la minería:
1. **Sincronización:** Se conecta mediante HTTP GET para descargar el último bloque válido de la cadena, codificado en Base64.
2. **Construcción del Candidato:** Desarma los 96 bytes del bloque anterior para extraer el número de bloque y el *Target* (objetivo de dificultad). Luego, construye el esqueleto del nuevo bloque sumando 1 al número de bloque, inyectando el *timestamp* actual, calculando el SHA-256 del bloque anterior, y agregando la firma criptográfica del minero (el hash del email registrado).
3. **Minería (PoW):** Utiliza fuerza bruta iterando sobre un espacio de 8 bytes (el *Nonce*). Por cada intento, calcula el hash SHA-256 del bloque completo de 96 bytes y evalúa si el valor numérico resultante es estrictamente menor al *Target* de la red.
4. **Propagación:** Una vez encontrado el *nonce* ganador, codifica el bloque resultante en Base64 y lo envía al servidor mediante un HTTP POST.

### Decisiones de Implementación y Eficiencia
Dado que el proceso de minería requiere millones de cálculos por segundo, el proyecto se optimizó a nivel de manejo de memoria:
* **Uso de `bytearray`:** En Python, el tipo `bytes` es inmutable. Para evitar reconstruir un objeto de 96 bytes en cada ciclo del bucle, se utilizó un `bytearray`. Esto permite sobreescribir únicamente los 8 bytes correspondientes al *nonce* en cada iteración, mejorando drásticamente los *hashes por segundo*.
* **Manejo de Endianness:** Se respetó estrictamente la convención *Big Endian* solicitada por el protocolo de la red para las conversiones entre enteros matemáticos y secuencias binarias (`int.from_bytes` y `to_bytes`).
* **Robustez:** Se implementaron manejos de excepciones específicos (`requests.exceptions.RequestException`) y límites de tiempo (`timeout`) en las peticiones de red para prevenir bloqueos de la aplicación en caso de fallas del servidor.

### Ejecución

Con el entorno virtual activado (ver requisitos en el Desafío 1), ejecuta el minero con:

```bash
python3 pow.py
```

***El script mostrará en consola el bloque descargado, el progreso de la minería, el nonce ganador con su hash respectivo, y la confirmación de aceptación de la red.***