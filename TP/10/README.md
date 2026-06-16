# Trabajo Práctico 10 — Sistema CFP (Call for Proposals)

Tres componentes que operan en conjunto:

- **`contracts/`** — Smart contracts en Solidity (Hardhat)
- **`api/`** — API REST en Flask + Python
- **`web/`** — Interfaz web en Vue 3 + Vite

---

## 1. Puesta en marcha (tres terminales)

### Terminal 1 — Blockchain local

```bash
cd TP/10/contracts
npx hardhat node
```

### Terminal 2 - despliegue de contratos

En otra terminal (sin cerrar la anterior):

```bash
cd TP/10/contracts
node scripts/deploy.js
```

La salida del deploy imprime las variables necesarias:
- `CFP_MNEMONIC`: frase owner del contrato (solo API, nunca en MetaMask)
- `CFP_FACTORY_ADDRESS`: dirección del contrato desplegado
- `CFP_ADMIN_ADDRESS`: cuenta admin (primera cuenta de la frase MetaMask)
- `CFP_METAMASK_MNEMONIC`: frase independiente para importar en MetaMask

Copiar estos valores. Se usan en los pasos siguientes.

> **Importante**: Las cuentas de MetaMask se fondean automáticamente con 1000 ETH cada una durante el deploy. Para fondeo manual existe `node scripts/fund.js "<frase_metamask>"`.

### Terminal 3 — Servidor de API

```bash
cd TP/10/api
source venv/bin/activate
export CFP_MNEMONIC="<valor del deploy>"
export CFP_FACTORY_ADDRESS="<valor del deploy>"
export CFP_ADMIN_ADDRESS="<valor del deploy>"
export CFP_METAMASK_MNEMONIC="<valor del deploy>"
python3 apiserver.py
```

El servidor queda escuchando en `http://127.0.0.1:5000`.

### Terminal 3 — Interfaz web

```bash
cd TP/10/web
npm install
npm run dev
```

El servidor de desarrollo queda en `http://localhost:5173`. \
Las peticiones a `/api/*` se redirigen automáticamente al backend Flask (configurado en `vite.config.js`), evitando problemas de CORS.

---

## 2. Roles y funcionalidades

### Administrador

La cuenta `CFP_ADMIN_ADDRESS` (primera cuenta derivada de la frase MetaMask, completamente independiente de `CFP_MNEMONIC`). No tiene privilegios sobre el contrato; solo firma EIP-712 para la API. Visible si la wallet conectada coincide.

- Listar solicitudes de registro pendientes (`GET /admin/pending`)
- Autorizar creadores (`POST /authorize/:address`)
- Desautorizar creadores (`POST /unauthorize/:address`)

Todas las operaciones requieren firma EIP-712 (`AdminActionRequest`).

### Creador

Cualquier cuenta puede registrarse en dos pasos:

1. **On-chain**: transacción MetaMask al `CFPFactory` (método `register()`)
2. **Off-chain**: firma EIP-712 (`RegisterRequest`) enviada a `POST /register`

Estados posibles (consultados on-chain como fuente de verdad):
- `pending`: ninguna interacción, o solo una de las dos (on-chain o API)
- `registered`: ambas interacciones completadas, pendiente de autorización
- `authorized`: autorizado por el administrador para crear llamados

Creadores autorizados pueden crear llamados mediante doble interacción:
1. **Off-chain**: firma EIP-712 (`CreateRequest`) enviada a `POST /create`
2. **On-chain**: transacción MetaMask a `CFPFactory.create(callId, timestamp)`

El frontend calcula el `callId` como `keccak256(rlp.encode([title, description]))`.

- Consultar estado (`GET /registrations/:address`)
- Actualizar perfil (`PATCH /registrations/:address`, firma EIP-712)
- **Cerrar un llamado** (`POST /close-call`, firma `CreateRequest` con `operation: "close"`): cierra el período de propuestas on-chain una vez expirado `closingTime`.
- Consultar entregas de sus llamados (`GET /deliveries/<call_id>`)
- Descargar archivos de entrega (`GET /deliveries/:call_id/:proposal_id/files/<hash>`)

### Público general / Oferente

Sin MetaMask. Puede realizar consultas y operaciones sobre llamados:

- Listado de creadores (`GET /creators`)
- Listado de llamados globales y filtrados por creador (`GET /calls?creator=0x...`)

**Presentación de propuestas anónimas** (Etapa 3):

1. El oferente completa título y descripción en el formulario web
2. El frontend calcula `keccak256(propuesta)` como identificador local
3. `POST /register-proposal` con `{ callId, title, description }`
4. La API firma y envía `CFP.registerProposal()` on-chain usando su cuenta owner
5. La API devuelve un **recibo JSON** con: `callId`, `proposalId`, `proof` (prueba Merkle), `title`, `description`
6. El oferente descarga el recibo como archivo `.json` para verificación futura

**Verificación de recibos** (Etapa 3):

1. `POST /verify-proof`: subir el archivo JSON de recibo
2. Verificación **off-chain**: prueba Merkle contra `proposalId`
3. Verificación **on-chain**: consulta existencia de `proposalId` en el contrato CFP

**Entrega post-cierre** (Etapa 3, solo para llamados cerrados):

1. `POST /deliver` con `multipart/form-data`: campo `receipt` (archivo JSON) + uno o más archivos físicos
2. La API llama a `CFP.registerDelivery()` on-chain y espera confirmación
3. Los archivos se almacenan en `api/uploads/` y quedan accesibles públicamente
4. Consultar entregas de un llamado (`GET /deliveries/<call_id>`)
5. Descargar archivos individuales (`GET /deliveries/:call_id/:proposal_id/files/<hash>`)

---

## 3. Arquitectura e integración

### On-chain (MetaMask)

| Acción | Método del contrato | Etapa |
|---|---|---|---|
| Registro de creador | `CFPFactory.register()` | 1 |
| Autorización / Desautorización | `CFPFactory.authorize()` / `CFPFactory.unauthorize()` | 1 |
| Creación de llamado | `CFPFactory.create()` | 2 |
| Cierre de llamado | `CFPFactory.closeCall()` | 2 |
| Presentación de propuesta | `CFP.registerProposal()` (API firma con cuenta owner) | 3 |
| Consulta de cierre | `CFP.closingTime()` (lectura) | 3 |
| Registro de entrega | `CFP.registerDelivery()` (API firma con cuenta owner) | 3 |

### Off-chain (API + EIP-712)

Todas las firmas usan el dominio EIP-712:

```json
{
  "name": "CFP API",
  "version": "1",
  "chainId": 31337,
  "verifyingContract": "<CFP_FACTORY_ADDRESS>"
}
```

Tipos de mensaje:

- `RegisterRequest` — registro y actualización de perfil (`operation: "register"` / `"update"`)
- `AdminActionRequest` — autorización y desautorización (`operation: "authorize"` / `"unauthorize"`)
- `CreateRequest` — creación de llamados (`operation: "create"`)

---

## 4. Pruebas

### Contratos (Hardhat)

```bash
cd TP/10/contracts
npm test
```

67 tests sobre CFPFactory, CFP, eventos y registro de entregas.

### API (pytest)

Requiere las mismas variables de entorno que el servidor. Usa un venv separado.

```bash
cd TP/10/api
source venv-test/bin/activate
export CFP_MNEMONIC="..."
export CFP_FACTORY_ADDRESS="..."
export CFP_ADMIN_ADDRESS="..."
export CFP_METAMASK_MNEMONIC="..."
pytest test_apiserver.py -v
```

87 tests (Etapas 1, 2 y 3). Requiere dos venv separados: `venv/` para el servidor y `venv-test/` para los tests.

### Interfaz web (vitest)

```bash
cd TP/10/web
npx vitest run
```

Pruebas de componentes con jsdom.

---

## 5. Base de datos off-chain

La API usa SQLite (`cfp.db`) con las siguientes tablas:

- **registrations** — `address` (PK), `name`, `nonce`. Solo metadatos off-chain; el estado se consulta on-chain.
- **admin_state** — `id` (PK), `nonce`. Contador de operaciones del administrador para anti-replay.
- **calls** — `call_id` (PK), `title`, `description`, `creator`, `cfp_address`, `status` (`pending`/`created`). El event listener actualiza `creator` y `cfp_address` al detectar `CFPCreated` on-chain.
- **proposals** — `proof_json`, `title`, `description`, `call_id`, `proposal_id` (PK). Pruebas de Merkle para verificación off-chain (Etapa 3).
- **deliveries** — `id` (PK), `call_id`, `proposal_id`, `receipt_json`, `created_at`. Registro de entregas post-cierre (Etapa 3).
- **proposal_files** — `id` (PK), `delivery_id` (FK → deliveries.id), `file_hash`, `filename`, `created_at`. Archivos físicos subidos en cada entrega (Etapa 3).

