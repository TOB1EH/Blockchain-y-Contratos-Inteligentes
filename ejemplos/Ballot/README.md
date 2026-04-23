# Compilación y despliegue de contratos

Para poder interactuar con un contrato escrito en Solidity, es necesario compilarlo y desplegarlo en la red de Ethereum.

Veremos primero como hacerlo manualmente, paso a paso, y luego mediante el uso de una herramienta llamada Hardhat.

## Compilación manual

Para compilar un contrato, es necesario tener instalado el compilador de Solidity. En Ubuntu, se puede instalar mediante el siguiente comando:

```shell
sudo apt install solc
```

Una vez instalado, podemos compilar el contrato con el siguiente comando:

```shell
solc --bin --abi -o build/ contracts/Ballot.sol
```

El compilador genera dos archivos en el directorio `build/`: `Ballot.bin` y `Ballot.abi`. El primero contiene el bytecode del contrato, y el segundo contiene la interfaz ABI del contrato.

Ambos artefactos son necesarios para desplegar el contrato en la red de Ethereum. Veamos como desplegar el contacto:

```python
from web3 import Web3, HTTPProvider
import json
# Conectamos a la red de Ethereum
w3 = Web3(HTTPProvider("http://localhost:8545"))

# Cargamos el bytecode y la interfaz ABI del contrato
with open("build/Ballot.bin") as f:
    bytecode = f.read()
with open("build/Ballot.abi") as f:
    abi = json.load(f)

contract = w3.eth.contract(abi=abi, bytecode=bytecode)
```

`contract` es un objeto que nos permitirá invocar el constructor del contrato y luego interactuar con el contrato desplegado. Para desplegar el contrato, debemos invocar al método `constructor` del objeto `contract`. Como el arguento es del tipo `bytes32[]`, debemos ser capaces de convertir cadenas de texto en secuencias de bytes del tamaño adecuado. Para eso, definiremos un par de funciones auxiliares:

```python
def to_bytes32(s: str) -> bytes:
    return s.encode("utf-8").ljust(32, b"\0")[:32]
def from_bytes32(b: bytes) -> str:
    return b.decode("utf-8").rstrip("\0")
```

Ahora podemos desplegar el contrato:

```python
# Desplegamos el contrato
tx_hash = contract.constructor([to_bytes32("Alice"), to_bytes32("Bob"), to_bytes32("Carol")]).transact({'from': w3.eth.accounts[0]})
tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
contract_address = tx_receipt.contractAddress
```

Como resultado, `contract_address` contiene la dirección del contrato desplegado en la red de Ethereum. Ahora podemos utilizar esa dirección para conectarnos con el contrato e interactuar con el mismo:

```python
# Conectamos con el contrato
ballot = w3.eth.contract(address=contract_address, abi=abi)
ballot.functions.numProposals().call() # 3
```

## Compilación y despliegue con Hardhat

Hardhat es una herramienta que nos permite compilar, desplegar y testear contratos de forma automática. Para instalar Hardhat, debemos tener instalado Node.js y NPM. En Ubuntu, se puede instalar mediante el siguiente comando:

```bash
sudo apt install nodejs npm
```

A diferencia de otras herramientas, Hardhat se instala como dependencia local del proyecto y no requiere instalación global. Para instalar las dependencias del proyecto, debemos ejecutar:

```bash
npm install
```

El proyecto tiene la siguiente estructura:

```text
.
├── contracts
├── ignition
│   └── modules
├── test
├── hardhat.config.js
└── package.json
```

El directorio `contracts/` contiene los contratos escritos en Solidity. El directorio `ignition/modules/` contiene los módulos de despliegue. El directorio `test/` contiene los tests unitarios. El archivo `hardhat.config.js` contiene la configuración de Hardhat.

En nuestro caso, el proyecto ya está creado, y cuenta con un contrato llamado `Ballot.sol` en el directorio `contracts/`.

Para compilar los contratos, debemos ejecutar el siguiente comando:

```bash
npx hardhat compile
```

Esto genera los artefactos de compilación en el directorio `artifacts/`, que incluyen el bytecode y la interfaz ABI de cada contrato.

Para desplegar el contrato, Hardhat utiliza el sistema de despliegue declarativo llamado *Hardhat Ignition*:

```bash
npx hardhat ignition deploy ignition/modules/Ballot.js
```

¿Donde se despliega el contrato? Depende de la configuración establecida en el archivo `hardhat.config.js`. El *default* es en una red local efímera levantada automáticamente por Hardhat. Para desplegar en una red específica, se utiliza el parámetro `--network`:

```bash
npx hardhat ignition deploy ignition/modules/Ballot.js --network <nombre-red>
```

donde `<nombre-red>` debe estar definida en el archivo `hardhat.config.js`.

Un ejemplo de configuración de red en `hardhat.config.js` es el siguiente:

```javascript
import { defineConfig } from "hardhat/config";
import hardhatToolboxMochaEthers from "@nomicfoundation/hardhat-toolbox-mocha-ethers";

export default defineConfig({
    plugins: [hardhatToolboxMochaEthers],
    solidity: "0.8.28",
    networks: {
        local: {
            type: "http",
            chainType: "l1",
            url: "http://127.0.0.1:8545",
            accounts: [
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ]
        }
    }
});
```

En este ejemplo, la red se llama `local` y apunta a un nodo JSON-RPC escuchando en `127.0.0.1:8545`.

En la lista `accounts` se deben colocar claves privadas (por ejemplo, `0x...` de 64 hex), no direcciones. Hardhat usa esas claves para firmar transacciones localmente antes de enviarlas al nodo RPC.

Para redes reales, se recomienda cargar la clave privada desde variables de entorno en lugar de escribirla directamente en el archivo de configuración.

Para conectarnos con el contrato desplegado e interactuar con él de forma interactiva, podemos utilizar la consola de Hardhat:

```bash
npx hardhat console --network <nombre-red>
```

Esto nos abre un entorno REPL de Node.js con acceso al entorno de Hardhat. Por ejemplo, podemos obtener la cantidad de propuestas de un contrato ya desplegado:

```javascript
const { ethers } = await hre.network.connect();
const ballot = await ethers.getContractAt("Ballot", "<dirección-del-contrato>");
await ballot.numProposals(); // 3n
```

Otros ejemplos de acciones que se pueden realizar en la consola:

```javascript
// Obtener cuentas disponibles
const { ethers } = await hre.network.connect();
const accounts = await ethers.getSigners();
await accounts[0].getAddress();
```

```javascript
// Consultar el nombre de una propuesta (bytes32 -> string)
const proposal0 = await ballot.proposals(0);
ethers.decodeBytes32String(proposal0.name);
```

```javascript
// Dar derecho a voto a una cuenta
await ballot.giveRightToVote(await accounts[1].getAddress());
```

```javascript
// Votar por la propuesta con índice 1
await ballot.connect(accounts[1]).vote(1);
```

```javascript
// Consultar propuesta ganadora y nombre ganador
const winnerIndex = await ballot.winningProposal();
const winnerName = ethers.decodeBytes32String(await ballot.winnerName());
winnerIndex; // por ejemplo: 1n
winnerName;  // por ejemplo: "Bob"
```

## Red independiente con Hardhat

Hardhat también permite lanzar una red local independiente (persistente mientras el proceso esté ejecutándose):

```bash
npx hardhat node
```

Este comando inicia un nodo JSON-RPC en `http://127.0.0.1:8545` y muestra en pantalla cuentas de prueba con sus claves privadas.

Con la red ya ejecutándose, podemos desplegar el contrato contra esa red:

```bash
npx hardhat ignition deploy ignition/modules/Ballot.js --network local
```

Y luego abrir la consola conectada a la misma red:

```bash
npx hardhat console --network local
```

De esta forma, el contrato queda desplegado en una red local que se mantiene viva entre comandos, lo que facilita pruebas manuales e integración con herramientas externas (por ejemplo, frontends o scripts).

## Ejecución de los casos de prueba

Para ejecutar los tests unitarios:

```bash
npx hardhat test
```
