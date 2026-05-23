/**
 * Despliega CFPFactory en un nodo local (hardhat node u otro nodo compatible).
 *
 * Uso:
 *   node scripts/deploy.js [rpc_url]
 *
 * Por defecto conecta a http://127.0.0.1:8545 con la cuenta 0 derivada de la
 * frase mnemónica estándar de hardhat node. Para usar otra cuenta o nodo,
 * pasar la URL como primer argumento y definir CFP_MNEMONIC en el entorno.
 */

import { ethers } from "ethers";
import { readFileSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const RPC_URL = process.argv[2] ?? "http://127.0.0.1:8545";
const MNEMONIC =
  process.env.CFP_MNEMONIC ??
  "test test test test test test test test test test test junk";

const { abi, bytecode } = JSON.parse(
  readFileSync(
    join(__dirname, "../artifacts/contracts/CFPFactory.sol/CFPFactory.json"),
    "utf8"
  )
);

const provider = new ethers.JsonRpcProvider(RPC_URL);
const deployer = ethers.HDNodeWallet.fromPhrase(MNEMONIC).connect(provider);

console.log(`Deploying CFPFactory from ${deployer.address} on ${RPC_URL}...`);

const factory = new ethers.ContractFactory(abi, bytecode, deployer);
const contract = await factory.deploy();
await contract.waitForDeployment();
const address = await contract.getAddress();

console.log(`CFPFactory deployed at: ${address}`);
console.log(`\nExport para el TP8:`);
console.log(`  export CFP_FACTORY_ADDRESS=${address}`);
console.log(`  export CFP_MNEMONIC="${MNEMONIC}"`);
