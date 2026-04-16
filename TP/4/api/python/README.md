# Stamper API — Servidor REST

API REST que interactúa con el contrato inteligente `Stamper` desplegado en la red de
prueba de la BFA (Blockchain Federal Argentina), permitiendo registrar y consultar hashes
de 256 bits en la blockchain.

---

## Estructura del proyecto

- `apiserver.py` – Servidor Flask que expone una API REST para interactuar con el contrato `Stamper`.
- `stamper_cli.py` – Cliente de línea de comandos que consume la API para verificar y sellar archivos.
- `test_apiserver.py` – Tests automáticos del servidor.
- `Stamper.json` – ABI y dirección del contrato desplegado en BFA.
- `requirements.txt` – Dependencias Python.

---

## Requisitos

- Python 3.10 o superior
- Un nodo de la BFA sincronizado y en ejecución
- Una cuenta de Ethereum en `~/.ethereum/keystore/` con ether suficiente para pagar gas
- El archivo `Stamper.json` con la ABI y dirección del contrato (incluido en el repositorio)

---

## Instalación

```bash
cd api/python

# Crear y activar el entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Configuración del keystore

La API utiliza la primera cuenta del keystore en orden lexicográfico (la más antigua).
El keystore debe estar en `~/.ethereum/keystore/`.

---

## Ejecución

### Opción A: contraseña interactiva (recomendada)

```bash
python3 apiserver.py
```

El servidor pedirá la contraseña de la cuenta al iniciar. Si es incorrecta, el programa
termina con un mensaje de error.

### Opción B: contraseña desde archivo

Para no tipiar la contraseña, se puede guardar en un archivo:

```bash
echo "contraseña" > ~/.ethereum/password
chmod 600 ~/.ethereum/password   # solo el dueño puede leerlo
```

Y luego pasarla como argunmento para ejecutar el servidor:

```bash
python3 apiserver.py --password-file ~/.ethereum/password
```

El servidor lee ese archivo automáticamente si existe en `~/.ethereum/password`. De lo
contrario, la pide de forma interactiva.

### Verificar que el servidor está activo

```bash
curl http://localhost:5000/stamped/0x836a97e0ff6a85dd2746a39ed71171595759c02beda2d45d0280e0cd19ba3c34
```

Respuesta esperada:
```json
{
  "signer": "0xe694177c2576f6644Cbd0b24bE32a323f88A08D5",
  "blockNumber": 10297664
}
```

---

## Endpoints

### `GET /stamped/:hash`

Consulta si un hash fue registrado en el contrato.

**Parámetro:** `:hash` — hash de 256 bits en formato hexadecimal con prefijo `0x`
(64 caracteres hex + prefijo = 66 caracteres en total).

**Respuestas:**

| Código | Descripción |
|--------|-------------|
| `200`  | Hash encontrado. Devuelve `signer` y `blockNumber`. |
| `404`  | Hash no registrado. |
| `400`  | Formato de hash inválido. |

**Ejemplo exitoso:**
```bash
curl http://localhost:5000/stamped/0x836a97e0ff6a85dd2746a39ed71171595759c02beda2d45d0280e0cd19ba3c34
```
```json
{ "signer": "0xe694177c2576f6644Cbd0b24bE32a323f88A08D5", "blockNumber": 10297664 }
```

---

### `POST /stamp`

Registra un hash en el contrato. El `Content-Type` debe ser `application/json`.

**Cuerpo:**
```json
{
  "hash": "0x...",         
  "signature": "0x..."    
}
```

El campo `signature` es opcional. Si se incluye, se invoca `stampSigned` en el contrato,
registrando como firmante la dirección que produjo esa firma (no quien paga el gas).
Si se omite, se invoca `stamp` y el firmante registrado es la cuenta del servidor.

**Respuestas:**

| Código | Descripción |
|--------|-------------|
| `201`  | Hash registrado. Devuelve `transaction` y `blockNumber`. |
| `403`  | Hash ya registrado. Devuelve además `signer` y `blockNumber` del registro existente. |
| `400`  | Hash o firma con formato inválido, JSON malformado, o Content-Type incorrecto. |

**Ejemplo sin firma:**
```bash
curl -X POST http://localhost:5000/stamp \
     -H "Content-Type: application/json" \
     -d '{"hash": "0xabc123...64chars..."}'
```
```json
{ "transaction": "0x4d2d0d57...", "blockNumber": 37386035 }
```

**Ejemplo con firma:**
```bash
curl -X POST http://localhost:5000/stamp \
     -H "Content-Type: application/json" \
     -d '{"hash": "0xabc123...", "signature": "0x1b8a...130chars..."}'
```

---

## Ejecutar los tests

Con el servidor corriendo en otra terminal:

```bash
pytest test_apiserver.py -v
```

---

## Cliente de línea de comandos (stamper_cli.py)

El script `stamper_cli.py` permite verificar y registrar archivos usando la API REST.
Acepta múltiples archivos en una misma invocación.

**Uso**

```bash
python3 stamper_cli.py verify <archivo1> [<archivo2> ...]
python3 stamper_cli.py stamp <archivo1> [<archivo2> ...]
```

**Ejemplos**

```bash
# Verificar si dos archivos ya fueron sellados
python3 stamper_cli.py verify doc1.pdf doc2.txt

# Registrar un archivo en la blockchain
python3 stamper_cli.py stamp contrato.pdf
```

**Salida esperada**

Para `verify` (no registrado):

```bash
Archivo: doc1.pdf
Hash: 0x8f42fc0e200680603b2033d2dc1dee5fa5ef4ab752dcf8f03f7ac466b3b9f2c7
No sellado
```

Para `verify` (registrado):

```bash
Archivo: doc1.pdf
Hash: 0x836a97e0ff6a85dd2746a39ed71171595759c02beda2d45d0280e0cd19ba3c34
Firmante: 0xe694177c2576f6644Cbd0b24bE32a323f88A08D5
Número de bloque: 10297664
```

Para `stamp` (éxito):

```bash
Archivo: doc1.pdf
Hash: 0x8f42fc0e200680603b2033d2dc1dee5fa5ef4ab752dcf8f03f7ac466b3b9f2c7
Sellado exitoso
```

Para `stamp` (hash ya existente):

```bash
Archivo: doc1.pdf
Hash: 0x8f42fc0e200680603b2033d2dc1dee5fa5ef4ab752dcf8f03f7ac466b3b9f2c7
Hash ya sellado por 0x122F... en bloque 37737698
```

---

## Notas

- El nodo de la BFA debe estar corriendo antes de iniciar el servidor.
  Por defecto se conecta via IPC en `~/blockchain-iua/bfatest/node/geth.ipc`.
- Cada operación `POST /stamp` realiza una transacción en la blockchain y consume gas.
  La cuenta del servidor debe tener ether suficiente.
- El servidor corre en modo desarrollo en `http://127.0.0.1:5000`.