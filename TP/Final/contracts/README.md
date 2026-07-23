# TP Final - Smart contracts

El proyecto extiende los contratos del TP 10 con tres nuevas funcionalidades:
ENS (Ethereum Name Service), Token ERC-20 de gobernanza, y garantia de oferta
con devolucion mediante mecanismo pull.

## Contratos

### Contratos nuevos (TP Final)

#### `ENSRegistry.sol`

Registro central ENS (EIP-137). Mapea nodos (namehash) a propietario, resolutor
y TTL. El nodo raiz (bytes32(0)) pertenece al deployer.

Constructor sin argumentos. El deployer es dueno del nodo raiz.

Eventos: `NewOwner`, `Transfer`, `NewResolver`, `NewTTL`, `ApprovalForAll`.

#### `FIFSRegistrar.sol`

Registrador FIFS (First In First Served) para un dominio especifico. Gestiona
los subnodos de un nodo padre en el registro ENS. El primer usuario en registrar
un nombre lo obtiene.

Constructor: `FIFSRegistrar(ENSRegistry _registry, bytes32 _rootNode)`.

Funcion publica: `register(bytes32 label, address newOwner)` - registra un
subdominio bajo el TLD gestionado. Falla si el nombre ya pertenece a otra cuenta.

Se despliega una instancia para `usuarios.cfp`. Los usuarios se registran a si
mismos via MetaMask llamando a `register(keccak256("sunombre"), suDireccion)`.

#### `PublicResolver.sol`

Resolutor de registros ENS que implementa:
- `IAddrResolver`: `addr(bytes32 node)` / `setAddr(bytes32 node, address addr)`
- `ITextResolver`: `text(bytes32 node, string key)` / `setText(...)`
- `INameResolver`: `name(bytes32 node)` / `setName(bytes32 node, string name)`
- `supportsInterface(bytes4)` (EIP-165)

Constructor: `PublicResolver(ENSRegistry _registry)`.

Autorizacion: solo el dueno del nodo en el registry (o un operador aprobado)
puede modificar sus registros.

#### `ReverseRegistrar.sol`

Gestiona la resolucion inversa (direccion a nombre). Permite que cualquier
cuenta configure su nombre reverso en `addr.reverse`.

Constructor: `ReverseRegistrar(ENSRegistry _registry)`.

Funciones publicas:
- `setName(string name)`:configura la resolucion inversa de `msg.sender`
- `setDefaultResolver(address resolver)`:solo owner, establece el resolutor
por defecto para nuevos registros

#### `CFPGovernanceToken.sol`

Token ERC-20 con funcionalidad de compra y redencion contra ETH a precio fijo.
Extiende `ERC20` + `Ownable` de OpenZeppelin v5.

Constructor: `CFPGovernanceToken(uint256 _tokensPerEth)` - acuna 1M tokens
para el deployer.

Funciones publicas:
- `buy()`: payable, acuna `msg.value * tokensPerEth` tokens al sender
- `redeem(uint256 amount)`: quema tokens del sender y le devuelve
`amount / tokensPerEth` ETH
- `withdraw(address to)`: solo owner, retira el ETH acumulado en el contrato
- `tokensPerEth()`: view, devuelve la tasa de conversion

### Contratos modificados (vs TP 10)

#### `CFPFactory.sol`

El constructor ahora recibe la direccion del token ERC-20 como parametro
inmutable:

```solidity
constructor(CFPGovernanceToken _token)
```

`create()` y `createFor()` ahora reciben un tercer parametro `guaranteeAmount`:

```solidity
function create(bytes32 callId, uint256 timestamp, uint256 guaranteeAmount)
    public returns (CFP)
```

Nueva funcion view:
- `token() -> address`:devuelve la direccion del token ERC-20

El evento `CFPCreated` ahora incluye `guaranteeAmount` como cuarto argumento:
`CFPCreated(address creator, bytes32 callId, CFP cfp, uint256 guaranteeAmount)`.

#### `CFP.sol`

Constructor modificado:

```solidity
constructor(
    bytes32 callId_,
    uint256 closingTime_,
    uint256 guaranteeAmount_,
    IERC20 token_,
    address creator_
)
```

Nuevas variables de estado:
- `guaranteeAmount` (uint256 immutable): monto de garantia requerido (0 = sin garantia)
- `token` (IERC20 immutable): direccion del token ERC-20
- `finalized` (bool): indica si el creador finalizo el proceso
- `refundClaimed` (mapping): evita reembolsos duplicados
- `acceptedProposals` (bytes32[]): propuestas aceptadas por el creador al finalizar

Nuevas funciones:
- `registerProposalWithCollateral(bytes32 proposal)`: registra una propuesta
transfiriendo `guaranteeAmount` tokens del proponente al contrato via
`transferFrom`. Requiere approve previo del proponente.
- `finalize(bytes32[] calldata _acceptedProposals)`: solo el creador, marca el
llamado como finalizado y guarda la lista de propuestas aceptadas. Habilita
la devolucion de garantias para las no aceptadas.
- `claimRefund(bytes32 proposal)`: permite a un proponente recuperar su garantia
si su propuesta NO esta en `acceptedProposals`. Mecanismo pull.
- `isProposalAccepted(bytes32 proposal) -> bool`: view, verifica si una propuesta
esta en la lista de aceptadas.
- `guaranteeAmount() -> uint256`: view (autogenerado por immutable)
- `token() -> address`: view (autogenerado por immutable)
- `finalized() -> bool`: view (autogenerado por public)

## Arbol ENS

El sistema ENS se organiza asi:

```
cfp                     ← deployer (owner del CFPFactory)
├── usuarios.cfp        ← FIFSRegistrar (autoregistro de usuarios)
│   └── <nombre>.usuarios.cfp  ← registrado por el usuario via MetaMask
├── llamados.cfp        ← deployer (la API registra nombres de llamados)
│   └── <nombre>.llamados.cfp  ← registrado por la API al crear el llamado
└── addr.reverse        ← ReverseRegistrar
    └── <addr>.addr.reverse    ← configurado por el usuario via setName()
```

## Orden de despliegue

1. ENSRegistry
2. PublicResolver (toma direccion del registry)
3. ReverseRegistrar
4. Crear nodo `cfp` como subnodo de la raiz
5. Crear `reverse` y `addr.reverse`
6. FIFSRegistrar para `usuarios.cfp`
7. Asignar `usuarios.cfp` al FIFSRegistrar
8. Crear `llamados.cfp` (owner = deployer)
9. Configurar resolvers del arbol ENS
10. CFPGovernanceToken
11. CFPFactory (toma direccion del token)

El script `scripts/deploy.js` ejecuta estos pasos e imprime las variables
de entorno necesarias.

## Variables de entorno emitidas en despliegue

| Variable | Descripcion |
|----------|-------------|
| CFP_MNEMONIC | Mnemonico BIP39 del owner |
| CFP_FACTORY_ADDRESS | Direccion del CFPFactory |
| CFP_ADMIN_ADDRESS | Direccion de la cuenta administradora |
| CFP_ENS_REGISTRY | Direccion del ENSRegistry |
| CFP_ERC20_TOKEN | Direccion del CFPGovernanceToken |
| CFP_METAMASK_MNEMONIC | Mnemonico para importar en MetaMask |

## Tests

Ejecutar con `npx hardhat test` o `npm test`.

Total: 68 tests. Cubren inicializacion de CFP y CFPFactory, registro de
propuestas (registerProposal, registerProposalFor), cierre de convocatoria,
entrega de archivos post-cierre, gestion de creadores, autorizacion, y
verificacion de eventos.

Los tests de las funcionalidades nuevas (ENS, Token, Garantia) estan
pendientes de implementacion.

## Comandos

```bash
npm install
npm run compile
npm run deploy          # Despliega en localhost:8545
npm test               # Ejecuta tests
```

## Decisiones de diseño

Ver `docs/DECISIONES_DISENO.md` en la raiz del proyecto para la justificacion
completa de todas las decisiones.
