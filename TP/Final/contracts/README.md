# Trabajo Práctico 10 - Smart contracts

El trabajo consiste en implementar dos contratos. El contrato `CFP` implementa un llamado a presentación de propuestas (*Call For Proposals*). Una propuesta está representada por el *hash* de un documento, que es registrada en el contrato antes de la fecha de cierre del llamado.

El contrato `CFPFactory` implementa una factoría que crea instancias del contrato `CFP`.

A los efectos de poder probar este práctico, deberán prever un mecanismo de despliegue en un nodo local (desplegado por ejemplo con `npx hardhat node`). El mecanismo de despliegue puede ser mediante `ignition` o un script *ad hoc*.

## Contratos

### `CFP`

#### Tipos de datos

La estructura `ProposalData` representa una propuesta, y almacena la dirección del autor de la propuesta (`sender`), el número de bloque y el `timestamp` en el que la propuesta fue registrada.

```solidity
struct ProposalData {
    address sender;
    uint blockNumber;
    uint timestamp;
}
```

#### Eventos

El evento `ProposalRegistered` se emite al momento de registrarse una propuesta.

```solidity
event ProposalRegistered(bytes32 proposal, address sender, uint blockNumber);
```

#### Constructor

El constructor recibe dos argumentos: un identificador del llamado, del tipo `bytes32`, y un `timestamp` de tipo `uint` que establece el tiempo de cierre de la convocatoria. Si ese timestamp es menor o igual al del bloque actual, la acción se revierte con el mensaje "El cierre de la convocatoria no puede estar en el pasado".

#### Funciones informativas

Las funciones especificadas a continuación pueden implementarse en forma explícita, o como consecuencia de la definición de una variable de estado pública con el nombre adecuado.

##### `proposalData(bytes32 proposal)`

* Devuelve una estructura de tipo `ProposalData`, asociada con la propuesta `proposal`.

##### `proposalCount()`

* Devuelve la cantidad de propuestas presentadas.

##### `proposals(uint index)`

* Devuelve la propuesta que está en la posición `index` de la lista.

##### `closingTime()`

* Devuelve el `timestamp` correspondiente al cierre del llamado.

##### `callId()`

* Devuelve el identificador de este llamado.

##### `creator()`

* Devuelve la dirección del creador de este contrato.

##### `proposalTimestamp(bytes32 proposal)`

* Devuelve el `timestamp` en el que se ha registrado una propuesta. Si la propuesta no está registrada devuelve cero.

#### Transacciones

##### `registerProposal(bytes32 proposal)`

* Permite registrar una propuesta, expresada como un argumento de tipo `bytes32`.
* Registra al emisor del mensaje como emisor de la propuesta.
* Si el timestamp del bloque actual es mayor que el del cierre del llamado, revierte con el error "Convocatoria cerrada".
* Si ya se ha registrado una propuesta igual, revierte con el mensaje "La propuesta ya ha sido registrada".
* Emite el evento `ProposalRegistered`.

##### `registerProposalFor(bytes32 proposal, address sender)`

* Permite registrar una propuesta especificando un emisor.
* Sólo puede ser ejecutada por el creador del llamado. Si no es así, revierte con el mensaje "Solo el creador puede hacer esta llamada".
* Si el timestamp del bloque actual es mayor que el del cierre del llamado, revierte con el error "Convocatoria cerrada".
* Si ya se ha registrado una propuesta igual, revierte con el mensaje "La propuesta ya ha sido registrada"
* Emite el evento `ProposalRegistered`

#### Errores

##### `La propuesta ya ha sido registrada`

Ocurre cuando se intenta registrar una propuesta que ha sido registrada previamente.

##### `El cierre de la convocatoria no puede estar en el pasado`

Ocurre cuando se intenta crear un llamado con fecha de cierre igual o anterior al `timestamp` del bloque actual.

##### `Convocatoria cerrada`

Ocurre cuando se intenta registrar una propuesta luego del cierre de la convocatoria.

##### `Solo el creador puede hacer esta llamada`

Ocurre cuando alguien que no es el creador de la llamada intenta ejecutar una función reservada para el creador.

### `CFPFactory`

#### Tipos de datos

La estructura `CallForProposals` representa un llamado, y almacena la dirección del creador y la dirección del nuevo contrato creado.

```solidity
struct CallForProposals {
    address creator;
    CFP cfp;
}
```

#### Eventos

El evento `CFPCreated` se emite cuando se crea un nuevo contrato.

```solidity
event CFPCreated(address creator, bytes32 callId, CFP cfp);
```

El evento `CreatorRegistered` se emite cuando una cuenta se registra mediante `register()`.

```solidity
event CreatorRegistered(address indexed creator);
```

El evento `CreatorAuthorized` se emite cuando el dueño autoriza a una cuenta mediante `authorize()`.

```solidity
event CreatorAuthorized(address indexed creator);
```

El evento `CreatorUnauthorized` se emite cuando el dueño revoca la autorización de una cuenta mediante `unauthorize()`.

```solidity
event CreatorUnauthorized(address indexed creator);
```

#### Constructor

El constructor no recibe argumentos y simplemente registra al emisor como dueño de la factoría.

#### Funciones informativas

##### `owner()`

* Devuelve la dirección del dueño de la factoría

##### `calls(bytes32 callId)`

* Devuelve una estructura de tipo `CallForProposals` con la información asociada con el argumento `callId`.

##### `creatorsCount()`

* Devuelve la cantidad de cuentas que han creado llamados.

##### `creators(uint index)`

* Devuelve la dirección del creador en la posición `index`.

##### `createdByCount(address creator)`

* Devuelve la cantidad de contratos creados por un cierto creador.

##### `createdBy(address creator, uint index)`

* Devuelve el identificador del contrato que se encuentra en la posición `index` de la lista de contratos creados por `creator`.

##### `pendingCount()`

* Devuelve la cantidad de cuentas que se han registrado para crear llamados y que no han sido autorizadas o desautorizadas aún.
* Sólo puede ser invocada por el dueño de la factoría.
* Si es ejecutada por otro usuario, revierte con el mensaje "Solo el creador puede hacer esta llamada"

##### `getPending(uint index)`

* Devuelve la dirección que está en la posición `index` de la lista de pendientes de autorización.
* Sólo puede ser invocada por el dueño de la factoría.
* Si es ejecutada por otro usuario, revierte con el mensaje "Solo el creador puede hacer esta llamada"

##### `getAllPending()`

* Devuelve la lista de todas las direcciones pendientes de autorización.
* Sólo puede ser invocada por el dueño de la factoría.
* Si es ejecutada por otro usuario, revierte con el mensaje "Solo el creador puede hacer esta llamada"

##### `isRegistered(address account)`

* Devuelve verdadero si la cuenta provista como argumento está actualmente pendiente de autorización o ya fue autorizada. Devuelve `false` para cuentas que nunca se han registrado o que han sido desautorizadas (la desautorización elimina completamente el estado de registro en el contrato).

##### `isAuthorized(address account)`

* Devuelve verdadero si la cuenta provista como argumento está autorizada para crear llamados.

#### Transacciones

##### `create(bytes32 callId, uint timestamp) public returns (CFP)`

* Crea un llamado, con un identificador y un tiempo de cierre.
* Si ya existe un llamado con ese identificador, revierte con el mensaje de error "El llamado ya existe".
* Si el emisor no está autorizado a crear llamados, revierte con el mensaje "No autorizado".
* Emite el evento `CFPCreated`.

##### `createFor(bytes32 callId, uint timestamp, address creator) public returns (CFP)`

* Crea un llamado, estableciendo a `creator` como creador del mismo.
* Sólo puede ser invocada por el dueño de la factoría.
* En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
* Se comporta en todos los demás aspectos como `create(bytes32 callId, uint timestamp)`, incluyendo la emisión del evento `CFPCreated`.

##### `register()`

* Permite que una cuenta se registre para poder crear llamados.
* El registro queda en estado pendiente hasta que el dueño de la factoría lo autorice.
* Si ya se ha registrado, revierte con el mensaje "Ya se ha registrado".
* Emite el evento `CreatorRegistered`.

##### `registerProposal(bytes32 callId, bytes32 proposal)`

* Permite a un usuario registrar una propuesta, para un llamado con identificador `callId`.
* Si el llamado no existe, revierte con el mensaje  "El llamado no existe".
* Registra la propuesta en el llamado asociado con `callId` y pasa como creador la dirección del emisor del mensaje.

##### `authorize(address creator)`

* Autoriza a una cuenta a crear llamados.
* Sólo puede ser ejecutada por el dueño de la factoría.
* En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
* Si la cuenta se ha registrado y está pendiente, la quita de la lista de pendientes.
* Emite el evento `CreatorAuthorized`.
* Emite el evento `CreatorAuthorized`

##### `unauthorize(address creator)`

* Quita la autorización de una cuenta para crear llamados.
* Sólo puede ser ejecutada por el dueño de la factoría.
* En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
* Elimina completamente el estado de registro de la cuenta: tras la desautorización, tanto `isRegistered(creator)` como `isAuthorized(creator)` devuelven `false`.
* Si la cuenta se ha registrado y está pendiente, la quita de la lista de pendientes.
* Para volver a crear llamados, la cuenta debe registrarse nuevamente mediante `register()`.
* Emite el evento `CreatorUnauthorized`.

#### Errores

##### `Solo el creador puede hacer esta llamada`

Ocurre cuando alguien que no es el creador de la llamada intenta ejecutar una función reservada para el creador.

##### `El llamado ya existe`

Ocurre cuando se intenta crear un llamado con el mismo `callId` que uno existente.

##### `El llamado no existe`

Ocurre cuando se intenta registrar una propuesta asociada con un `callId` inexistente.

##### `No autorizado`

Ocurre cuando una cuenta no autorizada intenta crear un llamado.

##### `Ya se ha registrado`

Ocurre cuando una cuenta registrada intenta registrarse nuevamente.

## Diferencias con el Práctico 7

El contrato `CFPFactory` incorpora tres eventos que no estaban presentes en el Práctico 7:

* `CreatorRegistered(address indexed creator)`: se emite cuando una cuenta llama a `register()` para solicitar autorización.
* `CreatorAuthorized(address indexed creator)`: se emite cuando el dueño de la factoría autoriza a una cuenta mediante `authorize()`.
* `CreatorUnauthorized(address indexed creator)`: se emite cuando el dueño de la factoría revoca la autorización de una cuenta mediante `unauthorize()`.

## Diferencias con el Práctico 9

Para el Práctico 10 se agregaron al contrato `CFP` los siguientes elementos para soportar la entrega de archivos post-cierre.

### `DeliveryData` (nuevo struct)

Estructura que representa la entrega de archivos asociada a una propuesta:

```solidity
struct DeliveryData {
    bytes32 filesRoot;      // raíz del árbol de Merkle de los archivos entregados
    address sender;          // dirección del emisor de la entrega
    uint256 blockNumber;     // bloque en el que se registró la entrega
    uint256 timestamp;       // timestamp del registro
    bool delivered;          // bandera que indica si la entrega fue realizada
}
```

### `FilesDelivered` (nuevo evento)

Se emite cuando se registra exitosamente una entrega de archivos:

```solidity
event FilesDelivered(bytes32 indexed proposalId, bytes32 filesRoot, address sender, uint256 timestamp);
```

### `registerDelivery(bytes32 proposalId, bytes32 filesRoot)` (nuevo método público)

Permite registrar en cadena la entrega final de archivos posterior al cierre del llamado.

Restricciones:

* La convocatoria debe haber cerrado (`block.timestamp > _closingTime`). Si no, revierte con "La convocatoria no ha cerrado".
* La propuesta debe existir en el contrato (`proposalData[proposalId].blockNumber != 0`). Si no, revierte con "La propuesta no existe".
* La entrega no debe haberse registrado previamente (`!_deliveries[proposalId].delivered`). Si ya existe, revierte con "La entrega ya fue registrada".

Emite el evento `FilesDelivered`.

### `deliveryData(bytes32 proposalId)` (nueva función view)

Devuelve la estructura `DeliveryData` asociada a la propuesta. Si la propuesta no tiene entrega registrada, devuelve `DeliveryData` con `delivered == false`.

### Decisiones de diseño

* La estructura `DeliveryData` incluye un campo `filesRoot` (raíz Merkle) para que el servidor pueda verificar la integridad de los archivos entregados contra el compromiso original.
* El sender de la entrega puede ser distinto del sender de la propuesta original (caso de entrega delegada por la API).
* La bandera `delivered` permite distinguir entre una propuesta sin entrega (`delivered == false`) y una propuesta con entrega registrada. Sin esta bandera, un struct con todos sus campos en cero sería ambiguo.
* Se usa `block.timestamp` en lugar de recibir un timestamp externo para garantizar integridad temporal on-chain.

### Casos de prueba agregados (6 tests en `test/testCFP.js`)

Los nuevos tests están en el bloque `"Entrega de archivos post-cierre"` dentro de `testCFP.js`:

| Test | Descripción |
|------|-------------|
| `debe permitir registrar una entrega después del cierre` | Registra una propuesta, avanza el tiempo, llama a `registerDelivery` y verifica los campos de `DeliveryData` |
| `debe emitir el evento FilesDelivered al registrar una entrega` | Verifica que el evento se emita con los argumentos correctos (proposalId, filesRoot, sender, timestamp) |
| `debe rechazar la entrega si la convocatoria no ha cerrado` | Intenta registrar entrega antes del cierre; espera revert con "La convocatoria no ha cerrado" |
| `debe rechazar la entrega si la propuesta no existe` | Intenta registrar entrega para un proposalId inexistente; espera revert con "La propuesta no existe" |
| `debe rechazar la entrega duplicada` | Registra entrega dos veces para la misma propuesta; espera revert con "La entrega ya fue registrada" |
| `debe devolver datos vacíos para una propuesta sin entrega` | Consulta `deliveryData()` para una propuesta sin entrega y verifica `delivered == false` y `blockNumber == 0` |

Total: **79 tests** (48 de CFPFactory + 31 de CFP).

### Script de despliegue (`scripts/deploy.js`)

Cambios respecto al TP9:

* **Exporta `deployments/CFPFactory.json`**: al desplegar, genera un archivo JSON con `address`, `chainId` y `abi` del contrato. La API y el frontend pueden leer este archivo para evitar direcciones hardcodeadas.
* **Deriva la cuenta administradora**: imprime la dirección de la cuenta 0 (`m/44'/60'/0'/0/0`) de `CFP_METAMASK_MNEMONIC` como `CFP_ADMIN_ADDRESS`. Esta cuenta es distinta del owner on-chain y se usa para firmar operaciones administrativas desde MetaMask.
* **Salida lista para exportar**: imprime los tres exports listos para copiar y pegar en la terminal de la API: `CFP_MNEMONIC`, `CFP_FACTORY_ADDRESS`, `CFP_ADMIN_ADDRESS`.

### Paquetes y comandos

Sin cambios respecto al TP9. Los comandos de compilación y tests son los mismos:
