# Patrones extraidos de los ejemplos del profesor

## Estructura de los ejemplos

Los ejemplos estan en el directorio `ejemplos/` de la rama `master`:

```
ejemplos/
  Bank/             # Contrato bancario simple con patron pull
  BuggyBank/        # Variante con bugs intencionales y fixed
  ENS/              # Implementacion completa de ENS
  ERC20/            # Token ERC-20 con compra
  ERC721/           # Token ERC-721 (NFT) con venta de entradas
```

## ENS (`ejemplos/ENS/`)

### Contratos (todos usables tal cual)

| Contrato | Archivo | Uso |
|----------|---------|-----|
| `ENSRegistry` | `contracts/ENSRegistry.sol` | Registro central con `owner()`, `resolver()`, `setSubnodeOwner()`, `setResolver()` |
| `FIFSRegistrar` | `contracts/FIFSRegistrar.sol` | Registrador FIFS para un dominio, `register(label, newOwner)` |
| `PublicResolver` | `contracts/PublicResolver.sol` | Implementa `IAddrResolver.addr()`, `INameResolver.name()`, `ITextResolver.text()` |
| `ReverseRegistrar` | `contracts/ReverseRegistrar.sol` | Resolucion inversa con `setName()`, maneja `addr.reverse` |
| `ENSDemo` | `contracts/ENSDemo.sol` | Ejemplo de consumo de ENS desde otro contrato |

### Interfaces

| Archivo | Funciones |
|---------|-----------|
| `interfaces/IAddrResolver.sol` | `addr(bytes32 node)`, `setAddr(bytes32, address)` |
| `interfaces/INameResolver.sol` | `name(bytes32 node)`, `setName(bytes32, string)` |
| `interfaces/ITextResolver.sol` | `text(bytes32, string key)`, `setText(bytes32, string, string)` |

### Patron de deploy (scripts/deploy.js)

```javascript
import { namehash, keccak256, toUtf8Bytes, ZeroHash } from "ethers";

// 1. Desplegar contratos
const registry         = await ENSRegistry.deploy();
const registrar        = await FIFSRegistrar.deploy(registry, namehash("iua"));
const reverseRegistrar = await ReverseRegistrar.deploy(registry);
const resolver         = await PublicResolver.deploy(registry);

// 2. Configurar arbol de nodos
registry.setSubnodeOwner(ZeroHash, labelHash("iua"), registrar);
registry.setSubnodeOwner(ZeroHash, labelHash("reverse"), owner);
registry.setSubnodeOwner(namehash("reverse"), labelHash("addr"), reverseRegistrar);
reverseRegistrar.setDefaultResolver(resolver);
```

### Patron de test (test/ENS.test.js)

Usa `loadFixture` para deploy y contexto compartido:

```javascript
const { ethers, networkHelpers } = await hre.network.create();
const { loadFixture } = networkHelpers;

async function deployENSFixture() {
    const [owner, alice, bob] = await ethers.getSigners();
    const registry = await (await ethers.getContractFactory("ENSRegistry")).deploy();
    // ... configuracion
    return { registry, resolver, registrar, reverseRegistrar, owner, alice, bob };
}
```

### Namehash

```javascript
import { namehash, keccak256, toUtf8Bytes } from "ethers";

namehash("alice.iua")           // nodo ENS
keccak256(toUtf8Bytes("alice"))  // label hash
```

## ERC-20 (`ejemplos/ERC20/`)

### IUAToken.sol

```solidity
contract IUAToken is ERC20, Ownable {
    uint256 constant initialSupply = 1000000 * (10**18);
    uint256 public constant TOKENS_PER_ETH = 1000;

    constructor() ERC20("IUAToken", "IUA") Ownable(msg.sender) {
        _mint(msg.sender, initialSupply);
    }

    function buy() external payable {
        require(msg.value > 0, "Debes enviar ETH para comprar tokens");
        uint256 amount = msg.value * TOKENS_PER_ETH;
        _mint(msg.sender, amount);
        emit TokensPurchased(msg.sender, msg.value, amount);
    }

    function withdraw(address payable to) external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No hay fondos para retirar");
        (bool ok, ) = to.call{value: balance}("");
        require(ok, "Transferencia fallida");
    }
}
```

### Patrones clave del ERC-20
- **OpenZeppelin v5.3.0**: `import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol"` y `{ Ownable } from "@openzeppelin/contracts/access/Ownable.sol"`
- **Constructor**: `ERC20("IUAToken", "IUA") Ownable(msg.sender)` - el owner se pasa como argumento en v5
- **Token price**: Constante `TOKENS_PER_ETH` (precio fijo, no oracle)
- **Decimals**: 18 (estandar), definido por `ERC20.decimals()` que retorna 18 por defecto
- **Buy**: `msg.value * TOKENS_PER_ETH` - mint directo al comprador
- **Withdraw**: soloOwner, transfiere ETH acumulado

### Diferencia con lo que necesitamos
El ejemplo del profesor **no tiene `redeem()`**. Nuestro token debe agregar:

```solidity
function redeem(uint256 amount) external {
    require(amount > 0 && balanceOf(msg.sender) >= amount, "Saldo insuficiente");
    uint256 ethAmount = amount / TOKENS_PER_ETH;
    _burn(msg.sender, amount);
    (bool ok, ) = msg.sender.call{value: ethAmount}("");
    require(ok, "Transferencia fallida");
}
```

## Bank (`ejemplos/Bank/`)

### Patron pull para retiros

```solidity
function withdraw(uint amount) public bankIsOpen enoughFunds(amount) nonZero(amount) {
    accounts[msg.sender].balance -= amount;
    (bool ok, ) = payable(msg.sender).call{value: amount}("");
    require(ok, "Transfer failed.");
    emit Withdraw(msg.sender, amount);
}
```

Este patron es el mismo que usaremos para `claimRefund()` en CFP: el contrato autoriza a ciertas direcciones y son ellas quienes ejecutan el retiro (mecanismo pull).

### Modifiers con revert personalizado

```solidity
error InsufficientFunds(uint requested, uint available);

modifier enoughFunds(uint amount) {
    if (accounts[msg.sender].balance < amount)
        revert InsufficientFunds({requested: amount, available: accounts[msg.sender].balance});
    _;
}
```

## BuggyBank (`ejemplos/BuggyBank/`)

### Patron de reentrancia y fix

`BuggyBank.sol` tiene vulnerabilidad de reentrancia en `withdraw()`.
`FixedBank.sol` usa `ReentrancyGuard` de OpenZeppelin o el patron checks-effects-interactions.

**Leccion**: En `claimRefund()` debemos usar checks-effects-interactions:
1. Verificar `refundable[msg.sender]`
2. `refundable[msg.sender] = false` (efecto ANTES de la transferencia)
3. `token.transfer(msg.sender, amount)` (interaccion)

## ERC-721 (`ejemplos/ERC721/`)

No es relevante para nuestro TP Final, pero usa el mismo patron que ERC-20 con OpenZeppelin.

## Hardhat config comun

Todos los ejemplos usan:

```javascript
import { defineConfig } from "hardhat/config";
import hardhatEthers from "@nomicfoundation/hardhat-ethers";
import hardhatEthersChaiMatchers from "@nomicfoundation/hardhat-ethers-chai-matchers";
import hardhatMocha from "@nomicfoundation/hardhat-mocha";
import hardhatNetworkHelpers from "@nomicfoundation/hardhat-network-helpers";

export default defineConfig({
  plugins: [
    hardhatEthers,
    hardhatEthersChaiMatchers,
    hardhatMocha,
    hardhatNetworkHelpers,
  ],
  solidity: "0.8.28",
  networks: {
    localhost: {
      type: "http",
      chainType: "l1",
      url: "http://127.0.0.1:8545",
    },
  },
});
```

Diferencias con nuestro TP/10:
- **Solidity 0.8.28** (vs 0.8.19 en TP/10)
- **Red localhost explícita** (TP/10 no la tiene, usa default)
- **hardhat-ignition** solo en ejemplos que usan Ignition (nosotros usamos deploy script)

## Dependencias npm

```json
{
  "devDependencies": {
    "@nomicfoundation/hardhat-ethers": "^4.0.8",
    "@nomicfoundation/hardhat-ethers-chai-matchers": "^3.0.5",
    "@nomicfoundation/hardhat-mocha": "^3.0.16",
    "@nomicfoundation/hardhat-network-helpers": "^3.0.5",
    "hardhat": "^3.0.0"
  },
  "dependencies": {
    "@openzeppelin/contracts": "^5.3.0"
  }
}
```
