# Uso de claves privadas locales y firma de transacciones

Cuando trabajamos en la consola de `geth`, podemos enviar ether de una cuenta a otra con el método `eth.sendTransaction()`:

```js
> eth.sendTransaction({from: eth.accounts[0], to: eth.accounts[1], value: 1})
"0xc30ae3650b64877a6df01ca84471814bd39736a549635077faa6c067e91d4456"
```

En este ejemplo estamos transfiriendo entre dos cuentas *alojadas en el nodo*. Las correspondientes claves privadas están en el *keystore*.

La cuenta de destino puede no estar en el nodo, pero la de origen debe estar disponible:

```js
> eth.sendTransaction({from: eth.accounts[0], to: "0xb3a34d94be07edb67454dcfe767881a686f8b5f7", value: web3.toWei(1,"ether")})
"0xdb3cb65b7235e66585b365dee34c7aefaaf64bde4f8e42b4dc33b12b565b20f2"
> eth.getBalance("b3a34d94be07edb67454dcfe767881a686f8b5f7")
1000000000000000000
> eth.sendTransaction({from: "0xb3a34d94be07edb67454dcfe767881a686f8b5f7", to: eth.accounts[1], value: web3.toWei(1,"ether")})
Error: unknown account
    at web3.js:6365:9(39)
    at send (web3.js:5099:62(29))
    at <eval>:1:20(16)
```

Además, antes de poder utilizarla es necesario hacer un *unlock* de la cuenta:

```js
> eth.getBalance(eth.accounts[2])
999978999000000000
> eth.sendTransaction({from: eth.accounts[2], to: eth.accounts[0], value: 1000})
Error: authentication needed: password or unlock
    at web3.js:6365:9(39)
    at send (web3.js:5099:62(29))
    at <eval>:1:20(15)
> personal.unlockAccount(eth.accounts[2])
Unlock account 0x56e62e963b329bf10d5b4e9da8cc70d02c834aa5
Passphrase: 
true
> eth.sendTransaction({from: eth.accounts[2], to: eth.accounts[0], value: 1000})
"0xcc5fabe9cc6661ca26100f06e5d7bea2b3b024c5f4acb491676544ebab73af84"
```

Este procedimiento puede ser adecuado si tenemos un nodo local, completamente bajo nuestro control. Pero si utilizamos un nodo controlado por alguien más, no es factible, ya que si colocamos nuestras claves en el nodo, quien lo controla tiene también control sobre nuestras claves.

En ese caso, debemos trabajar con *claves privadas locales*. Las claves no están en el nodo, sino en nuestro poder, y las utilizamos para firmar transacciones, las cuales son enviadas posteriormente a un nodo.

Firmar localmente significa que la clave privada nunca sale de nuestra máquina, aunque el nodo sea de terceros.

Los pasos son:

1. Contar con la clave privada
2. Construir una transacción
3. Firmar la transacción con nuestra clave privada
4. Enviar la transacción

## Python con web3.py

### Extracción de la clave privada de un archivo de geth con `web3`

Existen distintas formas de crear y almacenar una clave privada, pero veremos la forma de obtener, desde Python con `web3`, la clave privada almacenada en un archivo creado por `geth account new`.

```python
filename = 'UTC--...a45f2e9' # Archivo generado por `geth account new`
password = '...'
with open(filename) as f:
    encrypted_key = f.read()
private_key = w3.eth.account.decrypt(encrypted_key, password)
```

### Procedimiento A: construir, firmar y enviar con `send_raw_transaction`

Cuando usamos `eth.sendTransaction()` en la consola, le pasamos como argumento un objeto que tiene sólo tres campos: `from`, `to` y `value`, y el método provee los valores restantes. Sin embargo, cuando armamos una transacción para firmar localmente, debemos proveer todos los valores necesarios:

* `from`: La cuenta de origen
* `to`: La cuenta de destino
* `value`: El monto que queremos transferir
* `gas`: La cantidad de gas que estamos dispuestos a gastar. Si la transacción es simplemente una transferencia de ether, 21000 es un valor adecuado. Es posible calcular el gas necesario con `w3.eth.estimate_gas`, pasando la transacción como argumento.
* `gasPrice`: El precio que estamos dispuestos a pagar por el gas. Como este es un valor dinámico, existen distintas estrategias posibles para calcularlo. Una estrategia posible es preguntarle al nodo (`w3.eth.gas_price`).
* `nonce`: El nonce evita que una transacción se replique o procese dos veces. Es simplemente el número total de transacciones ya enviadas desde una cuenta. Podemos obtenerlo con `w3.eth.get_transaction_count(address)`.
* `chainId`: Este valor se requiere para que no se pueda reutilizar la transacción firmada en una cadena distinta. Podemos obtenerlo con `w3.eth.chain_id`.

Construimos la transacción:

```python
transaction = {
    'from': address,
    'to': to,
    'value': amount,
    'gasPrice': w3.eth.gas_price,
    'nonce': w3.eth.get_transaction_count(address),
    'chainId': w3.eth.chain_id
}
transaction['gas'] = w3.eth.estimate_gas(transaction)
```

La firmamos:

```python
signed = w3.eth.account.sign_transaction(transaction, private_key=private_key)
```

Y la enviamos:

```python
tx = w3.eth.send_raw_transaction(signed.raw_transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx)
if receipt['status']:
    print(f'Transacción confirmada en el bloque {receipt.get("blockNumber")}')
else:
    print('Transferencia fallida', file=stderr)
```

### Procedimiento B: middleware de firmado y `send_transaction`

`web3.py` también permite registrar un middleware que firma automáticamente las transacciones de una cuenta local. De este modo, podemos usar `send_transaction()` de la misma forma que lo haríamos con una cuenta alojada en el nodo, pero sin exponer la clave privada al nodo.

```python
from eth_account import Account
from web3.middleware import SignAndSendRawMiddlewareBuilder

acct = Account.from_key(private_key)
w3.middleware_onion.inject(SignAndSendRawMiddlewareBuilder.build(acct), layer=0)

transaction = {
    'from': acct.address,
    'to': to,
    'value': amount,
    'gasPrice': w3.eth.gas_price,
    'nonce': w3.eth.get_transaction_count(acct.address),
    'chainId': w3.eth.chain_id
}
transaction['gas'] = w3.eth.estimate_gas(transaction)

tx = w3.eth.send_transaction(transaction)
receipt = w3.eth.wait_for_transaction_receipt(tx)
```

El middleware intercepta la llamada a `send_transaction`, firma la transacción localmente con la clave privada de `acct`, y la envía al nodo ya firmada, de forma transparente.

En versiones anteriores de `web3.py` el middleware equivalente se conoce como `construct_sign_and_send_raw_middleware`.

## JavaScript con ethers

En `ethers`, el firmado local es el flujo natural de la biblioteca: se crea un `Wallet` con la clave privada, se lo conecta a un `provider`, y a partir de ahí todas las transacciones se firman localmente antes de enviarse al nodo.

### Extracción de la clave privada de un archivo de geth con `ethers`

Si tenemos un archivo keystore JSON generado por `geth account new`:

```javascript
const { ethers } = require("ethers");
const fs = require("node:fs/promises");

const encryptedJson = await fs.readFile("UTC--...a45f2e9", "utf8");
const wallet = await ethers.Wallet.fromEncryptedJson(encryptedJson, password);
```

### Procedimiento A: construir, firmar y enviar con `broadcastTransaction`

Equivalente al procedimiento A de Python: construimos los campos de la transacción, la firmamos explícitamente y la enviamos como transacción raw.

```javascript
const provider = new ethers.JsonRpcProvider("http://localhost:8545");
const signer = wallet.connect(provider);

const feeData = await provider.getFeeData();
const network = await provider.getNetwork();


const tx = {
    from: signer.address,
    to: "0x...", // Dirección a la cual queremos enviar
    value: ethers.parseEther("1.0"),
    gasPrice: feeData.gasPrice,
    nonce: await provider.getTransactionCount(signer.address),
    chainId: network.chainId,
    type: 0,
};

tx.gasLimit = await provider.estimateGas(tx);

// Firmar manualmente
const signedTx = await signer.signTransaction(tx);

// Enviar la transacción firmada
const txResponse = await provider.broadcastTransaction(signedTx);
const receipt = await txResponse.wait();
if (receipt.status === 1) {
    console.log(`Transacción confirmada en el bloque ${receipt.blockNumber}`);
} else {
    console.error("Transferencia fallida");
}
```

En este ejemplo se incluye explícitamente `type: 0` para forzar una transacción *legacy*. Esto es importante porque estamos trabajando sobre una red privada con reglas de ejecución compatibles con EVM Byzantium, donde el formato de transacción esperado es el tradicional (`gasPrice`) y no el de transacciones EIP-1559.

Si no se fija `type: 0`, `ethers` puede inferir otro tipo de transacción a partir de los campos presentes. En ese caso, la transacción puede serializarse de una forma que el nodo no acepta y terminar en errores como `invalid sender` al invocar `broadcastTransaction`.

En este caso es opcional la inclusión del campo `from` en la transacción que se firma manualmente. En `ethers`, la dirección del emisor se recupera a partir de la firma; si se firma una transacción raw con campos incompatibles con el tipo de transacción esperado por la red, el nodo puede rechazarla con un error como `invalid sender`.


### Procedimiento B: enviar con `wallet.sendTransaction`

Equivalente al procedimiento B de Python: `wallet.sendTransaction()` firma automáticamente la transacción en el cliente y la envía al nodo, sin necesidad de llamar a `signTransaction` explícitamente.

```javascript
const provider = new ethers.JsonRpcProvider("http://localhost:8545");
const signer = wallet.connect(provider);

const txResponse = await signer.sendTransaction({
    to,
    value: ethers.parseEther("1.0"),
});

const receipt = await txResponse.wait();
if (receipt.status === 1) {
    console.log(`Transacción confirmada en el bloque ${receipt.blockNumber}`);
} else {
    console.error("Transferencia fallida");
}
```

En este caso, `ethers` se encarga internamente de obtener el `gasPrice`, el `nonce` y el `chainId`, por lo que no es necesario proporcionarlos. Si se desea tener control sobre estos parámetros, se pueden incluir en el objeto que se pasa a `sendTransaction`.
