# TP Final - Interfaz web

## Stack utilizado

- **Vue 3** (Composition API con `<script setup>`) como framework frontend
- **Vite 8** como bundler y servidor de desarrollo
- **ethers.js v6** para conexion con MetaMask y firma EIP-712
- **vitest** + **jsdom** para pruebas de componentes
- **@vue/test-utils** como utility de testing

## Instalacion y puesta en marcha

```bash
cd TP/Final/web
npm install
npm run dev
```

El servidor de desarrollo queda en `http://localhost:5173`. Las peticiones a
`/api/*` se redirigen al servidor Flask mediante proxy configurado en
`vite.config.js`.

### Requisitos previos

1. Nodo Hardhat corriendo en el puerto 8545
2. Contratos desplegados (ENS + Token + CFPFactory)
3. Servidor Flask de la API corriendo en `http://127.0.0.1:5000`
4. MetaMask instalado, conectado a localhost:8545 (chainId 31337)

## Estructura del proyecto

```
web/
├── src/
│   ├── main.js                    # Punto de entrada Vue
│   ├── App.vue                    # Componente raiz con navegacion y wallet
│   ├── components/
│   │   ├── PublicView.vue         # Vista publica: creadores, llamados, propuestas, entregas
│   │   ├── CreatorPanel.vue       # Panel de creador: registro, perfil, creacion llamados
│   │   ├── AdminPanel.vue         # Panel de admin: autorizar/desautorizar
│   │   ├── ProposalSubmit.vue     # Presentacion de propuesta (anonima o con garantia)
│   │   ├── ReceiptVerifier.vue    # Verificacion de recibo (Merkle + on-chain)
│   │   ├── PostClosingDelivery.vue # Entrega post-cierre con archivos fisicos
│   │   ├── TokenPanel.vue         # Compra y redencion de tokens ERC-20
│   │   ├── EnsPanel.vue           # Resolucion ENS (directa e inversa)
│   │   └── GuaranteePanel.vue     # Finalizar llamado y reclamar reembolso
│   ├── composables/
│   │   ├── useWallet.js           # Conexion/desconexion MetaMask
│   │   └── useApi.js              # Fetch wrapper para endpoints REST
│   ├── utils/
│   │   └── eip712.js              # Builders EIP-712
│   └── tests/
│       ├── PublicView.spec.js
│       ├── ProposalSubmit.spec.js
│       └── PostClosingDelivery.spec.js
├── index.html
├── package.json
└── vite.config.js
```

## Roles y operaciones

### Publico general (sin MetaMask)

| Operacion | Componente |
|-----------|------------|
| Ver creadores registrados | PublicView |
| Ver llamados (por creador o global) | PublicView |
| Presentar propuesta anonima (sin garantia) | ProposalSubmit |
| Verificar recibo (Merkle + on-chain) | ReceiptVerifier |
| Entregar archivos post-cierre | PostClosingDelivery |
| Resolver nombre ENS a direccion | EnsPanel |
| Conversion inversa (direccion a nombre) | EnsPanel |

### Creador (MetaMask conectada, NO admin)

| Operacion | Componente |
|-----------|------------|
| Registro on-chain (MetaMask tx) | CreatorPanel |
| Registro off-chain (firma EIP-712) | CreatorPanel |
| Crear llamado (con garantia opcional y nombre ENS opcional) | CreatorPanel |
| Ver propuestas recibidas | CreatorPanel |
| Comprar tokens ERC-20 | TokenPanel |
| Redimir tokens ERC-20 por ETH | TokenPanel |
| Registrar nombre ENS en usuarios.cfp | CreatorPanel (integrado en registro) |
| Finalizar llamado (solo creador, seleccionando aceptadas) | CreatorPanel |

### Administrador (MetaMask conectada, cuenta == admin)

| Operacion | Componente |
|-----------|------------|
| Autorizar creadores | AdminPanel |
| Desautorizar creadores | AdminPanel |
| Ver solicitudes pendientes | AdminPanel |

### Proponente con garantia

| Operacion | Componente |
|-----------|------------|
| Presentar propuesta con garantia (approve + registerWithCollateral) | ProposalSubmit |
| Reclamar reembolso de garantia (pull mechanism) | GuaranteePanel |

## Flujos nuevos (TP Final)

### Compra de tokens

1. Ir a la pestana "Token"
2. Ingresar cantidad de ETH a convertir
3. Firmar transaccion MetaMask a `CFPGovernanceToken.buy()`
4. Los tokens aparecen en el balance

### Redencion de tokens

1. Ingresar cantidad de tokens a redimir
2. Firmar transaccion MetaMask a `CFPGovernanceToken.redeem(amount)`
3. El ETH se transfiere a la wallet

### Presentacion con garantia

Para llamados con `guaranteeAmount > 0`:

1. Comprar tokens si no se tienen suficientes (TokenPanel)
2. Ir al llamado en PublicView y hacer clic en "Presentar Propuesta"
3. Completar titulo, descripcion y archivos
4. La API responde con `requiresCollateral: true`
5. Paso adicional: firmar `approve()` para autorizar al CFP a gastar tokens
6. Firmar `registerProposalWithCollateral()` para depositar la garantia

### Finalizar llamado

Solo el creador puede finalizar un llamado con garantia:

1. Ir a la pestana "Creador"
2. Expandir el llamado (seccion "Llamados con garantia")
3. Seleccionar las propuestas aceptadas con checkbox
4. Click en "Finalizar llamado y aceptar N propuesta(s)"
5. Firmar la transaccion `finalize(bytes32[])` via MetaMask
6. El contrato marca el llamado como finalizado con la lista de aceptadas

### Reclamar reembolso

Los proponentes no aceptados pueden recuperar su garantia:

1. Ir a la pestana "Garantia"
2. La seccion "Mis Propuestas" carga automaticamente las propuestas del usuario
3. El estado de cada una se verifica on-chain: "Propuesta aceptada" (verde, sin boton) o "Propuesta rechazada" (con boton)
4. Click en "Reclamar Reembolso" para la propuesta rechazada
5. Firmar `claimRefund()` via MetaMask
6. Los tokens vuelven a la wallet del proponente

## Metodos de useApi.js

| Metodo | Endpoint | Proposito |
|--------|----------|-----------|
| getEnsRegistry | GET /ens/registry | Obtener direccion del registry ENS |
| postEnsResolve | POST /ens/resolve | Resolver nombre ENS a direccion |
| postEnsReverse | POST /ens/reverse | Resolucion inversa |
| getTokenAddress | GET /token/address | Obtener direccion del token |
| getTokenName | GET /token/name | Obtener nombre, simbolo, decimals |
| getTokenBalance | GET /token/balance/:addr | Obtener balance de tokens |
| getCallGuarantee | GET /calls/:id/guarantee | Info de garantia de un llamado |
| postCreateCall | POST /create | Crear llamado (acepta guaranteeAmount y ensName) |

## Pruebas

```bash
cd TP/Final/web
npx vitest run
```

## Mapeo endpoint/metodo por flujo (TP Final)

| Componente | Endpoint API | Metodo/Evento Contrato |
|------------|-------------|----------------------|
| EnsPanel | GET /ens/registry, POST /ens/resolve, POST /ens/reverse | — |
| TokenPanel | GET /token/address, GET /token/name, GET /token/balance/:addr | CFPGovernanceToken.buy(), redeem() |
| GuaranteePanel | GET /calls/:id/guarantee | CFP.finalize(), CFP.claimRefund() |
| CreatorPanel (crear) | POST /create (con guaranteeAmount, ensName) | CFPFactory.create(callId, ts, guaranteeAmount) |
| ProposalSubmit | POST /register-proposal | CFPFactory.registerProposal() o CFP.registerProposalWithCollateral() |
| PublicView | GET /calls | — |
