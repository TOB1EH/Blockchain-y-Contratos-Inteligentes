/**
 * Despliega el stack completo: ENS -> Token -> CFPFactory.
 *
 * Uso:
 *   node scripts/deploy.js [rpc_url]
 *
 * Por defecto conecta a http://127.0.0.1:8545. Usa CFP_MNEMONIC del entorno
 * como cuenta owner. Si no esta definida, genera una nueva frase aleatoria.
 *
 * Orden de despliegue:
 *   1. ENSRegistry
 *   2. PublicResolver (toma direccion del registry)
 *   3. ReverseRegistrar
 *   4. Configurar arbol de nodos ENS (cfp, usuarios.cfp, llamados.cfp, addr.reverse)
 *   5. FIFSRegistrar para `usuarios.cfp`
 *   6. CFPGovernanceToken
 *   7. CFPFactory (toma direccion del token)
 *
 * Tambien fondea 10 cuentas MetaMask con 1000 ETH c/u e imprime las variables
 * de entorno necesarias para la API.
 */

import { ethers } from "ethers";
import { readFileSync, writeFileSync, mkdirSync } from "fs";
import { dirname, join } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

const RPC_URL = process.argv[2] ?? "http://127.0.0.1:8545";
const HARDHAT_DEFAULT_MNEMONIC =
  "test test test test test test test test test test test junk";

const MNEMONIC =
  process.env.CFP_MNEMONIC ?? ethers.HDNodeWallet.createRandom().mnemonic?.phrase ?? "";

const DEFAULT_METAMASK_MNEMONIC = "odor tuition process ancient private piano rule noise crazy tomorrow depend nasty";
const METAMASK_MNEMONIC =
  process.env.CFP_METAMASK_MNEMONIC ?? DEFAULT_METAMASK_MNEMONIC;

// ── Helpers ENS ─────────────────────────────────────────────────────────────

function namehash(name) {
  return ethers.namehash(name);
}

function labelHash(label) {
  return ethers.keccak256(ethers.toUtf8Bytes(label));
}

// ── Lectura de artfefacts ───────────────────────────────────────────────────

function loadArtifact(contractName) {
  return JSON.parse(
    readFileSync(
      join(__dirname, `../artifacts/contracts/${contractName}.sol/${contractName}.json`),
      "utf8"
    )
  );
}

// ── Setup ───────────────────────────────────────────────────────────────────

const provider = new ethers.JsonRpcProvider(RPC_URL);
const deployer = ethers.HDNodeWallet.fromPhrase(MNEMONIC).connect(provider);
const network = await provider.getNetwork();

console.log(`Deployer: ${deployer.address} on ${RPC_URL}`);
console.log(`Chain ID: ${network.chainId}`);

const deployerBalance = await provider.getBalance(deployer.address);
if (deployerBalance < ethers.parseEther("1")) {
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

let txNonce = await deployer.getNonce();

function enc(contract, method, args) {
  return contract.interface.encodeFunctionData(method, args);
}

async function sendTx(to, data) {
  const tx = {
    from: deployer.address,
    to,
    data,
    nonce: txNonce++,
    gasLimit: 8_000_000n,
    gasPrice: ethers.parseUnits("1", "gwei"),
    chainId: network.chainId,
  };
  const signed = await deployer.signTransaction(tx);
  const sent = await provider.broadcastTransaction(signed);
  return await sent.wait();
}

async function deploy(name, args = []) {
  const artifact = loadArtifact(name);
  const cf = new ethers.ContractFactory(artifact.abi, artifact.bytecode, deployer);
  const deployTx = await cf.getDeployTransaction(...args);
  const receipt = await sendTx(null, deployTx.data);
  return new ethers.Contract(receipt.contractAddress, artifact.abi, deployer);
}

// ── 1. Desplegar contratos ENS (en orden, cada uno espera su receipt) ───────

console.log("\n=== Desplegando ENS ===");

const registry         = await deploy("ENSRegistry");
console.log("ENSRegistry:      ", registry.target);

const resolver         = await deploy("PublicResolver", [registry.target]);
console.log("PublicResolver:   ", resolver.target);

const reverseRegistrar = await deploy("ReverseRegistrar", [registry.target]);
console.log("ReverseRegistrar: ", reverseRegistrar.target);

// ── 2. Configurar arbol de nodos ENS ────────────────────────────────────────
//   cfp            ← deployer (propietario directo)
//   usuarios.cfp   ← FIFSRegistrar_usuarios (autoregistro de usuarios)
//   llamados.cfp   ← deployer (la API registra nombres de llamados)
//   addr.reverse   ← ReverseRegistrar

console.log("\n=== Configurando arbol de nodos ENS ===");

const ZeroHash = ethers.ZeroHash;

const R = registry.target;
const Rs = resolver.target;
const Rev = reverseRegistrar.target;

// Crear TLD "cfp"
await sendTx(R, enc(registry, "setSubnodeOwner", [ZeroHash, labelHash("cfp"), deployer.address]));
console.log("  nodo 'cfp' creado, owner = deployer");

// Reverse chain: reverse.addr
await sendTx(R, enc(registry, "setSubnodeOwner", [ZeroHash, labelHash("reverse"), deployer.address]));
await sendTx(R, enc(registry, "setSubnodeOwner", [namehash("reverse"), labelHash("addr"), Rev]));
console.log("  nodo 'addr.reverse' configurado");

// Configurar resolver por defecto en ReverseRegistrar
await sendTx(Rev, enc(reverseRegistrar, "setDefaultResolver", [Rs]));

// Desplegar FIFSRegistrar para `usuarios.cfp`
const registrarUsuarios = await deploy("FIFSRegistrar", [R, namehash("usuarios.cfp")]);
console.log("FIFSRegistrar (usuarios):", registrarUsuarios.target);

// Crear `usuarios.cfp` con el deployer como owner temporal
await sendTx(R, enc(registry, "setSubnodeOwner", [namehash("cfp"), labelHash("usuarios"), deployer.address]));
console.log("  nodo 'usuarios.cfp' creado, owner = deployer");

// Setear resolver para usuarios.cfp (la API lo expone, el frontend lo usa)
await sendTx(R, enc(registry, "setResolver", [namehash("usuarios.cfp"), Rs]));
console.log("  resolver de 'usuarios.cfp' configurado");

// Transferir ownership al FIFSRegistrar (solo el owner puede hacer setResolver)
await sendTx(R, enc(registry, "setOwner", [namehash("usuarios.cfp"), registrarUsuarios.target]));
console.log("  nodo 'usuarios.cfp' asignado al FIFSRegistrar");

// `llamados.cfp` queda bajo control directo del deployer
await sendTx(R, enc(registry, "setSubnodeOwner", [namehash("cfp"), labelHash("llamados"), deployer.address]));
console.log("  nodo 'llamados.cfp' creado, owner = deployer");

// Configurar resolver para el TLD (los subdominios tienen su propio owner)
await sendTx(R, enc(registry, "setResolver", [namehash("cfp"), Rs]));

// Registrar un usuario de prueba: alice.usuarios.cfp
const regUsr = registrarUsuarios.target;
await sendTx(regUsr, enc(registrarUsuarios, "register", [labelHash("alice"), deployer.address]));
const aliceNode = namehash("alice.usuarios.cfp");
await sendTx(R, enc(registry, "setResolver", [aliceNode, Rs]));
await sendTx(Rs, enc(resolver, "setAddr", [aliceNode, deployer.address]));
await sendTx(Rev, enc(reverseRegistrar, "setName", ["alice.usuarios.cfp"]));
console.log("  alice.usuarios.cfp ->", deployer.address);

// ── 3. Desplegar Token ERC-20 ──────────────────────────────────────────────

console.log("\n=== Desplegando CFPGovernanceToken ===");

const TOKENS_PER_ETH = 1000n;
const token = await deploy("CFPGovernanceToken", [TOKENS_PER_ETH]);
console.log("CFPGovernanceToken:", token.target);

// ── 4. Desplegar CFPFactory ─────────────────────────────────────────────────

console.log("\n=== Desplegando CFPFactory ===");

const factory = await deploy("CFPFactory", [token.target]);
const factoryAddress = await factory.getAddress();
console.log("CFPFactory:        ", factoryAddress);

// ── Guardar deployments ─────────────────────────────────────────────────────

const deploymentsDir = join(__dirname, "../deployments");
mkdirSync(deploymentsDir, { recursive: true });

const chainId = Number(network.chainId);

function saveDeployment(name, address, abi) {
  writeFileSync(
    join(deploymentsDir, `${name}.json`),
    JSON.stringify({ address, chainId, abi }, null, 2),
    "utf8"
  );
}

saveDeployment("ENSRegistry", registry.target, loadArtifact("ENSRegistry").abi);
saveDeployment("PublicResolver", resolver.target, loadArtifact("PublicResolver").abi);
saveDeployment("FIFSRegistrar", registrarUsuarios.target, loadArtifact("FIFSRegistrar").abi);
saveDeployment("ReverseRegistrar", reverseRegistrar.target, loadArtifact("ReverseRegistrar").abi);
saveDeployment("CFPGovernanceToken", token.target, loadArtifact("CFPGovernanceToken").abi);
saveDeployment("CFPFactory", factoryAddress, loadArtifact("CFPFactory").abi);

// ── Fondear cuentas MetaMask ─────────────────────────────────────────────────

const adminWallet = ethers.HDNodeWallet.fromPhrase(
  METAMASK_MNEMONIC, "", "m/44'/60'/0'/0/0"
);

console.log(`\n=== Fondeando cuentas MetaMask (1000 ETH each) ===`);
const hardhatFunders = Array.from({ length: 5 }, (_, fi) =>
  ethers.HDNodeWallet.fromPhrase(
    HARDHAT_DEFAULT_MNEMONIC, "", `m/44'/60'/0'/0/${fi}`
  ).connect(provider)
);
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
      console.log(`  ${i}: ${wallet.address} funded`);
      funderIdx = (funderIdx + attempt + 1) % hardhatFunders.length;
      sent = true;
      break;
    }
  }
  if (!sent) {
    console.log(`  ${i}: ${wallet.address} SKIPPED (no Hardhat account with enough balance)`);
  }
}

// ── Output final ────────────────────────────────────────────────────────────

console.log(`\n================================================================`);
console.log(`Contratos desplegados:`);
console.log(`================================================================`);
console.log(`ENSRegistry:       ${registry.target}`);
console.log(`PublicResolver:    ${resolver.target}`);
console.log(`FIFSRegistrar:     ${registrarUsuarios.target}`);
console.log(`ReverseRegistrar:  ${reverseRegistrar.target}`);
console.log(`CFPGovernanceToken: ${token.target}`);
console.log(`CFPFactory:        ${factoryAddress}`);
console.log(`\n================================================================`);
console.log(`Copia y pega estos exports en la terminal de la API:`);
console.log(`================================================================`);
console.log(`export CFP_MNEMONIC="${MNEMONIC}"`);
console.log(`export CFP_FACTORY_ADDRESS=${factoryAddress}`);
console.log(`export CFP_ADMIN_ADDRESS=${adminWallet.address}`);
console.log(`export CFP_ENS_REGISTRY=${registry.target}`);
console.log(`export CFP_ERC20_TOKEN=${token.target}`);
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
