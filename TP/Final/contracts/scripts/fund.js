/**
 * Fondea las primeras 10 cuentas derivadas de una frase mnemónica de MetaMask
 * usando la cuenta 0 de la frase default de Hardhat como fuente de fondos.
 *
 * Uso:
 *   node scripts/fund.js "<frase_mnemonic_metamask>" [rpc_url]
 *
 * Ejemplo:
 *   node scripts/fund.js "slide train nephew cube modify..." http://127.0.0.1:8545
 *
 * Transfiere 1000 ETH a cada una de las 10 cuentas. Es seguro re-ejecutarlo:
 * si una cuenta ya tiene saldo >= 999 ETH se salta.
 */

import { ethers } from "ethers";

const RPC_URL = process.argv[3] ?? "http://127.0.0.1:8545";
const METAMASK_MNEMONIC = process.argv[2];

if (!METAMASK_MNEMONIC) {
    console.error("Uso: node scripts/fund.js \"<frase_mnemonic_metamask>\" [rpc_url]");
    process.exit(1);
}

const HARDHAT_DEFAULT_MNEMONIC =
    "test test test test test test test test test test test junk";

const provider = new ethers.JsonRpcProvider(RPC_URL);
const funder = ethers.HDNodeWallet.fromPhrase(HARDHAT_DEFAULT_MNEMONIC).connect(provider);
const network = await provider.getNetwork();

console.log(`Funding from Hardhat default account ${funder.address} on ${RPC_URL}`);
console.log(`Chain ID: ${network.chainId}`);

for (let i = 0; i < 10; i++) {
    const wallet = ethers.HDNodeWallet.fromPhrase(
        METAMASK_MNEMONIC, "", `m/44'/60'/0'/0/${i}`
    ).connect(provider);
    const balance = await provider.getBalance(wallet.address);
    if (balance >= ethers.parseEther("999")) {
        console.log(`  ${i}: ${wallet.address} already has ${ethers.formatEther(balance)} ETH, skipping`);
        continue;
    }
    const tx = await funder.sendTransaction({
        to: wallet.address,
        value: ethers.parseEther("1000")
    });
    await tx.wait();
    console.log(`  ${i}: ${wallet.address} funded with 1000 ETH (tx: ${tx.hash})`);
}

console.log("\nDone.");
