# Compilacion y despliegue de contratos

Para poder interactuar con un contrato escrito en Solidity, es necesario compilarlo y desplegarlo en la red de Ethereum.

En este ejemplo, el proyecto utiliza Hardhat 3 con TypeScript para compilar, desplegar y testear el contrato `Ballot.sol`.

## Instalacion de dependencias

Para trabajar con el proyecto, debemos tener instalado Node.js y NPM. En Ubuntu, se puede instalar mediante el siguiente comando:

```bash
sudo apt install nodejs npm
```

Luego debemos instalar las dependencias del proyecto:

    npm install

## Estructura del proyecto

El proyecto tiene la siguiente estructura:

        .
        ├── contracts
        ├── ignition
        │   └── modules
        ├── test
        ├── hardhat.config.ts
        ├── package.json
        └── tsconfig.json

El directorio `contracts/` contiene los contratos escritos en Solidity. El directorio `ignition/modules/` contiene los modulos de despliegue. El directorio `test/` contiene los tests unitarios. El archivo `hardhat.config.ts` contiene la configuracion de Hardhat, y `tsconfig.json` define la configuracion de TypeScript.

En nuestro caso, el proyecto cuenta con un contrato llamado `Ballot.sol` en el directorio `contracts/`, un modulo de despliegue llamado `Ballot.ts` en `ignition/modules/` y un archivo de pruebas llamado `Ballot.ts` en `test/`.

## Compilacion con Hardhat

Para compilar los contratos, debemos ejecutar el siguiente comando:

    npx hardhat compile

Esto genera los artefactos de compilacion en el directorio `artifacts/`, que incluyen el bytecode y la interfaz ABI de cada contrato.

La configuracion minima utilizada por el proyecto es la siguiente:

```typescript
import { defineConfig } from "hardhat/config";
import hardhatToolboxMochaEthers from "@nomicfoundation/hardhat-toolbox-mocha-ethers";

export default defineConfig({
  plugins: [hardhatToolboxMochaEthers],
  solidity: "0.8.28",
});
```

## Despliegue con Hardhat Ignition

Hardhat utiliza el sistema de despliegue declarativo llamado *Hardhat Ignition*. En este proyecto, el modulo de despliegue se encuentra en `ignition/modules/Ballot.ts` y define las opciones iniciales del contrato:

```typescript
import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";
import { encodeBytes32String } from "ethers";

export default buildModule("BallotModule", (m) => {
  const languages = ["Aleman", "Bulgaro", "Catalan", "Danes", "Espanol"];
  const options = languages.map((language) => encodeBytes32String(language));

  const ballot = m.contract("Ballot", [options]);

  return { ballot };
});
```

Para desplegar el contrato, debemos ejecutar:

    npx hardhat ignition deploy ignition/modules/Ballot.ts

Por defecto, Hardhat despliega sobre una red local efimera. Si queremos desplegar sobre una red especifica, debemos declararla en `hardhat.config.ts` y usar `--network`.

Por ejemplo:

```typescript
import { defineConfig } from "hardhat/config";
import hardhatToolboxMochaEthers from "@nomicfoundation/hardhat-toolbox-mocha-ethers";

export default defineConfig({
  plugins: [hardhatToolboxMochaEthers],
  solidity: "0.8.28",
  networks: {
    localhost: {
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

En la lista `accounts` se deben colocar claves privadas, no direcciones. Hardhat usa esas claves para firmar transacciones localmente antes de enviarlas al nodo RPC.

Con esa configuracion, el despliegue sobre una red local persistente puede realizarse asi:

    npx hardhat ignition deploy ignition/modules/Ballot.ts --network localhost

## Consola de Hardhat

Para interactuar con el contrato desplegado desde la consola, podemos ejecutar:

    npx hardhat console --network localhost

Esto nos abre un entorno REPL de Node.js con acceso al entorno de Hardhat. Por ejemplo, podemos conectarnos a un contrato ya desplegado:

```typescript
const { ethers } = await hre.network.connect();
const ballot = await ethers.getContractAt("Ballot", "<direccion-del-contrato>");
await ballot.numProposals();
```

Otros ejemplos de acciones que se pueden realizar en la consola:

```typescript
const { ethers } = await hre.network.connect();
const accounts = await ethers.getSigners();
await accounts[0].getAddress();
```

```typescript
const proposal0 = await ballot.proposals(0);
ethers.decodeBytes32String(proposal0.name);
```

```typescript
await ballot.giveRightToVote(await accounts[1].getAddress());
await ballot.connect(accounts[1]).vote(1);
```

```typescript
const winnerIndex = await ballot.winningProposal();
const winnerName = ethers.decodeBytes32String(await ballot.winnerName());
winnerIndex;
winnerName;
```

Si se desea utilizar una cuenta local que no proviene del nodo, podemos crear una billetera a partir de su clave privada y conectarla al provider:

```typescript
const { ethers } = await hre.network.connect();
const wallet = new ethers.Wallet("0xTU_CLAVE_PRIVADA", ethers.provider);
await ballot.connect(wallet).vote(1);
```

## Red independiente con Hardhat

Hardhat tambien permite lanzar una red local independiente, persistente mientras el proceso este ejecutandose:

```bash
npx hardhat node
```

Este comando inicia un nodo JSON-RPC en `http://127.0.0.1:8545` y muestra en pantalla cuentas de prueba con sus claves privadas.

Una vez levantada la red, podemos desplegar y luego abrir la consola conectada a esa misma red:

```bash
npx hardhat ignition deploy ignition/modules/Ballot.ts --network localhost
npx hardhat console --network localhost
```

## Ejecucion de los casos de prueba

Para ejecutar los tests unitarios, debemos utilizar:

    npx hardhat test

Las pruebas de este ejemplo estan escritas en TypeScript en el archivo `test/Ballot.ts` y utilizan la API de Hardhat 3 mediante `hre.network.connect()`.