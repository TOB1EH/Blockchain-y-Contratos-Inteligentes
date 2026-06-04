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

/**
 * MODIFICACIONES:
 * Se mofifico el presente script para que, al desplegar, exporte automáticamente el
 * ABI y la dirección (address) del contrato a un archivo deployments/CFPFactory.json.
 * Esto evitará que se tengan que hardcodear direcciones en la API y en el Frontend.
 */

import { ethers } from "ethers";
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const RPC_URL = process.argv[2] ?? "http://127.0.0.1:8545";
const MNEMONIC =
  process.env.CFP_MNEMONIC ??
  "test test test test test test test test test test test junk";

const artifact = JSON.parse(
    readFileSync(
        join(__dirname, "../artifacts/contracts/CFPFactory.sol/CFPFactory.json"),
        "utf8"
    )
); // Cargar el artifact de CFPFactory para obtener el ABI y bytecode

const provider = new ethers.JsonRpcProvider(RPC_URL);
const deployer = ethers.HDNodeWallet.fromPhrase(MNEMONIC).connect(provider);
const network = await provider.getNetwork();

console.log(`Deploying CFPFactory from ${deployer.address} on ${RPC_URL}...`);
console.log(`Chain ID: ${network.chainId}`);

const factory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, deployer);
const contract = await factory.deploy();
await contract.waitForDeployment();
const address = await contract.getAddress();

// Guardar ABI + direccion + chainId para usar en la APU y el Frontend
const deploymentsDir = join(__dirname, "../deployments");
// Crear el directorio deployments si no existe:
mkdirSync(deploymentsDir, { recursive: true });

// Objeto con la información del despliegue:
const deployment = {
    address,
    chainId: Number(network.chainId),
    abi: artifact.abi,
}

// Escribir el archivo deployments/CFPFactory.json con la información del despliegue:
writeFileSync(
    join(deploymentsDir, "CFPFactory.json"),
    JSON.stringify(deployment, null, 2),
    "utf8"
)

// Derivar la dirección del admin (cuenta 2, para compatibilidad con tests) a partir de la frase mnemónica
const adminWallet = ethers.HDNodeWallet.fromPhrase(MNEMONIC, "", "m/44'/60'/0'/0/2");
// Logs finales
console.log(`\nCFPFactory deployed at: ${address}`);
console.log(`ABI y dirección guardados en contracts/deployments/CFPFactory.json\n`);
console.log(`================================================================`);
console.log(`Copiá y pegá estos exports en la terminal de la API (TP10):`);
console.log(`================================================================`);
console.log(`export CFP_MNEMONIC="${MNEMONIC}"`);
console.log(`export CFP_FACTORY_ADDRESS=${address}`);
console.log(`export CFP_ADMIN_ADDRESS=${adminWallet.address}\n`);
