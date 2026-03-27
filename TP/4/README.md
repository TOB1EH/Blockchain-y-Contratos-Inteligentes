# Trabajo práctico 4

En la red de testeo de la BFA se encuentra desplegado un contrato en la dirección `0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2`. Dicho contrato provee funcionalidades de sello de tiempo, y provee una interface equivalente a la siguiente:

```solidity
struct Stamped {
    address signer;
    uint blockNumber;
}

function stamp(bytes32 hash) public;

function stampSigned(bytes32 hash, bytes signature) public;

function stamped(bytes32 hash) public returns (Stamped);
```

La interface está simplificada, pero responde a lo que puede verse externamente.

Su semántica es la siguiente:

* La función `stamp(bytes32 hash)`  es una transacción que recibe como argumento un *hash* de 256 bits y almacena, asociado con él, el emisor del mensaje y el número de bloque en el que se produjo la transacción. Si el *hash* ya ha sido registrado, produce un error y la transacción se revierte.
* La función `stampSigned(bytes32 hash, bytes signature)`  es una transacción que recibe como argumento un *hash* de 256 bits, y una firma de dicho hash, y almacena, asociado con hash, el firmante del mensaje y el número de bloque en el que se produjo la transacción. Si el *hash* ya ha sido registrado, produce un error y la transacción se revierte.
* La función `stamped(bytes32 hash)` es una llamada que recibe un *hash* de 256 bits, y devuelve la estructura `Stamped` asociada con ese hash. Si ese *hash* nunca ha sido registrado, devolverá una estructura con ambos valores con su valor *default*, es decir
`'0x0000000000000000000000000000000000000000'` para la dirección y `0` para el número de bloque.

La ABI y la dirección del contrato están definidas en el archivo [Stamper.json](Stamper.json). En dicho archivo se define un objeto con los siguientes campos:

* `contractName` define el nombre del contrato ("Stamper")
* `abi` contiene la ABI necesaria para interactuar con el contrato.
* `networks` contiene infomación del despliegue del contrato: Red, dirección y transacción de creación.

## Consigna

### Implementación de una API REST

Implementar una API REST que interactúe con el contrato y permita acceder a sus funcionalidades. En la API los *hashes*, direcciones y transacciones se expresarán como cadenas hexadecimales de la longitud adecuada y el prefijo "0x". Los valores enteros se expresarán como números decimales.
La API deberá trabajar con cuentas locales, es decir, debe poder interactuar con un nodo que no tiene definida ninguna cuenta. Se asume que hay al menos dos cuentas locales, con el formato de keystore de `geth`, y alojadas en el directorio `~/.ethereum/keystore`.

La cuenta utilizada para interactuar con el nodo ethereum debe ser la primera del *keystore* en orden lexicográfico (ello implica que es la más antigua). Esa cuenta poseerá `ether` suficiente como para realizar transacciones. Las otras cuentas pueden no tener `ether`.

El programa que implemente la API debe leer la primera cuenta del *keystore*, descifrar la clave privada y operar con ella. Para ello debe pedir la contraseña de descifrado al inicio de su ejecución, o recibir el nombre de un archivo con la contraseña como argumento de la línea de comandos.

Documente el trabajo realizado en un archivo README.md, en formato Markdown. La documentación debe proporcionar información sobre la forma de ejecutar el servidor de API.

La API debe proveer los siguientes *endpoints*:

#### `/stamped/:hash`

* Método: `GET`
* Argumento: `:hash` corresponde a un *hash* de 256 bits.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con dos campos: `signer` y `blockNumber`, correspondientes a la dirección que ha registrado el *hash* y al número de bloque correspondiente a dicha transacción.
* Retorno fallido:
  * Codigo HTTP:
    * Si el hash no ha sido registrado: `404 Not Found`
    * Si el argumento está mal formado: `400 Bad Request`
  * Cuerpo: Un objeto JSON con un campo `message` que contiene el mensaje de error.

#### `/stamp`

* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con un campo `hash`, que contiene el hash a registrar, y un campo opcional `signature`, que contiene una firma del hash. Si la firma está presente se llamará al método `stampSigned` del contrato, y si está ausente se invocará el método `stamp`. La firma es una firma ECDSA de Ethereum estándar: 65 bytes expresados como 130 caracteres hexadecimales con prefijo `0x`.
* Retorno exitoso:
  * Código HTTP: 201
  * Cuerpo: Un objeto JSON con dos campos: `transaction` y `blockNumber`, correspondientes a la transacción en la que se ha registrado el *hash* y al número de bloque correspondiente a dicha transacción.
* Retorno fallido:
  * Codigo HTTP:
    * Si el hash ya ha sido registrado: `403 Forbidden`
    * Si alguno de los argumentos está mal formado o el *content_type* del requerimiento no es `application/json`: `400 Bad Request`
  * Cuerpo: Un objeto JSON con un campo `message` que contiene el mensaje de error. Si el error se debe a que el hash ya estaba registrado, se deben incluir además los campos `signer` y `blockNumber` con los valores correspondientes.

La especificación completa de la API se encuentra en el archivo [openapi.yaml](openapi.yaml).

### Implementación de un programa que interactúe con la API REST

Implementar, o bien una aplicación web, o un programa de línea de comandos que interactúe con la API REST. Documente el trabajo realizado en un archivo README.md en formato Markdown. La documentación debe incluir las instrucciones necesarias para utilizar la solución implementada.

#### Aplicación Web

En el caso de implementarse una aplicación web, esta debe permitir subir archivos y dar al usuario la opción de verificar si el archivo ya ha sido registrado, y de registrarlo.

#### Programa de línea de comandos

En el caso de implementar un programa de línea de comandos, este debe admitir dos comandos, `verify` y `stamp`, y recibir una lista de nombres de archivos. El programa debe verificar o sellar el hash de los archivos proporcionados, según corresponda, e informar del resultado en la salida estándar.

## Resolución del práctico

Debemos desarrollar un servidor que se comunique por un lado con un usuario, mediante la API REST, y por otro lado, con un contrato ya desplegado.

La interacción con un contrato se realiza en última instancia mediante transacciones que tienen como destino la dirección del contrato, pero las distintas bibliotecas nos proporcionan métodos que simplifican esta tarea. Los ejemplos que siguen corresponden a la biblioteca `web3` de Python, pero pueden adaptarse a otros lenguajes.

### Interacción con un contrato utilizando Python con web3

Para interactuar con un contrato ya desplegado necesitamos dos elementos: su dirección y su ABI (*Application Binary Interface*), que define qué métodos provee el contrato, cuáles son sus argumentos y cuáles sus valores de retorno.

En este caso, ambos valores han sido provistos en el archivo `Stamper.json`. Una posible forma de construir un objeto que nos permita interactuar con el contrato es la siguiente:

```python
import json
with open('Stamper.json') as f:
    config = json.load(f)
contract = w3.eth.contract(abi = config['abi'], address = config["networks"]["55555000000"]["address"])
```

El objeto `contract` nos brinda una serie de métodos que nos permiten interactuar con el contrato. Debemos recordar que tenemos dos formas de interactuar con un contrato:

* Mediante *llamadas*, con las cuales hacemos consultas que no modifican el estado del contrato, no consumen gas y no tienen costo.
* Mediante *transacciones*, que modifican el estado del contrato, consumen gas y tienen un costo en ether que es pagado por quien invoca la transacción.

En el contrato `Stamper`, el método `stamped()` se invoca mediante una llamada, ya que simplemente nos indica si un determinado hash ha sido registrado en el contrato. Veamos un ejemplo:

```python
already_stamped = '0x836a97e0ff6a85dd2746a39ed71171595759c02beda2d45d0280e0cd19ba3c34'
contract.functions.stamped(already_stamped).call()
# ['0xe694177c2576f6644Cbd0b24bE32a323f88A08D5', 10297664]
```

La respuesta nos indica que ese hash ha sido registrado desde la dirección `0xe694177c2576f6644Cbd0b24bE32a323f88A08D5` en el bloque 10297664.

Por otra parte, el método `stamp()` es una transacción, y requiere ser invocado desde una cuenta con ether. Una forma de hacerlo es utilizando cuentas alojadas en el nodo:

```python
new_hash = '0x' + os.urandom(32).hex()
contract.functions.stamp(new_hash).transact()
# ValueError: {'code': -32000, 'message': 'unknown account'}
```

Necesitamos indicar una cuenta:

```python
new_hash = '0x' + os.urandom(32).hex()
contract.functions.stamp(new_hash).transact({'from': w3.eth.accounts[0]})
```

Otra forma de hacerlo es con claves privadas locales, firmando transacciones y enviando transacciones firmadas. Ese es el mecanismo que utilizaremos. En este caso tenemos dos opciones, armar la transacción, firmarla y enviarla con `send_raw_transaction()`, o utilizar _middleware_ de firmado y `transact()`.

#### Procedimiento A: armar la transacción, firmarla y enviarla con `send_raw_transaction`

Podemos utilizar el método `build_transaction()` para construir la transacción.

```python
gas = contract.functions.stamp(new_hash).estimate_gas({'from': account.address})
transaction = contract.functions.stamp(new_hash).build_transaction({
    'gas': 100000,
    'gasPrice': w3.eth.gas_price,
    'nonce': w3.eth.get_transaction_count(account.address),
    'chainId': w3.eth.chain_id
})
signed_transaction = w3.eth.account.sign_transaction(transaction, private_key = private_key)
w3.eth.send_raw_transaction(signed_transaction.raw_transaction)
```

Un inconveniente que tiene este mecanismo es que no sabemos de inmediato si la transacción se revirtió debido a un error. Podemos saber si la transacción fue exitosa analizando el recibo. Supongamos que repetimos la transacción que mostramos más arriba. La transacción debería fallar, ya que el hash ya ha sido registrado.

```python
transaction = contract.functions.stamp(new_hash).build_transaction({
    'gasPrice': w3.eth.gas_price,
    'nonce': w3.eth.get_transaction_count(account),
    'chainId': w3.eth.chain_id
})
signed_transaction = w3.eth.account.sign_transaction(transaction, private_key = private_key)
txh = w3.eth.send_raw_transaction(signed_transaction.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(txh)
```

El contenido del recibo será algo similar a lo siguiente:

```python
AttributeDict({'blockHash': HexBytes('0xadd313d4ed887548c4116cd0c3d6175ff54c663da75314ef4e64d1e8b8aa1509'),
 'blockNumber': 19917226,
 'contractAddress': None,
 'cumulativeGasUsed': 64479,
 'effectiveGasPrice': 1000000000,
 'from': '0xf555994877943ca34B6E1218751BCC53837ecA6D',
 'gasUsed': 64479,
 'logs': [],
 'logsBloom': HexBytes('0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000'),
 'status': 0,
 'to': '0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2',
 'transactionHash': HexBytes('0x4d2d0d5711a347740aa769840b3a623cad1323476600cbea5d318749b7525cba'),
 'transactionIndex': 0,
 'type': 0})
```

 El valor 0 en `status` nos indica que la transacción ha fracasado. Pero no sabemos la causa. Para averiguar la causa, debemos invocar nuevamente la transacción con un `call()`.

 Podemos obtener la transacción a partir de su hash:

 ```python
 tx = w3.eth.get_transaction(txh)
 ```

 El resultado será algo así:

 ```python
 AttributeDict({'blockHash': HexBytes('0xadd313d4ed887548c4116cd0c3d6175ff54c663da75314ef4e64d1e8b8aa1509'),
 'blockNumber': 19917226,
 'from': '0xf555994877943ca34B6E1218751BCC53837ecA6D',
 'gas': 100000,
 'gasPrice': 1000000000,
 'hash': HexBytes('0x4d2d0d5711a347740aa769840b3a623cad1323476600cbea5d318749b7525cba'),
 'input': '0xdd89581f51e2298647465d30b801b1a4f245ed255b9070e6c995a3419cf098783be8d878',
 'nonce': 8,
 'to': '0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2',
 'transactionIndex': 0,
 'value': 0,
 'type': 0,
 'v': 198237680,
 'r': HexBytes('0xbe7ce6068024e0c4ecde2e92b8b869ed2ab6b75be7aadb1cbd96f0a4c1821541'),
 's': HexBytes('0x040ad9d720d11eb7e339cd18ec3d38ae97d3d6d017690fe427f96b028ca09a77')})
```

Así, podemos ejecutar:

```python
w3.eth.call(tx)
```

Esta llamada fracasará con el mismo error que la transacción original:

```console
ContractLogicError: execution reverted: The hash is already stamped
```

#### Procedimiento B: utilizar _middleware_ de firmado y `transact()`

En este caso el procedimiento es más simple

```python
from web3.middleware import SignAndSendRawMiddlewareBuilder
w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(account), layer = 0)
new_hash = os.urandom(32)
tx_hash = contract.functions.stamp(new_hash).transact({'from': account.address, 'gasPrice': w3.eth.gas_price})
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
```

En este caso, si la transacción revierte se lanzará una excepción que puede ser capturada y manejada. No necesitamos realizar un `call()` para averiguar la razón del fallo.

### Interacción con un contrato utilizando Javascript con ethers

La biblioteca `ethers` de JavaScript proporciona una forma similar de interactuar con contratos ya desplegados. También necesitamos dos elementos: la dirección del contrato y su ABI, que se encuentran en el archivo `Stamper.json`.

Una posible forma de construir un objeto que nos permita interactuar con el contrato es:

```javascript
const fs = require("node:fs");
const { ethers } = require("ethers");

const provider = new ethers.JsonRpcProvider("http://localhost:8545")
const config = JSON.parse(fs.readFileSync("Stamper.json", "utf8"));
const contractAddress = config.networks["55555000000"].address;
const contractAbi = config.abi;

const contract = new ethers.Contract(contractAddress, contractAbi, provider);
```

Donde `provider` es una instancia de `ethers.JsonRpcProvider` o `ethers.IpcSocketProvider` conectada a un nodo Ethereum. En este ejemplo nos estamos conectando via http a un nodo local.

El objeto `contract` nos brinda métodos que nos permiten interactuar con el contrato. Similarmente a Python, tenemos dos formas de interactuar:

* Mediante *llamadas* (read-only), que no modifican el estado del contrato, no consumen gas y no tienen costo.
* Mediante *transacciones*, que modifican el estado del contrato, consumen gas y tienen un costo en ether.

En el contrato `Stamper`, el método `stamped()` se invoca mediante una llamada:

```javascript
const alreadyStamped = "0x836a97e0ff6a85dd2746a39ed71171595759c02beda2d45d0280e0cd19ba3c34";
const result = await contract.stamped(alreadyStamped);
// Acceso por índice: result[0], result[1]
// Acceso por propiedad: result.signer, result.blockNumber
```

La respuesta es un Proxy que permite acceder a los campos de la estructura `Stamped` de dos formas equivalentes:

* Por índice: `result[0]` (signer), `result[1]` (blockNumber)
* Por propiedad: `result.signer`, `result.blockNumber`

En ethers v6, los números grandes se representan como `BigInt` (sufijo `n` en el literal).

Por otra parte, el método `stamp()` es una transacción. Para invocar transacciones con una clave privada local, necesitamos crear un objeto `Wallet` y luego comunicarlo al contrato:

```javascript
const privateKey = "0x..."; // clave privada hexadecimal
const wallet = new ethers.Wallet(privateKey, provider);
const contractWithSigner = contract.connect(wallet);

const newHash = ethers.randomBytes(32);
const tx = await contractWithSigner.stamp(newHash);
const receipt = await tx.wait();
```

El método `wait()` espera confirmación de la transacción y devuelve el recibo. Un recibo de ethers tiene una estructura como la siguiente:

```javascript
ContractTransactionReceipt {
  provider: JsonRpcProvider {},
  to: '0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2',
  from: '0xf555994877943ca34B6E1218751BCC53837ecA6D',
  contractAddress: null,
  hash: '0xf44402bd4c3f9948a128ed9df404bfe7c4699ac3a2d0fa270ea846eb26cab480',
  index: 0,
  blockHash: '0x64d8543cc83d4b1c7cc5b99c8343ba15a3780088e90939388d7ddf116241e9bd',
  blockNumber: 37386035,
  logsBloom: '0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
  gasUsed: 64479n,
  blobGasUsed: null,
  cumulativeGasUsed: 64479n,
  gasPrice: 1000000000n,
  blobGasPrice: null,
  type: 0,
  status: 1,
  root: undefined
}
```

Si la transacción revierte, `ethers` lanza una excepción con el mensaje de error del contrato:

```javascript
try {
  const tx = await contractWithSigner.stamp(alreadyStamped);
  const receipt = await tx.wait();
} catch (error) {
  if (error.reason) {
    console.error(error.reason); // "The hash is already stamped"
  }
}
```

Para firmar una transacción manualmente y enviar su versión firmada, el proceso es similar al de Python:

```javascript
const newHash = ethers.randomBytes(32);

// Construir la transacción
const tx = await contractWithSigner.stamp.populateTransaction(newHash);

// Agregar gas, nonce, chainId y type
tx.gasPrice = await provider.getFeeData().then(d => d.gasPrice);
tx.nonce = await provider.getTransactionCount(wallet.address);
tx.chainId = (await provider.getNetwork()).chainId;
tx.gasLimit = await wallet.estimateGas(tx);
tx.type = 0;

// Firmar
const signedTx = await wallet.signTransaction(tx);

// Enviar
const txResponse = await provider.broadcastTransaction(signedTx);
const receipt = await txResponse.wait();
```

A diferencia de la biblioteca `web3` de Python, si la transacción revierte, se producirá un error en la obtención del recibo:

```javascript
receipt = await txResponse.wait()
Uncaught:
Error: transaction execution reverted (action="sendTransaction", data=null, reason=null, invocation=null, revert=null, transaction={ "data": "", "from": "0xf555994877943ca34B6E1218751BCC53837ecA6D", "to": "0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2" }, receipt={ "_type": "TransactionReceipt", "blobGasPrice": null, "blobGasUsed": null, "blockHash": "0x21d76c78a5abfb1d8e0e6ba0a1cfc5a6f953d968ccd7f2aaf6575da2c8844315", "blockNumber": 37386716, "contractAddress": null, "cumulativeGasUsed": "24079", "from": "0xf555994877943ca34B6E1218751BCC53837ecA6D", "gasPrice": "1000000000", "gasUsed": "24079", "hash": "0x54987afb2ca04506382cf03b55494744be73838db261a99f4d147926ce3975e3", "index": 0, "logs": [  ], "logsBloom": "0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000", "root": null, "status": 0, "to": "0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2" }, code=CALL_EXCEPTION, version=6.16.0)
    at makeError (/Users/miguel/repos/bitbucket.org/blockchain-iua/blockchain/TP/4/node_modules/ethers/lib.commonjs/utils/errors.js:137:21)
    at assert (/Users/miguel/repos/bitbucket.org/blockchain-iua/blockchain/TP/4/node_modules/ethers/lib.commonjs/utils/errors.js:157:15)
    at checkReceipt (/Users/miguel/repos/bitbucket.org/blockchain-iua/blockchain/TP/4/node_modules/ethers/lib.commonjs/providers/provider.js:1138:35)
    at TransactionResponse.wait (/Users/miguel/repos/bitbucket.org/blockchain-iua/blockchain/TP/4/node_modules/ethers/lib.commonjs/providers/provider.js:1154:24)
    at process.processTicksAndRejections (node:internal/process/task_queues:105:5)
    at async REPL517:1:43 {
  code: 'CALL_EXCEPTION',
  action: 'sendTransaction',
  data: null,
  reason: null,
  invocation: null,
  revert: null,
  transaction: {
    to: '0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2',
    from: '0xf555994877943ca34B6E1218751BCC53837ecA6D',
    data: ''
  },
  receipt: TransactionReceipt {
    provider: JsonRpcProvider {},
    to: '0xA2e82b0666a291c53F374E34A6C09fBA873aB0f2',
    from: '0xf555994877943ca34B6E1218751BCC53837ecA6D',
    contractAddress: null,
    hash: '0x54987afb2ca04506382cf03b55494744be73838db261a99f4d147926ce3975e3',
    index: 0,
    blockHash: '0x21d76c78a5abfb1d8e0e6ba0a1cfc5a6f953d968ccd7f2aaf6575da2c8844315',
    blockNumber: 37386716,
    logsBloom: '0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
    gasUsed: 24079n,
    blobGasUsed: null,
    cumulativeGasUsed: 24079n,
    gasPrice: 1000000000n,
    blobGasPrice: null,
    type: 0,
    status: 0,
    root: undefined
  },
  shortMessage: 'transaction execution reverted'
}
```
