# TP Final - API REST

API REST que interactua con los contratos del TP Final (ENS, Token ERC-20,
CFPFactory, CFP) y extiende la API del TP 10.

## Stack

- Flask 3.1.3
- Web3.py 7.x
- SQLite (base de datos local)
- eth-account (firmas EIP-712)

## Variables de entorno

| Variable | Requerida | Descripcion |
|----------|-----------|-------------|
| CFP_MNEMONIC | Si | Mnemonico BIP39 del owner del contrato |
| CFP_FACTORY_ADDRESS | Si | Direccion del CFPFactory desplegado |
| CFP_ADMIN_ADDRESS | Si | Direccion de la cuenta administradora (indice 2) |
| CFP_ENS_REGISTRY | Si | Direccion del ENSRegistry |
| CFP_ERC20_TOKEN | Si | Direccion del token ERC-20 |
| CFP_WEB3_URI | No | URL del nodo Ethereum (default http://localhost:8545) |
| CFP_CONTRACTS_DIR | No | Ruta a contratos compilados (default ../contracts) |
| CFP_DB_PATH | No | Ruta de la base de datos (default cfp.db) |

## Endpoints nuevos (TP Final)

### ENS

#### `GET /ens/registry`
Devuelve la direccion del registry ENS.

#### `POST /ens/resolve`
Resuelve un nombre ENS a direccion. Cuerpo: `{"name": "alice.usuarios.cfp"}`.
Retorno: `{"address": "0x...", "name": "alice.usuarios.cfp"}`.

#### `POST /ens/reverse`
Resolucion inversa. Cuerpo: `{"address": "0x..."}`.
Retorno: `{"name": "alice.usuarios.cfp", "address": "0x..."}`.

### Token

#### `GET /token/address`
Devuelve la direccion del token ERC-20.

#### `GET /token/name`
Devuelve nombre, simbolo, decimals y tokensPerEth del token.

#### `GET /token/balance/<address>`
Devuelve el balance de tokens de una direccion: `{"balance": "1000000000000000000"}`.

### Garantia

#### `GET /calls/<call_id>/guarantee`
Devuelve informacion de la garantia de un llamado:
```json
{
  "guaranteeAmount": "100",
  "token": "0x...",
  "finalized": false
}
```

## Endpoints modificados (vs TP 10)

### `POST /create`
Ahora acepta campos adicionales:
- `guaranteeAmount`: entero, monto de tokens requerido como garantia (0 = sin garantia)
- `ensName`: string opcional, nombre ENS para registrar en `llamados.cfp`

Retorna ademas:
- `guaranteeAmount`: el monto configurado
- `ensName`: el nombre ENS (si se proporciono)

### `POST /register-proposal`
Ahora detecta si el llamado requiere garantia consultando la DB. Si
`guarantee_amount > 0`, la respuesta incluye:
- `requiresCollateral: true`
- `cfpAddress`: direccion del contrato CFP
- `guaranteeAmount`: monto de tokens requerido

En este caso la API NO envia la transaccion on-chain. El proponente debe
ejecutar `approve` + `registerProposalWithCollateral` via MetaMask.

### `GET /calls/<call_id>`
Ahora incluye el campo `guaranteeAmount` (0 si no tiene garantia) y
`ens_name` (string o null).

## Mensajes nuevos (TP Final)

| ID | Mensaje |
|----|---------|
| INVALID_AMOUNT | "Monto invalido" |
| ENS_NAME_NOT_FOUND | "Nombre ENS no encontrado" |
| ENS_ADDRESS_NOT_FOUND | "Direccion ENS no encontrada" |
| CALL_FINALIZED | "El llamado ya fue finalizado" |
| NO_COLLATERAL_NEEDED | "El llamado no requiere garantia" |
| COLLATERAL_ALREADY_SENT | "La garantia ya fue depositada" |

## Base de datos

Tabla `calls` modificada: se agrega columna `ens_name TEXT` para almacenar
el nombre ENS del llamado (opcional).

El resto de las tablas se mantienen igual que en TP 10.

## Event listener

El event listener ahora tambien registra nombres ENS en `llamados.cfp` cuando
el evento `CFPCreated` se dispara para un llamado que tiene `ens_name` configurado.

El flujo es:
1. El listener detecta `CFPCreated` y actualiza el estado del llamado a "created"
2. Si el llamado tiene `ens_name`, ejecuta transacciones on-chain para:
   - Crear el subnodo `<ens_name>.llamados.cfp` en el ENSRegistry
   - Configurar el resolver
   - Asignar la direccion del contrato CFP via `resolver.setAddr()`

La API firmas estas transacciones con la cuenta del servidor (owner del
CFPFactory), que es la duena del dominio `llamados.cfp`.

## Tests

```bash
pytest test_apiserver.py -v
```

Los tests de las funcionalidades nuevas (ENS, Token, Garantia) estan
pendientes de implementacion.

## Arranque

```bash
# 1. Nodo local
cd contracts && npx hardhat node

# 2. Desplegar contratos (otra terminal)
cd contracts && npm run deploy

# 3. Exportar variables y lanzar API
export CFP_MNEMONIC="..."
export CFP_FACTORY_ADDRESS=0x...
export CFP_ADMIN_ADDRESS=0x...
export CFP_ENS_REGISTRY=0x...
export CFP_ERC20_TOKEN=0x...
python3 apiserver.py

# 4. Tests (entorno separado)
python3 -m venv venv-test
source venv-test/bin/activate
pip install -r pytest-requirements.txt
pytest test_apiserver.py -v
```

## Decisiones de diseno

Ver `docs/DECISIONES_DISENO.md` en la raiz del proyecto.
