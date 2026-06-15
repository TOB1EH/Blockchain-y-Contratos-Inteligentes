/**
 * Despliega CFPFactory en un nodo local y prepara las cuentas para el entorno.
 *
 * Uso:
 *   node scripts/deploy.js [rpc_url]
 *
 * Por defecto conecta a http://127.0.0.1:8545. Usa CFP_MNEMONIC del entorno
 * como cuenta owner del contrato. Si no está definida, genera una nueva frase
 * mnemónica aleatoria distinta del default de Hardhat.
 *
 * El script también genera una frase mnemónica independiente para MetaMask,
 * fondea las primeras 10 cuentas derivadas de ella, e imprime las variables
 * de entorno necesarias para ejecutar la API y los tests.
 */

import { ethers } from "ethers";
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const RPC_URL = process.argv[2] ?? "http://127.0.0.1:8545";
const HARDHAT_DEFAULT_MNEMONIC =
  "test test test test test test test test test test test junk";

// CFP_MNEMONIC: frase owner del contrato, NUNCA en MetaMask
const MNEMONIC =
  process.env.CFP_MNEMONIC ?? ethers.HDNodeWallet.createRandom().mnemonic?.phrase ?? "";

// Frase independiente para MetaMask (completamente distinta de CFP_MNEMONIC)
// En desarrollo local usa una frase fija para que las cuentas persistan entre reinicios.
const DEFAULT_METAMASK_MNEMONIC = "odor tuition process ancient private piano rule noise crazy tomorrow depend nasty";
const METAMASK_MNEMONIC =
  process.env.CFP_METAMASK_MNEMONIC ?? DEFAULT_METAMASK_MNEMONIC;

const artifact = JSON.parse(
    readFileSync(
        join(__dirname, "../artifacts/contracts/CFPFactory.sol/CFPFactory.json"),
        "utf8"
    )
);

const provider = new ethers.JsonRpcProvider(RPC_URL);
const deployer = ethers.HDNodeWallet.fromPhrase(MNEMONIC).connect(provider);
const network = await provider.getNetwork();

console.log(`Deploying CFPFactory from ${deployer.address} on ${RPC_URL}...`);
console.log(`Chain ID: ${network.chainId}`);

// Fondear el deployer si no tiene ETH (cuando CFP_MNEMONIC no es el default de Hardhat)
const deployerBalance = await provider.getBalance(deployer.address);
if (deployerBalance < ethers.parseEther("1")) {
    // Usar cuenta 0 de Hardhat para fondear
    const hardhatFunder = ethers.HDNodeWallet.fromPhrase(
        HARDHAT_DEFAULT_MNEMONIC
    ).connect(provider);
    const funderBalance = await provider.getBalance(hardhatFunder.address);
    if (funderBalance >= ethers.parseEther("1")) {
        console.log(`Funding deployer ${deployer.address} with 1 ETH from Hardhat...`);
        const tx = await hardhatFunder.sendTransaction({
            to: deployer.address,
            value: ethers.parseEther("1")
        });
        await tx.wait();
        console.log(`Deployer funded.`);
    }
}

const factory = new ethers.ContractFactory(artifact.abi, artifact.bytecode, deployer);
const contract = await factory.deploy();
await contract.waitForDeployment();
const address = await contract.getAddress();

// Guardar ABI + direccion + chainId
const deploymentsDir = join(__dirname, "../deployments");
mkdirSync(deploymentsDir, { recursive: true });

const deployment = {
    address,
    chainId: Number(network.chainId),
    abi: artifact.abi,
}

writeFileSync(
    join(deploymentsDir, "CFPFactory.json"),
    JSON.stringify(deployment, null, 2),
    "utf8"
)

// CFP_ADMIN_ADDRESS: primera cuenta derivada de la frase MetaMask
const adminWallet = ethers.HDNodeWallet.fromPhrase(
    METAMASK_MNEMONIC, "", "m/44'/60'/0'/0/0"
);

// Fondear las primeras 10 cuentas MetaMask desde cuentas de Hardhat
console.log(`\nFunding MetaMask accounts (1000 ETH each)...`);
const hardhatFunders = [];
for (let fi = 0; fi < 5; fi++) {
    hardhatFunders.push(
        ethers.HDNodeWallet.fromPhrase(
            HARDHAT_DEFAULT_MNEMONIC, "", `m/44'/60'/0'/0/${fi}`
        ).connect(provider)
    );
}
let funderIdx = 0;
for (let i = 0; i < 10; i++) {
    const wallet = ethers.HDNodeWallet.fromPhrase(
        METAMASK_MNEMONIC, "", `m/44'/60'/0'/0/${i}`
    ).connect(provider);
    const balance = await provider.getBalance(wallet.address);
    if (balance >= ethers.parseEther("999")) {
        console.log(`  ${i}: ${wallet.address} already has sufficient balance`);
        continue;
    }
    // Buscar un funder con saldo suficiente
    let sent = false;
    for (let attempt = 0; attempt < hardhatFunders.length; attempt++) {
        const funder = hardhatFunders[(funderIdx + attempt) % hardhatFunders.length];
        const funderBalance = await provider.getBalance(funder.address);
        if (funderBalance >= ethers.parseEther("1000")) {
            const tx = await funder.sendTransaction({
                to: wallet.address,
                value: ethers.parseEther("1000")
            });
            await tx.wait();
            console.log(`  ${i}: ${wallet.address} funded with 1000 ETH (from account ${(funderIdx + attempt) % hardhatFunders.length})`);
            funderIdx = (funderIdx + attempt + 1) % hardhatFunders.length;
            sent = true;
            break;
        }
    }
    if (!sent) {
        console.log(`  ${i}: ${wallet.address} SKIPPED (no Hardhat account with enough balance)`);
    }
}

// Logs finales
console.log(`\nCFPFactory deployed at: ${address}`);
console.log(`ABI y dirección guardados en contracts/deployments/CFPFactory.json\n`);
console.log(`================================================================`);
console.log(`Copiá y pegá estos exports en la terminal de la API:`);
console.log(`================================================================`);
console.log(`export CFP_MNEMONIC="${MNEMONIC}"`);
console.log(`export CFP_FACTORY_ADDRESS=${address}`);
console.log(`export CFP_ADMIN_ADDRESS=${adminWallet.address}`);
console.log(`export CFP_METAMASK_MNEMONIC="${METAMASK_MNEMONIC}"\n`);
console.log(`================================================================`);
console.log(`Frase para importar en MetaMask (10 cuentas fondeadas con 1000 ETH c/u):`);
console.log(`================================================================`);
console.log(`"${METAMASK_MNEMONIC}"\n`);
console.log(`Cuentas MetaMask:`);
for (let i = 0; i < 10; i++) {
    const wallet = ethers.HDNodeWallet.fromPhrase(
        METAMASK_MNEMONIC, "", `m/44'/60'/0'/0/${i}`
    );
    console.log(`  ${i}: ${wallet.address}  (privateKey: ${wallet.privateKey})`);
}
