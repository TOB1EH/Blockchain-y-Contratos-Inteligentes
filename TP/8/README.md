# TP8 — API REST para CFP y CFPFactory

API REST en Python/Flask que interactúa con los contratos inteligentes `CFP` y
`CFPFactory` del TP7, permitiendo registrar usuarios, crear llamados a presentación
de propuestas y registrar propuestas en la blockchain.

---

## Requisitos previos

- Python 3.10 o superior
- Node.js y npm (para levantar el nodo y desplegar los contratos del TP7)
- El directorio del TP7 compilado (`artifacts/` presente)

---

## Instalación

Desde la carpeta `TP/8/`:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Configuración: variables de entorno

El servidor requiere las siguientes variables de entorno. **No modificar el código**,
solo configurar estas variables antes de ejecutar.

| Variable               | Descripción                                              | Valor por defecto       |
|------------------------|----------------------------------------------------------|-------------------------|
| `CFP_MNEMONIC`         | Frase mnemónica BIP39 de la cuenta que desplegó el contrato | (requerida)         |
| `CFP_FACTORY_ADDRESS`  | Dirección del contrato `CFPFactory` desplegado           | (requerida)             |
| `CFP_RPC_URL`          | URL del nodo Ethereum                                    | `http://localhost:8545` |
| `CFP_TP7_DIR`          | Ruta al directorio del TP7 (donde están los `artifacts/`)| `../7`                  |

---

## Pasos para ejecutar

Se necesitan cuatro terminales abiertas en paralelo.

### Terminal 1 — Levantar el nodo local

Desde el directorio del TP7:

```bash
cd TP/7
npx hardhat node
```

Dejar esta terminal corriendo. El nodo escucha en `http://127.0.0.1:8545`.

### Terminal 2 — Desplegar el contrato

Desde el directorio del TP7, con el nodo ya corriendo:

```bash
cd TP/7
npx hardhat compile

node ../8/scripts/deploy.js

# ó

npx hardhat run ../8/scripts/deploy.js --network localhost
```

El script imprime la dirección del contrato desplegado. Por ejemplo:

```
CFPFactory desplegado en: 0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512
```

Copiar esa dirección para el siguiente paso.

### Terminal 3 — Configurar variables y lanzar la API

```bash
cd TP/8
source venv/bin/activate

export CFP_MNEMONIC="la frase mnemónica de doce palabras aquí"
export CFP_FACTORY_ADDRESS="0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"

# Opcionales (solo si diferente del default):
# export CFP_RPC_URL="http://localhost:8545"
# export CFP_TP7_DIR="../7"

python3 apiserver.py
```

El servidor queda escuchando en `http://127.0.0.1:5000`.

### Terminal 4 — Ejecutar los tests

```bash
cd TP/8
source venv/bin/activate
pytest test_apiserver.py -v
```

---

## Nota sobre `hardhat node`

Si se usa `npx hardhat node` como nodo local, la frase mnemónica es siempre:

```
test test test test test test test test test test test junk
```

La cuenta en el índice 0 (`m/44'/60'/0'/0/0`) es la que despliega el contrato
y queda como owner de `CFPFactory`. El servidor usa esa misma cuenta para firmar
y pagar el gas de todas las transacciones.

---

## Endpoints disponibles

| Método | Endpoint                          | Descripción                              |
|--------|-----------------------------------|------------------------------------------|
| GET    | `/contract-address`               | Dirección del contrato CFPFactory        |
| GET    | `/contract-owner`                 | Dirección del owner del contrato         |
| GET    | `/authorized/:address`            | Estado de autorización de una cuenta     |
| GET    | `/calls/:call_id`                 | Datos de un llamado                      |
| GET    | `/closing-time/:call_id`          | Fecha de cierre de un llamado            |
| GET    | `/proposal-data/:call_id/:proposal` | Datos de una propuesta               |
| POST   | `/register`                       | Registrar y autorizar una cuenta         |
| POST   | `/create`                         | Crear un llamado a propuestas            |
| POST   | `/register-proposal`              | Registrar una propuesta en un llamado    |

---

## Estructura del proyecto

```
TP/8/
├── apiserver.py          ← servidor Flask
├── messages.py           ← constantes de mensajes de error
├── test_apiserver.py     ← tests automáticos
├── requirements.txt      ← dependencias Python
├── scripts/
│   └── deploy.js         ← script de despliegue del contrato
└── README.md             ← este archivo
```