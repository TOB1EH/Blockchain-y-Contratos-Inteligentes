# TP5 — Contrato Ballot

Implementación de un contrato inteligente en Solidity que modela un sistema de votación con ciclo de vida controlado, desplegable en cualquier red compatible con Ethereum.

El contrato permite registrar propuestas, habilitar votantes, controlar el inicio y fin de la votación, y determinar las propuestas ganadoras con soporte para empates.

---

## Requisitos

- Node.js y npm instalados
- En Ubuntu:
  ```bash
  sudo apt install nodejs npm
  ```

---

## Instalación

Desde la carpeta raíz del proyecto (`Ballot/`):

```bash
npm install
```

Esto instala Hardhat y todas las dependencias declaradas en `package.json`.

---

## Estructura del proyecto

```
Ballot/
├── contracts/
│   └── Ballot.sol        ← el contrato en Solidity
├── scripts/
│   └── deploy.js         ← script de despliegue
├── test/
│   └── ballot.test.js    ← 41 tests automáticos
├── hardhat.config.js     ← configuración de Hardhat
└── package.json          ← dependencias
```

---

## Compilar el contrato

```bash
npx hardhat compile
```

Genera los artefactos (bytecode y ABI) en `artifacts/`.

---

## Ejecutar los tests

```bash
npx hardhat test
```

Hardhat levanta una red local efímera, despliega el contrato, corre los 41 tests y muestra los resultados. No se necesita ningún nodo externo.

Resultado esperado:

```
  Ballot
    Deployment       (7 tests)
    Starting         (12 tests)
    Voting           (9 tests)
    After voting ends (13 tests)

  41 passing
```

---

## Desplegar en una red local persistente

Para probar el contrato de forma interactiva, primero levantá la red de Hardhat:

```bash
npx hardhat node
```

En otra terminal, desplegá el contrato:

```bash
npx hardhat run scripts/deploy.js --network localhost
```

Abrir la consola interactiva:

```bash
npx hardhat console --network localhost
```

Desde la consola podés interactuar con el contrato desplegado:

```javascript
const { ethers } = await hre.network.connect();
const ballot = await ethers.getContractAt("Ballot", "0x5FbDB2315678afecb367f032d93F642f64180aa3");
await ballot.numProposals();   // → 5n
await ballot.chairperson();    // → la primera cuenta del nodo
```

---

## Funcionalidades del contrato

| Función | Quién puede llamarla | Cuándo |
|---|---|---|
| `giveRightToVote(addr)` | chairperson | Antes de `start()` |
| `giveAllRightToVote(addrs)` | chairperson | Antes de `start()` |
| `withdrawRightToVote(addr)` | chairperson | Antes de `start()` |
| `start()` | chairperson | Una vez |
| `vote(index)` | votantes habilitados | Entre `start()` y `end()` |
| `end()` | chairperson | Después de `start()` |
| `winningProposals()` | cualquiera | Después de `end()` |
| `winners()` | cualquiera | Después de `end()` |