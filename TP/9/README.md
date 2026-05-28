# TP/9: API REST con Contratos Inteligentes

Sistema integrado de gestión de Llamados a Propuestas (CFP - Call For Proposals) que combina contratos Solidity con una API REST de Python, demostrando una arquitectura híbrida on-chain/off-chain.

## Descripción General

Este proyecto implementa una plataforma descentralizada para administrar procesos de compra con transparencia blockchain, mientras mantiene datos descriptivos (títulos, descripciones, archivos) en una base de datos local. El modelo híbrido equilibra el costo y escalabilidad de Ethereum con la flexibilidad de un servidor tradicional.

### Conceptos Clave Implementados

- **Almacenamiento on-chain**: Hashes criptográficos de propuestas en contratos Solidity
- **Almacenamiento off-chain**: Base de datos SQLite con datos descriptivos  
- **Escucha de eventos**: Daemon de Python que sincroniza la base de datos con eventos del contrato
- **Árboles de Merkle**: Pruebas criptográficas que permiten verificar propuestas sin revelar datos completos
- **RLP**: Serialización determinista para calcular identificadores únicos de llamados

Para detalles técnicos de estos conceptos, véase `CONSGINA.md`.

## Estructura del Proyecto

```
TP/9/
├── api/                           # API REST en Flask
│   ├── apiserver.py               # Endpoints REST (register, create, authorize, etc.)
│   ├── database.py                # Esquema y consultas SQLite
│   ├── event_listener.py          # Daemon que escucha eventos de contratos
│   ├── get_admin_address.py       # Deriva dirección del admin desde el mnemonic
│   ├── merkle.py                  # Generador y verificador de pruebas Merkle
│   ├── messages.py                # Tipos de mensajes para validación
│   ├── requirements.txt            # Dependencias (Flask, web3.py, eth-account, etc.)
│   ├── pytest-requirements.txt     # Dependencias para tests (pytest, web3.py, etc.)
│   ├── test_apiserver.py          # Suite de 71 tests de integración
│   └── test/
│       ├── test_db.py             # Tests unitarios de base de datos
│       └── test_merkle.py         # Tests de Merkle tree
│
├── contracts/                     # Contratos Solidity + Hardhat
│   ├── contracts/
│   │   ├── CFP.sol                # Contrato de propuesta individual
│   │   └── CFPFactory.sol         # Factory para crear instancias de CFP
│   ├── test/
│   │   ├── testCFP.js
│   │   ├── testCFPFactory.js
│   │   └── shared.js
│   ├── hardhat.config.js
│   ├── package.json
│   └── package-lock.json
│
├── CONSGINA.md                    # Especificación completa del TP (conceptos y API)
└── img/
    └── merkle-tree.svg
```

## Setup Inicial

### 1. Configurar Contratos

```bash
cd TP/9/contracts
npm install
npm test  # Verifica que los contratos compilan y tests pasan
```

### 2. Configurar API - Ambiente del Servidor

```bash
cd TP/9/api

# Crear virtual environment
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar API - Ambiente de Tests

```bash
cd TP/9/api

# Crear second virtual environment (SEPARADO del servidor)
python3 -m venv venv-test
source venv-test/bin/activate

# Instalar dependencias de testing
pip install -r pytest-requirements.txt
```

## Ejecución

Se requieren **4 terminales separadas** ejecutándose en paralelo. Las direcciones de contrato variarán según tu máquina.

### Terminal 1: Levantar Nodo Ethereum Local (Hardhat)

```bash
cd TP/9/contracts
npx hardhat node
```

Espera hasta ver:
```
Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545/
```

El nodo genera 20 cuentas de prueba con 10,000 ETH cada una. Estas direcciones se utilizarán para todas las transacciones.

### Terminal 2: Desplegar Contratos

```bash
cd TP/9/contracts
node scripts/deploy.js
```

El script imprime la dirección donde se desplegó `CFPFactory`. **Copia esa dirección**, la necesitarás como `CFP_FACTORY_ADDRESS`. También confirma que el mnemonic a usar es `"test test test test test test test test test test test junk"`.

### Terminal 3: Obtener Dirección del Admin

```bash
cd TP/9/api
source venv/bin/activate
python3 get_admin_address.py
```

El script imprime la dirección del administrador derivada del mnemonic. **Copia esa dirección**, la necesitarás como `CFP_ADMIN_ADDRESS`.

### Terminal 3 (Continuación): Iniciar Servidor Flask

```bash
cd TP/9/api
source venv/bin/activate

export CFP_MNEMONIC="test test test test test test test test test test test junk"
export CFP_FACTORY_ADDRESS=<DIRECCION_OBTENIDA_DE_DEPLOY>
export CFP_ADMIN_ADDRESS=<DIRECCION_OBTENIDA_DE_GET_ADMIN>

python3 apiserver.py
```

Espera hasta ver:
```
INFO:werkzeug: * Running on http://127.0.0.1:5000
INFO:event_listener: Event listener iniciado en bloque 1
```

### Terminal 4: Ejecutar Tests

Abre una cuarta terminal y exporta **LAS MISMAS** variables que usaste para el servidor:

```bash
cd TP/9/api
source venv-test/bin/activate

export CFP_MNEMONIC="test test test test test test test test test test test junk"
export CFP_FACTORY_ADDRESS=<DIRECCION_OBTENIDA_DE_DEPLOY>
export CFP_ADMIN_ADDRESS=<DIRECCION_OBTENIDA_DE_GET_ADMIN>

pytest test_apiserver.py -v
```

Resultado esperado:
```
============================================================= 71 passed in 14.08s =============================================================
```

Los tests son **state-dependent** y deben ejecutarse en orden. No reinicies pytest a mitad de la ejecución.

### Resumen del Flujo

1. **Terminal 1**: `npx hardhat node` → Blockchain local corriendo
2. **Terminal 2**: `node scripts/deploy.js` → Anotar `CFP_FACTORY_ADDRESS`
3. **Terminal 3**: `python3 get_admin_address.py` → Anotar `CFP_ADMIN_ADDRESS`
4. **Terminal 3**: Exportar variables (con las direcciones anotadas) + `python3 apiserver.py` → API corriendo
5. **Terminal 4**: Exportar las MISMAS variables + `pytest test_apiserver.py -v` → Tests ejecutando

**Importante**: `CFP_FACTORY_ADDRESS` cambia cada vez que ejecutas `deploy.js`. `CFP_ADMIN_ADDRESS` depende del mnemonic usado. Siempre obtén los valores actuales de `scripts/deploy.js` y `get_admin_address.py`.

## Componentes Principales

### API Server (apiserver.py)

Implementa endpoints REST para:

- **Autenticación**: `POST /register`, `POST /authorize`, `POST /unauthorize`
- **Creación de llamados**: `POST /create` (con validación de call_id via RLP)
- **Consultas**: `GET /calls/{callId}`, `GET /closing-time/{callId}`, `GET /proposal-data/{callId}/{proposalId}`
- **Gestión de propuestas**: `POST /register-proposal`, `POST /verify-proof`
- **Información del contrato**: `GET /contract-address`, `GET /contract-owner`

Todos los endpoints devuelven JSON validado contra esquemas Pydantic.

### Event Listener (event_listener.py)

Daemon que:

1. Se ejecuta en hilo separado dentro del mismo proceso Flask
2. Cada 2 segundos consulta los últimos bloques de Hardhat
3. Procesa eventos `CFPCreated`, `CreatorRegistered`, `CreatorAuthorized`, `CreatorUnauthorized`
4. Actualiza la base de datos local de forma sincronizada con la blockchain
5. Maneja reinicio del servidor: recupera eventos desde el último bloque procesado

Garantiza que la base de datos nunca queda en estado inconsistente.

### Database (database.py)

SQLite con tablas para:

- `creators`: Registros de creadores (dirección, estado, metadata)
- `calls`: Llamados a propuestas (callId, creador, timestamps, estado)
- `proposals`: Propuestas individuales (proposalId, callId, archivos, estado)

Implementa consultas ACID con transacciones explícitas.

### Merkle Proof (merkle.py)

Generador de pruebas Merkle siguiendo la especificación de OpenZeppelin:

- Hojas ordenadas lexicográficamente
- Nodos internos: `keccak256(min(a,b) ++ max(a,b))`
- Compatible con verificación on-chain

Permite probar que un archivo pertenece a una propuesta sin revelar otros archivos.

## Flujo de Operación Típico

1. **Creador se registra**: `POST /register` con firma
2. **Admin autoriza**: `POST /authorize/{address}` 
3. **Creador crea llamado**: `POST /create` con título, descripción, call_id (precalculado via RLP)
4. Event listener detecta `CFPCreated` en contrato
5. Base de datos se actualiza con nuevo llamado
6. **Otros crean propuestas**: `POST /register-proposal` adjuntando archivos
7. Event listener detecta evento
8. **Verificación**: `POST /verify-proof` con Merkle proof para comprobar archivo sin revelar otros

## Troubleshooting

### "Conexión rechazada en 127.0.0.1:5000"

El servidor no está corriendo. Asegúrate de ejecutar Terminal 1 y esperar a ver el mensaje "Running on...".

### "ConnectionError: RemoteDisconnected"

Los tests se conectan al servidor. Si el servidor se cae durante tests, los restantes fallarán. Reinicia ambos terminales.

### "ModuleNotFoundError: No module named 'rlp'"

RLP no está en el venv del servidor. Ejecuta (en Terminal 1):
```bash
pip install rlp==4.1.0
```

### "ValidationError: 'closingTime' is a required property"

Los endpoints pueden tener cambios de estructura. Verifica que `apiserver.py` devuelve las claves correctas en camelCase (no snake_case).

### Tests fallan en orden aleatorio

Los tests tienen dependencias de estado (por diseño). Asegúrate de ejecutar:
```bash
pytest test_apiserver.py -v  # Sin flags -k ni --collect-only
```

No permutes el orden ni ejecutes tests individuales.

### "Database is locked"

Múltiples procesos escribiendo en SQLite simultáneamente. Esto no debería ocurrir con la arquitectura actual (event listener en thread separado). Verifica que no hay múltiples servidores corriendo.

## Variación de Dependencias

El proyecto usa dos archivos `requirements.txt`:

- `requirements.txt`: Dependencias del servidor (Flask, web3.py, eth-account, rlp, pydantic, etc.)
- `pytest-requirements.txt`: Dependencias para tests (pytest, web3.py, eth-account, etc.)

**Nota**: Idealmente debería haber un único `requirements.txt` con todas las dependencias, y `requirements-dev.txt` solo para desarrollo/testing. Esta estructura quedará normalizada en futuras iteraciones.

## Características Implementadas y Validadas

- 71 tests de integración pasando
- Sincronización on-chain/off-chain sin inconsistencias
- Generación y verificación de pruebas Merkle
- Validación de call_id mediante RLP
- Event listener recuperable tras reinicio
- Autorización granular (creadores registrados vs. autorizados)
- Propuestas archivables con cascada de estado
- Validación de entrada con límites de longitud y caracteres especiales

## Referencias

- `CONSGINA.md`: Especificación técnica, ejemplos de código, detalles de RLP y Merkle trees
- `/contracts/README.md`: Detalles de los contratos Solidity
- `test_apiserver.py`: Suite de tests con casos de uso reales (lectura recomendada para entender el flujo)
- OpenZeppelin [MerkleProof.sol](https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/cryptography/MerkleProof.sol)
