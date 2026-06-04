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
│   │   ├── PublicView.vue         # Vista pública: listado de creadores
│   │   ├── CreatorPanel.vue       # Panel de creador: registro y perfil
│   │   └── AdminPanel.vue         # Panel de admin: autorizar/desautorizar
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

### Creador (MetaMask conectada, NO admin)

La UI detecta automáticamente si la cuenta conectada es admin y en ese caso bloquea el registro.

| Operación | Tipo | Endpoint/Método | Componente |
|-----------|------|-----------------|------------|
| Conectar/desconectar wallet | MetaMask | `eth_requestAccounts` | `App.vue` / `useWallet.js` |
| Consultar estado de registro | API (GET) | `/registrations/:address` | `CreatorPanel.vue` |
| Registro on-chain | MetaMask tx | `CFPFactory.register()` | `CreatorPanel.vue` |
| Registro off-chain (firma + POST) | API (POST) + EIP-712 | `POST /register` | `CreatorPanel.vue` |
| Actualizar perfil (firma + PATCH) | API (PATCH) + EIP-712 | `PATCH /registrations/:address` | `CreatorPanel.vue` |

#### Flujo de registro (2 pasos)

1. **On-chain**: usuario firma transacción MetaMask a `CFPFactory.register()`.
   - Mientras espera: `msg = 'Enviando transaccion on-chain...'` y luego `'Esperando confirmacion...'`
   - Confirmada: pasa al Paso 2.
   - Fallida: muestra el error de MetaMask.
2. **Off-chain**: usuario completa nombre, firma mensaje EIP-712 (`RegisterRequest`, operation `"register"`, nonce 0) y lo envía a `POST /register`.
   - Exitosa: estado reflejado en la UI (`pending`, `registered` o `authorized`).
   - Fallida: muestra el mensaje de error devuelto por la API.

#### Estructuras EIP-712 usadas por el creador

**RegisterRequest** (registro: `operation = "register"`, nonce 0; actualización: `operation = "update"`, nonce actual):

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `operation` | `string` | `"register"` o `"update"` |
| `contract` | `address` | Dirección del `CFPFactory` |
| `nonce` | `uint256` | 0 para registro, nonce actual para update |
| `name` | `string` | Nombre del creador |

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
| Transacción revertida | MetaMask muestra el error; se captura y muestra en `msg` |
| Transacción pendiente | `msg` muestra el tx hash y "Esperando confirmacion..." |
| Transacción confirmada | `msg` actualiza con resultado exitoso |
| Conexión perdida | MetaMask emite `accountsChanged` con array vacío; `disconnectWallet()` limpia el estado |
| Cambio de cuenta/red | MetaMask emite `accountsChanged`/`chainChanged`; `connectWallet()` se re-ejecuta |

## Estados transaccionales

Para cada operación on-chain (actualmente solo `CFPFactory.register()`) la UI contempla:

1. **Pendiente**: después de firmar en MetaMask, antes de `tx.wait()`. Se muestra el tx hash.
2. **Confirmada**: después de `tx.wait()` exitoso. Se actualiza el estado del creador.
3. **Fallida/revertida**: si MetaMask rechaza o la tx revierte, se captura en `catch` y se muestra el error.

## Pruebas

```bash
cd TP/10/web
npx vitest run
```

Usan `vi.mock()` para simular la API (`useApi.js`) y `@vue/test-utils` para montar componentes. Entorno jsdom.

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
