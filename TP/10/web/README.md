# Trabajo Práctico 10 — Interfaz web

## Stack utilizado

- **Vue 3** (Composition API con `<script setup>`) como framework frontend
- **Vite 8** como bundler y servidor de desarrollo
- **ethers.js v6** para conexión con MetaMask y firma EIP-712
- **vitest** + **jsdom** para pruebas de componentes
- **@vue/test-utils** como utility de testing

## Instalación y puesta en marcha

```bash
cd TP/10/web
npm install
npm run dev
```

El servidor de desarrollo queda en `http://localhost:5173`. Las peticiones a `/api/*` se redirigen automáticamente al servidor Flask en `http://127.0.0.1:5000` mediante el proxy configurado en `vite.config.js`, evitando problemas de CORS.

### Requisitos previos

1. Nodo Hardhat corriendo en el puerto 8545 (ver `TP/10/contracts/README.md`)
2. Contrato `CFPFactory` desplegado y variables de entorno configuradas (ver `TP/10/api/README.md`)
3. Servidor Flask de la API corriendo en `http://127.0.0.1:5000`
4. MetaMask instalado en el navegador, conectado a la red local (chainId 31337) con cuentas fondeadas

### Estructura del proyecto

```
web/
├── src/
│   ├── main.js                    # Punto de entrada Vue
│   ├── App.vue                    # Componente raíz con navegación y wallet
│   ├── components/
│   │   ├── PublicView.vue         # Vista pública: creadores, llamados, propuestas, entregas
│   │   ├── CreatorPanel.vue       # Panel de creador: registro, perfil, creación llamados
│   │   ├── AdminPanel.vue         # Panel de admin: autorizar/desautorizar
│   │   ├── ProposalSubmit.vue     # Presentación anónima de propuesta (sin MetaMask)
│   │   ├── ReceiptVerifier.vue    # Verificación de recibo (Merkle + on-chain)
│   │   └── PostClosingDelivery.vue # Entrega post-cierre con archivos físicos
│   ├── composables/
│   │   ├── useWallet.js           # Conexión/desconexión MetaMask
│   │   └── useApi.js              # Fetch wrapper para endpoints REST
│   ├── utils/
│   │   └── eip712.js              # Builders EIP-712 (domain, tipos, mensajes)
│   └── tests/
│       └── PublicView.spec.js     # Test de componente con mock
├── index.html
├── package.json
└── vite.config.js                 # Proxy /api, alias @, config vitest
```

## Roles y operaciones

### Público general (sin MetaMask o sin conectar)

| Operación | Tipo | Endpoint/Método | Componente |
|-----------|------|-----------------|------------|
| Ver creadores registrados | API (GET) | `/creators` | `PublicView.vue` |
| Ver llamados (global o por creador) | API (GET) | `/calls`, `/calls?creator=0x...` | `PublicView.vue` |
| Presentar propuesta anónima | API (POST) | `/register-proposal` | `ProposalSubmit.vue` |
| Verificar recibo (Merkle + on-chain) | API (POST) / MetaMask (lectura) | `/verify-proof`, consulta on-chain `CFP.proposalData()` | `ReceiptVerifier.vue` |
| Entregar archivos post-cierre | API (POST) | `/deliver` | `PostClosingDelivery.vue` |
| Consultar entrega y descargar archivos | API (GET) | `/deliveries/<id>`, `/deliveries/<id>/files/<hash>` | `PublicView.vue` |

### Creador (MetaMask conectada, NO admin)

La UI detecta automáticamente si la cuenta conectada es admin y en ese caso bloquea el registro.

| Operación | Tipo | Endpoint/Método | Componente |
|-----------|------|-----------------|------------|
| Conectar/desconectar wallet | MetaMask | `eth_requestAccounts` | `App.vue` / `useWallet.js` |
| Consultar estado de registro | API (GET) | `/registrations/:address` | `CreatorPanel.vue` |
| Registro on-chain | MetaMask tx | `CFPFactory.register()` | `CreatorPanel.vue` |
| Registro off-chain (firma + POST) | API (POST) + EIP-712 | `POST /register` | `CreatorPanel.vue` |
| Actualizar perfil (firma + PATCH) | API (PATCH) + EIP-712 | `PATCH /registrations/:address` | `CreatorPanel.vue` |
| Crear llamado (doble interacción) | API (POST) + EIP-712 + MetaMask tx | `POST /create` + `CFPFactory.create()` | `CreatorPanel.vue` |

#### Flujo de registro (2 pasos)

1. **On-chain**: usuario firma transacción MetaMask a `CFPFactory.register()`.
   - Mientras espera: `msg = 'Enviando transaccion on-chain...'` y luego `'Esperando confirmacion...'`
   - Confirmada: pasa al Paso 2.
   - Fallida: muestra el error de MetaMask.
2. **Off-chain**: usuario completa nombre, firma mensaje EIP-712 (`RegisterRequest`, operation `"register"`, nonce 0) y lo envía a `POST /register`.
   - Exitosa: estado reflejado en la UI (`pending`, `registered` o `authorized`).
   - Fallida: muestra el mensaje de error devuelto por la API.

#### Flujo de creación de llamado (2 pasos, solo autorizados)

1. **Off-chain**: creador completa título y descripción, firma mensaje EIP-712 (`CreateRequest`, operation `"create"`, `callId`) y lo envía a `POST /create`. La API lo almacena con estado `"pending"`.
2. **On-chain**: creador firma transacción MetaMask a `CFPFactory.create(callId, closingTime)`.
   - Pendiente: se muestra el tx hash mientras se espera confirmación.
   - Confirmada: el estado pasa a `"created"` (detectado por event listener).
   - Fallida: se muestra el error de MetaMask.

#### Estructuras EIP-712 usadas por el creador

**RegisterRequest** (registro: `operation = "register"`, nonce 0; actualización: `operation = "update"`, nonce actual):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `operation` | `string` | `"register"` o `"update"` |
| `contract` | `address` | Dirección del `CFPFactory` |
| `nonce` | `uint256` | 0 para registro, nonce actual para update |
| `name` | `string` | Nombre del creador |

**CreateRequest** (creación de llamado: `operation = "create"`):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `operation` | `string` | `"create"` |
| `contract` | `address` | Dirección del `CFPFactory` |
| `callId` | `bytes32` | `keccak256(rlp([title_utf8, desc_utf8]))` |

### Administrador (MetaMask conectada, cuenta == `CFP_ADMIN_ADDRESS`)

La UI compara `account` contra `GET /admin/address`. Solo si coinciden se muestra el panel.

| Operación | Tipo | Endpoint/Método | Componente |
|-----------|------|-----------------|------------|
| Verificar rol admin | API (GET) | `/admin/address` | `AdminPanel.vue` |
| Ver solicitudes pendientes | API (GET) | `/admin/pending` | `AdminPanel.vue` |
| Autorizar creador (firma + POST) | API (POST) + EIP-712 | `POST /authorize/:address` | `AdminPanel.vue` |
| Desautorizar creador (firma + POST) | API (POST) + EIP-712 | `POST /unauthorize/:address` | `AdminPanel.vue` |
| Obtener nonce admin | API (GET) | `/admin/nonce` | `AdminPanel.vue` |

#### Estructuras EIP-712 usadas por el admin

**AdminActionRequest** (autorizar: `operation = "authorize"`; desautorizar: `operation = "unauthorize"`):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `operation` | `string` | `"authorize"` o `"unauthorize"` |
| `contract` | `address` | Dirección del `CFPFactory` |
| `nonce` | `uint256` | Nonce actual del admin (de `GET /admin/nonce`) |
| `target` | `address` | Dirección a autorizar/desautorizar |

## Dominio EIP-712 común

Todas las firmas usan el mismo dominio:

```json
{
  "name": "CFP API",
  "version": "1",
  "chainId": <id de la cadena>,
  "verifyingContract": "<dirección del CFPFactory>"
}
```

El `chainId` se obtiene dinámicamente de MetaMask (`provider.getNetwork().chainId`). La dirección del contrato se obtiene de `GET /contract-address`.

## Manejo de errores

| Situación | Comportamiento |
|-----------|----------------|
| MetaMask no instalado | `walletError = 'MetaMask no instalado'`; botón conectar inhabilitado; vistas públicas funcionales |
| Usuario rechaza conexión | `walletError` con el mensaje de MetaMask |
| Red incorrecta (no 31337) | Mensaje rojo: "Red incorrecta (debe ser 31337)" |
| Cuenta conectada es admin e intenta registrarse | Mensaje: "No puedes registrarte como creador con la cuenta administradora." (backend devuelve 403 ADMIN_CANNOT_REGISTER) |
| Firma inválida | API devuelve `INVALID_SIGNATURE`; se muestra en `msg` del panel |
| Nonce inválido | API devuelve `INVALID_SIGNATURE` (nonce incorrecto en la firma) |
| No autorizado | API devuelve `UNAUTHORIZED` (creador no autorizado intenta create) |
| Convocatoria no cerrada | API devuelve `CALL_NOT_CLOSED` al intentar entregar en llamado abierto |
| Entrega ya registrada | API devuelve `ALREADY_DELIVERED` al intentar entregar dos veces |
| Recibo inválido | API devuelve `INVALID_PROPOSAL` si el recibo o los hashes no coinciden |
| Transacción revertida | MetaMask muestra el error; se captura y muestra en `msg` |
| Transacción pendiente | `msg` muestra el tx hash y "Esperando confirmacion..." |
| Transacción confirmada | `msg` actualiza con resultado exitoso |
| Conexión perdida | MetaMask emite `accountsChanged` con array vacío; `disconnectWallet()` limpia el estado |
| Cambio de cuenta/red | MetaMask emite `accountsChanged`/`chainChanged`; `connectWallet()` se re-ejecuta |

## Estados transaccionales

Para cada operación on-chain (`CFPFactory.register()`, `CFPFactory.create()`, etc.) la UI contempla:

1. **Pendiente**: después de firmar en MetaMask, antes de `tx.wait()`. Se muestra el tx hash.
2. **Confirmada**: después de `tx.wait()` exitoso. Se actualiza el estado del creador.
3. **Fallida/revertida**: si MetaMask rechaza o la tx revierte, se captura en `catch` y se muestra el error.

## Flujos de Etapa 3

### Presentación de propuesta (anónima, sin MetaMask)

Cualquier usuario puede presentar una propuesta para un llamado:

| Paso | Acción | Componente |
|------|--------|------------|
| 1 | Seleccionar llamado abierto | `PublicView.vue` |
| 2 | Ingresar título, descripción y archivos | `ProposalSubmit.vue` |
| 3 | El navegador calcula hashes keccak256 localmente (FileReader) | `ProposalSubmit.vue` |
| 4 | Enviar solo los hashes a la API (`POST /register-proposal`) | `ProposalSubmit.vue` vía `useApi.js` |
| 5 | La API registra el compromiso on-chain y devuelve recibo (`proposalId` + pruebas Merkle) | API |
| 6 | Descargar recibo JSON verificable | `ProposalSubmit.vue` |

### Verificación de recibo

| Paso | Acción | Componente |
|------|--------|------------|
| 1 | Cargar recibo JSON descargado | `ReceiptVerifier.vue` |
| 2 | Verificar pruebas Merkle contra `proposalId` vía API (`POST /verify-proof`) | `ReceiptVerifier.vue` vía `useApi.js` |
| 3 | (Opcional) Consultar `CFP.proposalData(proposalId)` on-chain con MetaMask | `ReceiptVerifier.vue` |

### Entrega post-cierre

Una vez cerrado el llamado, el oferente entrega los archivos físicos:

| Paso | Acción | Componente |
|------|--------|------------|
| 1 | Cargar recibo original + todos los archivos comprometidos | `PostClosingDelivery.vue` |
| 2 | Enviar a `POST /deliver` como `multipart/form-data` | `PostClosingDelivery.vue` vía `useApi.js` |
| 3 | La API verifica hashes contra el recibo y registra `registerDelivery()` on-chain | API |
| 4 | La API almacena archivos en disco y actualiza DB | API |
| 5 | Confirmación de entrega exitosa | `PostClosingDelivery.vue` |

### Consulta pública de entregas

| Operación | Tipo | Endpoint/Método | Componente |
|-----------|------|-----------------|------------|
| Ver datos de entrega | API (GET) | `/deliveries/<proposal_id>` | `PublicView.vue` |
| Descargar archivo | API (GET) | `/deliveries/<proposal_id>/files/<hash>` | `PublicView.vue` |

## Pruebas

```bash
cd TP/10/web
npx vitest run
```

Usan `vi.mock()` para simular la API (`useApi.js`) y `@vue/test-utils` para montar componentes. Entorno jsdom.

## Mapeo endpoint/método por flujo (Etapa 2 y 3)

| Pantalla | Endpoint API | Método/Evento Contrato |
|----------|-------------|----------------------|
| `PublicView.vue` (creadores) | `GET /creators` | — |
| `PublicView.vue` (llamados) | `GET /calls`, `GET /calls?creator=0x...` | `CFPFactory.calls()`, `CFPFactory.createdByCount()` |
| `PublicView.vue` (propuesta) | — | Botón abre `ProposalSubmit.vue` |
| `PublicView.vue` (entrega) | — | Botón abre `PostClosingDelivery.vue` (solo cerrados) |
| `PublicView.vue` (ver archivos) | `GET /deliveries/<proposal_id>`, `GET /deliveries/.../files/<hash>` | — |
| `CreatorPanel.vue` (registro) | `POST /register` | `CFPFactory.register()` (tx MetaMask) |
| `CreatorPanel.vue` (estado) | `GET /registrations/:address` | `CFPFactory.isRegistered()`, `CFPFactory.isAuthorized()` |
| `CreatorPanel.vue` (perfil) | `PATCH /registrations/:address` | — |
| `CreatorPanel.vue` (crear llamado) | `POST /create` | `CFPFactory.create(callId, closingTime)` (tx MetaMask) |
| `AdminPanel.vue` | `GET /admin/address`, `GET /admin/nonce`, `GET /admin/pending` | `CFPFactory.owner()`, `CFPFactory.getAllPending()` |
| `AdminPanel.vue` (autorizar) | `POST /authorize/:address` | — |
| `AdminPanel.vue` (desautorizar) | `POST /unauthorize/:address` | — |
| `ProposalSubmit.vue` | `POST /register-proposal` | `CFPFactory.registerProposal()` (API firma con server_account) |
| `ReceiptVerifier.vue` | `POST /verify-proof` | `CFP.proposalData(proposalId)` (lectura on-chain opcional con MetaMask) |
| `PostClosingDelivery.vue` | `POST /deliver` | `CFP.registerDelivery()` (API firma con server_account) |

## Configuración del proxy

En `vite.config.js` se define:

```js
server: {
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:5000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, ''),
    },
  },
}
```

El frontend llama a `/api/creators`, `/api/register`, etc. Vite reenvía a `http://127.0.0.1:5000/creators`, `http://127.0.0.1:5000/register`.
