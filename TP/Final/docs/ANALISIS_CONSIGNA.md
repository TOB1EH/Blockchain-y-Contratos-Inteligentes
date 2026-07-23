# Analisis de la Consigna - TP Final

## Estructura requerida

El proyecto debe ubicarse bajo `TP/Final/` con tres componentes:

```
TP/Final/contracts   # Smart contracts (Hardhat)
TP/Final/api         # API REST (Flask)
TP/Final/web         # Interfaz web (Vue 3)
```

Cada componente debe tener su propio `README.md` documentando estructura,
decisiones de diseno y casos de prueba.

## Requisitos funcionales

### 1. ENS (Ethereum Name Service)

#### Contratos necesarios
- **ENSRegistry**: Registro central de nombres (EIP-137)
- **FIFSRegistrar**: Registrador first-in-first-served para `usuarios.cfp`
- **PublicResolver**: Resolutor con soporte addr() y name() (EIP-137, EIP-165, EIP-181)
- **ReverseRegistrar**: Resolucion inversa para `addr.reverse`

#### Dominios
| Dominio | Proposito | Owner |
|---------|-----------|-------|
| `cfp` | TLD del sistema | Owner de CFPFactory (deployer) |
| `usuarios.cfp` | Nombres de usuarios | FIFSRegistrar |
| `llamados.cfp` | Nombres de llamados | Owner de CFPFactory (deployer) |
| `addr.reverse` | Resolucion inversa | ReverseRegistrar |

#### Flujo de registro de usuario
1. Usuario con MetaMask llama a `FIFSRegistrar.register(label, address)` para `usuarios.cfp`
2. Usuario configura resolución directa: `setResolver()` + `setAddr()`
3. Usuario configura resolución inversa: `reverseRegistrar.setName()`
4. Recién entonces puede registrarse como creador en CFPFactory

#### Flujo de registro de llamado
1. Durante `POST /create`, el creador provee un `ensName` (ej: "mi-licitacion")
2. La API (owner de `llamados.cfp`) detecta el evento `CFPCreated` via `event_listener.py`
3. El listener crea el subnodo `mi-licitacion.llamados.cfp` on-chain: `ENSRegistry.setSubnodeOwner()` + `PublicResolver.setAddr()` apuntando al CFP desplegado

#### Anti-spoofing en UI
Para cada direccion mostrada, el frontend debe:
1. Hacer resolución inversa: `resolver.name(node)` -> obtener nombre
2. Hacer resolución directa: `resolver.addr(node)` -> obtener direccion
3. Si `direccion_resuelta == direccion_original` -> mostrar nombre
4. Si no -> mostrar direccion cruda (posible impostura)

### 2. Token ERC-20 con garantia

#### Contrato ERC-20
- Precio fijo en ETH, establecido en el constructor
- Funcion `buy()`: permite comprar tokens enviando ETH
- Funcion `redeem()`: permite redimir tokens por ETH (a precio fijo)
- 18 decimales (estandar Ethereum)

#### Llamados con garantia (`guaranteeAmount > 0`)
- La propuesta deja de ser anonima: requiere MetaMask
- Requiere registro ENS previo del oferente
- `approve`/`transferFrom` del monto de garantia al contrato CFP
- El creador puede finalizar el proceso y determinar reembolsos
- Mecanismo pull: `claimRefund()` para que cada oferente retire sus tokens

#### Llamados sin garantia (`guaranteeAmount == 0`)
- Funcionamiento identico al TP/10 (anonimo, via API)

#### Finalizacion
- `CFP.finalize()` (soloCreator, post-close). Marca `finalized = true`
- `CFP.claimRefund(bytes32 proposal, bytes32[] acceptedProposals)`: cada proponente no aceptado retira su garantia. El creador pasa la lista de aceptados como prueba
- Permite modelar: llamado desierto (todos reembolso) o con ganador(es)

### 3. Modificaciones a componentes existentes

#### CFP.sol
- Agregar `guaranteeAmount` (immutable), `token` (immutable IERC20), `finalized`, `refundClaimed` (mapping), `proposers[]`
- Nueva funcion `registerProposalWithCollateral(bytes32 proposal)`: transfiere `guaranteeAmount` tokens via `transferFrom` al registrar
- Nueva funcion `finalize()` (soloCreator): marca `finalized = true`
- Nueva funcion `claimRefund(bytes32 proposal, bytes32[] calldata acceptedProposals)`: mecanismo pull, verifica que la propuesta no este en `acceptedProposals` y transfiere la garantia al proponente

#### CFPFactory.sol
- Almacenar direccion del token ERC-20 como inmutable
- Modificar `create()` para recibir `guaranteeAmount`
- Struct `CallForProposals` con nuevo campo `guaranteeAmount`

#### API
- `POST /create`: nuevo campo `ensName` (string, opcional) y `guaranteeAmount` (uint, default 0)
- `GET /calls`, `GET /calls/:id`: incluir `guaranteeAmount`, `creator_ens`, `ens_name`
- `GET /creators`, `GET /creators/:id`: incluir `ens` (nombre ENS resuelto inversamente)
- `POST /register-proposal`: rechazar si `guaranteeAmount > 0`
- Nuevos endpoints: `/token/address`, `/ens/addresses`, `/ens/resolve/:name`, `/ens/reverse/:address`
- DB: columnas `guarantee_amount` y `ens_name` en tabla `calls`

#### Frontend
- `EnsPanel.vue`: registro ENS autonomo 4 pasos (FIFSRegistrar → setResolver → setAddr → setName inverso) + verificación forward+reverse + indicador de impostura
- `TokenPanel.vue`: comprar/redimir tokens via MetaMask
- `GuaranteePanel.vue`: registro de propuesta con garantía via `registerProposalWithCollateral` (MetaMask directo)
- `CreatorPanel.vue`: registro de creador, creacion de llamado con `ensName` y `guaranteeAmount`, boton finalizar, validacion ENS antes de registro
- `PublicView.vue`: nombres ENS, `ens_name.llamados.cfp`, badge garantia

## Requisitos de despliegue

El deploy script debe:
1. Desplegar ENS Registry, Resolver, Registrar y ReverseRegistrar
2. Configurar arbol de nodos (cfp, usuarios.cfp, llamados.cfp, addr.reverse)
3. Desplegar Token ERC-20
4. Desplegar CFPFactory (como en TP/10)
5. Imprimir todas las direcciones necesarias para configurar API y web

## Criterios de evaluacion

- Documentacion de decisiones de diseno
- Casos de prueba para nuevas funcionalidades
- Explicacion del codigo en el examen final
