# Trabajo Práctico 8

## Consigna

Implementar una API REST que interactúe con los contratos `CFP` y `CFPFactory` del práctico anterior y permita acceder a sus funcionalidades.

En la API los *hashes*, direcciones y transacciones se expresarán como cadenas hexadecimales de la longitud adecuada y el prefijo "0x". Los valores enteros se expresarán como números decimales. La información temporal (por ejemplo, fecha y hora del cierre de convocatoria), deberá expresarse en formato ISO 8601.

El contrato `CFPFactory` estará desplegado en un nodo que recibe requerimientos RPC en `http://localhost:8545`. La API debe conectarse con el nodo mediante HTTP, y debe responder a requerimientos escuchando en el puerto 5000 de `localhost`.

El práctico 7 no incluía ningún mecanismo de despliegue. A los efectos de poder probar este práctico, deberán prever un mecanismo de despliegue en un nodo local (desplegado por ejemplo con `npx hardhat node`). El mecanismo de despliegue puede ser mediante `ignition` o un script *ad hoc*.

La API deberá trabajar con una cuenta local, es decir, debe poder interactuar con un nodo que no tiene definida ninguna cuenta. Esta cuenta se obtendrá de la frase mnemónica definida en la variable de entorno `CFP_MNEMONIC`. Se asume que la cuenta que ha desplegado el contrato es la que tiene el índice 0 (`m/44'/60'/0'/0/0`). La forma de obtener esta cuenta se describe más adelante.

La ABI de los contratos puede obtenerse de los archivos JSON creados por Hardhat en el directorio `artifacts` del proyecto del TP anterior (por ejemplo, `artifacts/contracts/CFPFactory.sol/CFPFactory.json`, campo `abi`). El servidor puede almacenar la ABI en el código fuente, o en un archivo de configuración del proyecto.

La dirección del contrato `CFPFactory` desplegado debe ser leída de la variable de entorno `CFP_FACTORY_ADDRESS`.

Cualquier otra información que requiera el servidor para ser ejecutado debe ser provista en línea de comandos, por variables de entorno o por un archivo de configuración. En ningún caso debe ser necesario modificar el código para que el servidor se ejecute. Cualquier requerimiento debe estar documentado en el `README.md`.

La API debe proveer los siguientes *endpoints*:

### `/create`

* Crea un llamado a presentación de propuestas utilizando la función correspondiente de `CFPFactory`.
* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `callId`: Hash que identifica al llamado.
  * `closingTime`: Fecha y hora del cierre de convocatoria, expresada en formato ISO 8601.
  * `signature`: Firma, con la clave privada del que hace la llamada, de la dirección del contrato concatenada con `callId` y con `closingTime`. La API utiliza la dirección que se deriva de la firma para asignarle la propiedad del llamado creado. El mensaje a firmar es una secuencia de bytes de longitud 84. Los primeros 20 bytes son la dirección del contrato, los siguientes 32 bytes son el `callId`, y los últimos 32 bytes son el *timestamp* correspondiente al `closingTime`, codificado como un entero *big endian* de 32 bytes. Antes de ser firmado, al mensaje se le agrega el prefijo estándar de Ethereum `\x19Ethereum Signed Message:\n` seguido de la longitud del mensaje en bytes en formato decimal ASCII, para evitar confusión con la firma de transacciones.  En el caso de la biblioteca `web3` de Python, esto equivale a que el mensaje sea procesado por la función `encode_defunct` de `eth_account.messages` de la biblioteca `eth-account` de Python previo a la firma.
* Retorno exitoso:
  * Código HTTP: 201
  * Cuerpo: Un objeto JSON con un campo "message" con valor OK.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                          | Código | Mensaje              |
    |--------------------------------|--------|----------------------|
    | Content-Type incorrecto        | 400    | INVALID_MIMETYPE     |
    | campo requerido ausente        | 400    | MISSING_FIELD        |
    | callId mal formado             | 400    | INVALID_CALLID       |
    | closingTime mal formado        | 400    | INVALID_TIME_FORMAT  |
    | callId ya existente            | 403    | ALREADY_CREATED      |
    | emisor no autorizado           | 403    | UNAUTHORIZED         |
    | tiempo de cierre inválido      | 400    | INVALID_CLOSING_TIME |
    | firma inválida                 | 400    | INVALID_SIGNATURE    |
    | desconocida                    | 500    | INTERNAL_ERROR       |

### `/register`

* Permite a un usuario registrarse para crear llamados, y los autoriza de inmediato.
* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `address`: Dirección del solicitante.
  * `signature`: Firma de la dirección del contrato con la clave privada del solicitante. El mensaje a firmar es una secuencia de bytes de longitud 20. Antes de ser firmado, al mensaje se le agrega el prefijo estándar de Ethereum `\x19Ethereum Signed Message:\n` seguido de la longitud del mensaje en bytes en formato decimal ASCII, para evitar confusión con la firma de transacciones. En el caso de la biblioteca `web3` de Python, esto equivale a que el mensaje sea procesado por la función `encode_defunct` de `eth_account.messages` de la biblioteca `eth-account` de Python previo a la firma. La API verifica que la dirección recuperada de la firma coincida con el campo `address`.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo "message" con valor OK.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                          | Código | Mensaje              |
    |--------------------------------|--------|----------------------|
    | Content-Type incorrecto        | 400    | INVALID_MIMETYPE     |
    | campo requerido ausente        | 400    | MISSING_FIELD        |
    | dirección inválida             | 400    | INVALID_ADDRESS      |
    | ya estaba autorizado           | 403    | ALREADY_AUTHORIZED   |
    | firma inválida                 | 400    | INVALID_SIGNATURE    |
    | desconocida                    | 500    | INTERNAL_ERROR       |

### `/register-proposal`

* Permite a un usuario registrar una propuesta en un determinado llamado. Este registro es anónimo, es decir, la dirección que quedará registrada en el contrato es la utilizada por el servidor de la API.
* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `callId`: Hash que identifica al llamado.
  * `proposal`: Hash que identifica a la propuesta.
* Retorno exitoso:
  * Código HTTP: 201
  * Cuerpo: Un objeto JSON con un campo "message" con valor OK.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                          | Código | Mensaje              |
    |--------------------------------|--------|----------------------|
    | Content-Type incorrecto        | 400    | INVALID_MIMETYPE     |
    | campo requerido ausente        | 400    | MISSING_FIELD        |
    | callId mal formado             | 400    | INVALID_CALLID       |
    | callId inexistente             | 404    | CALLID_NOT_FOUND     |
    | propuesta mal formada          | 400    | INVALID_PROPOSAL     |
    | propuesta ya existente         | 403    | ALREADY_REGISTERED   |
    | desconocida                    | 500    | INTERNAL_ERROR       |

### `/authorized/:address`

* Método: `GET`
* Argumento: `:address` corresponde a una dirección
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo booleano
    * "authorized", el estado de autorización de la dirección provista.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código |  Mensaje             |
    |--------------------------|--------|----------------------|
    |dirección inválida        | 400    | INVALID_ADDRESS      |
    |desconocida               | 500    | INTERNAL_ERROR       |

### `/calls/:call_id`

* Método: `GET`
* Argumento: `:call_id` es el hash que identifica a un llamado
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con dos campos de tipo `string`:
    * "creator", la dirección del creador del llamado.
    * "cfp", la dirección del contrato que representa al llamado.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código |  Mensaje             |
    |--------------------------|--------|----------------------|
    |callId mal formado        | 400    | INVALID_CALLID       |
    |callId inexistente        | 404    | CALLID_NOT_FOUND     |
    |desconocida               | 500    | INTERNAL_ERROR       |

### `/closing-time/:call_id`

* Método: `GET`
* Argumento: `:call_id` es el hash que identifica a un llamado
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo de tipo `string`:
    * "closingTime", la fecha y hora de cierre del llamado, en formato ISO 8601.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código |  Mensaje             |
    |--------------------------|--------|----------------------|
    |callId mal formado        | 400    | INVALID_CALLID       |
    |callId inexistente        | 404    | CALLID_NOT_FOUND     |
    |desconocida               | 500    | INTERNAL_ERROR       |

### `/contract-address`

* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo de tipo `string`:
    * "address", dirección del contrato factoría.

### `/contract-owner`

* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo de tipo `string`:
    * "address", dirección del dueño del contrato factoría.

### `/proposal-data/:call_id/:proposal`

* Método: `GET`
* Argumentos:
  * `:call_id` es el hash que identifica a un llamado.
  * `:proposal` es el hash que identifica una propuesta.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con tres campos:
    * "sender", de tipo "string" con la dirección del que envió la propuesta.
    * "blockNumber", de tipo "number" con el número de bloque en el cual se registró.
    * "timestamp", de tipo string, con la fecha y hora de registro en formato ISO 8601.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código |  Mensaje             |
    |--------------------------|--------|----------------------|
    |callId mal formado        | 400    | INVALID_CALLID       |
    |callId inexistente        | 404    | CALLID_NOT_FOUND     |
    |propuesta mal formada     | 400    | INVALID_PROPOSAL     |
    |propuesta inexistente     | 404    | PROPOSAL_NOT_FOUND   |
    |desconocida               | 500    | INTERNAL_ERROR       |

## Mensajes

| ID                  | Mensaje                               |
|---------------------|---------------------------------------|
| INVALID_ADDRESS     | "Dirección inválida"                  |
| INVALID_SIGNATURE   | "Firma inválida"                      |
| INVALID_MIMETYPE    | "Tipo MIME inválido"                  |
| INVALID_CALLID      | "Identificador de llamado incorrecto" |
| INVALID_PROPOSAL    | "Formato de propuesta incorrecto"     |
| INVALID_TIME_FORMAT | "Formato de tiempo incorrecto"        |
| INVALID_CLOSING_TIME| "Tiempo de cierre inválido"           |
| MISSING_FIELD       | "Campo requerido ausente"             |
| ALREADY_AUTHORIZED  | "Ya está autorizado"                  |
| ALREADY_CREATED     | "El llamado ya existe"                |
| ALREADY_REGISTERED  | "La propuesta ya ha sido registrada"  |
| CALLID_NOT_FOUND    | "El llamado no existe"                |
| PROPOSAL_NOT_FOUND  | "La propuesta no existe"              |
| UNAUTHORIZED        | "No autorizado"                       |
| INTERNAL_ERROR      | "Error interno"                       |
| OK                  | "OK"                                  |

## Uso de una frase mnemónica

Una frase mnemónica BIP39 (Bitcoin Improvement Proposal 39) es una herramienta utilizada para generar y recordar claves privadas de redes Blockchain. Si bien fue creada para Bitcoin, se utiliza en Ethereum y otras redes. BIP39 define un estándar para la creación de claves privadas a partir de una frase de recuperación (también conocida como semilla) de entre 12 y 24 palabras.
Si bien es posible generar frases en distintos idiomas, se recomienda utilizar el inglés, ya que es el idioma más utilizado y el que tiene mayor soporte.

La frase de recuperación se genera a partir de una fuente de entropía aleatoria y se codifica en una secuencia de palabras que siguen una lista de palabras estándar. Cada palabra de la lista está asociada a un número específico, lo que permite codificar la entropía en un formato fácil de recordar y escribir. Las palabras están elegidas de tal forma que sean difíciles de confundir entre sí. Por ejemplo, no hay palabras que difieran en solo una letra, y las primeras cuatro letras de cada palabra son únicas.

La lista tiene 2048 palabras, lo que significa que cada palabra representa 11 bits de información. Por lo tanto, una frase de 12 palabras representa 132 bits en total (12 x 11), de los cuales 128 son bits de entropía y 4 son bits de checksum. Una frase de 24 palabras representa 264 bits en total, de los cuales 256 son de entropía y 8 de checksum. La entropía es una medida de la aleatoriedad de la fuente de datos. Cuanto mayor sea la entropía, más difícil será adivinar la frase de recuperación.

La secuencia de palabras se utiliza como semilla para generar una clave maestra que a su vez se utiliza para generar claves privadas para diferentes criptomonedas. Las claves privadas se derivan a través de una función criptográfica determinista conocida como Hierarchical Deterministic Wallet (HD Wallet), lo que significa que cada vez que se utiliza la misma semilla, se generará la misma secuencia de claves privadas.

Este proceso de generación de claves privadas a partir de una frase de recuperación mnemónica facilita la copia de seguridad y recuperación de las claves en caso de pérdida o robo del dispositivo de almacenamiento. La frase de recuperación se puede escribir en un papel y almacenar en un lugar seguro, o se puede guardar en un archivo cifrado en un dispositivo de almacenamiento externo.

### Ejemplos de uso de una frase mnemónica

El siguiente ejemplo muestra cómo generar una frase mnemónica aleatoria y derivar cuentas Ethereum a partir de ella.

En Python con `eth-account`:

```python
from eth_account import Account
from eth_account.hdaccount import generate_mnemonic

# Como es una característica no auditable, debemos habilitarla explícitamente
Account.enable_unaudited_hdwallet_features()

mnemonic = generate_mnemonic(num_words=12, lang="english")
print(mnemonic)
# Por ejemplo: "cute alley left buddy deal ripple action sugar snap betray illegal stomach"

account = Account.from_mnemonic(mnemonic)
print(account.address)
# 0x8D624b950AFf3D012bB70d04B3a50F77B764b16E (si usamos la frase del ejemplo anterior)
```

En JavaScript con `ethers` (v6):

```javascript
import { ethers } from "ethers";

const mnemonic = ethers.Mnemonic.entropyToPhrase(ethers.randomBytes(16));
console.log(mnemonic);
// Por ejemplo: "visa whip scatter dawn garden identify attract pizza enjoy flat eye social"

const wallet = ethers.HDNodeWallet.fromPhrase(mnemonic);
console.log(wallet.address);
// 0xbE4E1D90F7bA72D0b062e003CD598a42889DC050 (si usamos la frase del ejemplo anterior)
```

Cada vez que se genera una frase nueva, las claves privadas y las direcciones derivadas son distintas.

#### Caso especial: `hardhat node`

`hardhat node` utiliza siempre la misma frase fija y pública:

```text
test test test test test test test test test test test junk
```

Este es un mecanismo establecido en el estándar BIP32 (Bitcoin Improvement Proposal 32), que define la forma en la que se generan las claves privadas a partir de una clave maestra, y el estándar BIP44, que define el uso de claves maestras para generar claves privadas para distintas criptomonedas. El HD Path se representa como una cadena de texto que sigue el siguiente formato:

```text
m / purpose' / coin_type' / account' / change / address_index
```

El HD Path utilizado por `hardhat node` es `m/44'/60'/0'/0/{address_index}`, donde 44 hace referencia al mecanismo estandarizado en BIP44, 60 indica que se trata de una dirección Ethereum, y `address_index` es el índice de dirección que queremos utilizar. Por ejemplo, para obtener la segunda dirección se usa el índice 1.

En Python con `eth-account`:

```python
from eth_account import Account

# Como es una característica no auditable, debemos habilitarla explícitamente
Account.enable_unaudited_hdwallet_features()

mnemonic = "test test test test test test test test test test test junk"
for i in range(10):
    print(Account.from_mnemonic(mnemonic, account_path=f"m/44'/60'/0'/0/{i}").address)
```

En JavaScript con `ethers` (v6):

```javascript
import { ethers } from "ethers";

const mnemonic = "test test test test test test test test test test test junk";
for (let i = 0; i < 10; i++) {
    const wallet = ethers.HDNodeWallet.fromPhrase(mnemonic, undefined, `m/44'/60'/0'/0/${i}`);
    console.log(wallet.address);
}
```

El resultado en ambos casos será:

```text
0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
0x70997970C51812dc3A010C7d01b50e0d17dc79C8
0x3C44CdDdB6a900fa2b585dd299e03d12FA4293BC
0x90F79bf6EB2c4f870365E785982E1f101E93b906
0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65
0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc
0x976EA74026E726554dB657fA54763abd0C3a0aa9
0x14dC79964da2C08b23698B3D3cc7Ca32193d9955
0x23618e81E3f5cdF7f54C3d65f7FBc0aBf5B21E8f
0xa0Ee7A142d267C1f36714E4a8F75612F20a79720
```

que se corresponde exactamente con las cuentas que muestra `hardhat node` al iniciarse.

#### Contraseña adicional (BIP39 passphrase)

BIP39 permite combinar la frase mnemónica con una contraseña opcional (*passphrase*) al derivar la clave maestra. Si se usa una contraseña, las claves generadas son completamente distintas a las que se obtienen con la misma frase sin contraseña. Esto permite tener "billeteras ocultas": con la misma frase mnemónica, distintas contraseñas producen distintas cuentas.

El valor por defecto es la cadena vacía `""`, que es el estándar BIP39 y lo que utilizan `hardhat node`, MetaMask y la mayoría de las herramientas.

En Python con `eth-account`:

```python
account = Account.from_mnemonic(mnemonic, passphrase="mi contraseña secreta")
```

En JavaScript con `ethers` (v6):

```javascript
const wallet = ethers.HDNodeWallet.fromPhrase(mnemonic, "mi contraseña secreta", `m/44'/60'/0'/0/0`);
```

## Firma y verificación de mensajes

El mecanismo de firma usado en este práctico sigue el estándar Ethereum de mensajes firmados. Antes de firmar, al mensaje se le agrega el prefijo `\x19Ethereum Signed Message:\n{longitud}`, lo que evita que una firma de mensaje pueda confundirse con una firma de transacción. Este prefijo es agregado automáticamente tanto por `encode_defunct` (Python) como por `signMessage` (JS).

### Firma de un mensaje binario

El mensaje a firmar es una secuencia de bytes construida concatenando los campos relevantes. En Python, los bytes se construyen directamente; en JS, `ethers.concat` devuelve un string hexadecimal que debe convertirse a `Uint8Array` con `ethers.getBytes` antes de firmar, de lo contrario `signMessage` lo interpretaría como UTF-8.

En Python con `eth-account`:

```python
from eth_account import Account
from eth_account.messages import encode_defunct

Account.enable_unaudited_hdwallet_features()

# Construir el mensaje como secuencia de bytes
contract_address = bytes.fromhex("f39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
call_id = bytes.fromhex("abcd" * 16)
message = contract_address + call_id  # 20 + 32 = 52 bytes

# Firmar
signable = encode_defunct(message)
signed = account.sign_message(signable)
print(signed.signature.hex())
```

En JavaScript con `ethers` (v6):

```javascript
import { ethers } from "ethers";

// Construir el mensaje como Uint8Array (52 bytes)
const contractAddress = ethers.getBytes("0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266");
const callId = ethers.getBytes("0x" + "abcd".repeat(16));
const message = ethers.getBytes(ethers.concat([contractAddress, callId]));

// Firmar
const signature = await wallet.signMessage(message);
console.log(signature);
```

Ambos producen la misma firma para el mismo mensaje y la misma clave privada.

### Verificación (recuperación de la dirección)

A partir de la firma y el mensaje original se recupera la dirección del firmante, sin necesidad de conocer la clave pública de antemano.

En Python con `eth-account`:

```python
recovered = Account.recover_message(signable, signature=signed.signature)
print(recovered)  # 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```

En JavaScript con `ethers` (v6):

```javascript
const recovered = ethers.verifyMessage(message, signature);
console.log(recovered);  // 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266
```
