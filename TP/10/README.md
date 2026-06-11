# Trabajo Práctico 10 — Sistema CFP (Call for Proposals)

Tres componentes que operan en conjunto:

- **`contracts/`** — Smart contracts en Solidity (Hardhat)
- **`api/`** — API REST en Flask + Python
- **`web/`** — Interfaz web en Vue 3 + Vite

---

## 1. Puesta en marcha (tres terminales)

### Terminal 1 — Blockchain local + despliegue de contratos

```bash
cd TP/10/contracts
npx hardhat node
```

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

### Terminal 2 — Servidor de API

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

Creadores autorizados pueden crear llamados (Etapa 2).

- Consultar estado (`GET /registrations/:address`)
- Actualizar perfil (`PATCH /registrations/:address`, firma EIP-712)

### Público general

Sin MetaMask. Consulta:

- Listado de creadores (`GET /creators`)
- Listado de llamados (Etapa 2)

---

## 3. Arquitectura e integración

### On-chain (MetaMask)

| Acción | Método del contrato |
|---|---|---|
| Registro de creador | `CFPFactory.register()` |
| Creación de llamado | `CFPFactory.create()` |
| Autorización/Desautorización | `CFPFactory.authorize()` / `CFPFactory.unauthorize()` |

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

72 tests con firmas EIP-712. Requiere dos venv separados: `venv/` para el servidor y `venv-test/` para los tests.

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

