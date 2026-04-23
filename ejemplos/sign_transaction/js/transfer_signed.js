#!/usr/bin/env node
/**
 * Transfiere fondos de una cuenta de la que se dispone la clave privada
 * (en keystore JSON) a otra cuenta arbitraria.
 */

"use strict";

const fs = require("node:fs/promises");
const path = require("node:path");
const process = require("node:process");
const readline = require("node:readline");
const { ethers } = require("ethers");

const DEFAULT_WEB3_URI = "~/blockchain-iua/bfatest/node/geth.ipc";

function expandHome(p) {
    if (!p) return p;
    if (p === "~") return process.env.HOME || p;
    if (p.startsWith("~/")) return path.join(process.env.HOME || "", p.slice(2));
    return p;
}

function ethereumAddress(address) {
    if (ethers.isAddress(address)) {
        return ethers.getAddress(address);
    }
    throw new Error("Invalid address");
}

function parseArgs(argv) {
    const args = {
        uri: DEFAULT_WEB3_URI,
        privateKeyFile: null,
        to: null,
        amount: null,
        unit: "wei",
    };

    for (let i = 2; i < argv.length; i += 1) {
        const a = argv[i];
        if (a === "--uri") args.uri = argv[++i];
        else if (a === "--private-key") args.privateKeyFile = argv[++i];
        else if (a === "--to") args.to = argv[++i];
        else if (a === "--amount") args.amount = argv[++i];
        else if (a === "--unit") args.unit = argv[++i];
        else if (a === "--help" || a === "-h") {
            printHelp();
            process.exit(0);
        } else {
            throw new Error(`Argumento desconocido: ${a}`);
        }
    }

    if (!args.privateKeyFile) throw new Error("Falta --private-key");
    if (!args.to) throw new Error("Falta --to");
    if (args.amount == null) throw new Error("Falta --amount");

    return args;
}

function printHelp() {
    console.log(`Transfiere fondos de una cuenta de la que se dispone la clave privada a otra cuenta arbitraria.
Por defecto, se conecta al nodo mediante '${DEFAULT_WEB3_URI}'.

Uso:
  node transfer_signed.js --private-key <archivo_keystore> --to <direccion> --amount <monto> [--unit <unidad>] [--uri <uri>]

Opciones:
  --uri           URI para la conexion con geth (http://... o ruta IPC)
  --private-key   Archivo con la clave privada en formato keystore JSON
  --to            Cuenta de destino
  --amount        Monto a transferir
  --unit          Unidad: wei | kwei | mwei | gwei | szabo | finney | ether
`);
}

async function askPassword(promptText = "Ingrese contraseña: ") {
    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
        terminal: true,
    });

    return new Promise((resolve) => {
        const onDataHandler = (char) => {
            char = String(char);
            switch (char) {
                case "\n":
                case "\r":
                case "\u0004":
                    process.stdin.removeListener("data", onDataHandler);
                    break;
                default:
                    readline.cursorTo(process.stdout, 0);
                    process.stdout.write(promptText + "*".repeat(rl.line.length));
                    break;
            }
        };

        process.stdin.on("data", onDataHandler);
        rl.question(promptText, (value) => {
            rl.history = rl.history.slice(1);
            rl.close();
            process.stdout.write("\n");
            resolve(value);
        });
    });
}

async function connectToNode(uri) {
    const resolvedUri = expandHome(uri);
    if (resolvedUri.startsWith("http://")) {
        const provider = new ethers.JsonRpcProvider(resolvedUri);
        await provider.getBlockNumber();
        return provider;
    }

    return new Promise((resolve, reject) => {
        const provider = new ethers.IpcSocketProvider(resolvedUri);
        let settled = false;

        const handleError = (err) => {
            if (settled) return;
            settled = true;
            reject(err);
        };

        provider.socket.once("error", handleError);

        provider
            .getBlockNumber()
            .then(() => {
                if (settled) return;
                settled = true;
                provider.socket.off("error", handleError);
                resolve(provider);
            })
            .catch((err) => {
                if (settled) return;
                settled = true;
                provider.socket.off("error", handleError);
                reject(err);
            });
    });
}

async function getWalletFromKeystore(filename, provider) {
    const filePath = expandHome(filename);
    let encryptedJson;
    try {
        encryptedJson = await fs.readFile(filePath, "utf8");
    } catch (err) {
        if (err && err.code === "ENOENT") {
            throw new Error(err.message);
        }
        throw err;
    }

    const password = await askPassword("Ingrese contraseña: ");
    try {
        const wallet = await ethers.Wallet.fromEncryptedJson(encryptedJson, password);
        return wallet.connect(provider);
    } catch {
        throw new Error("Contraseña incorrecta");
    }
}

function normalizeUnit(unit) {
    const map = {
        wei: "wei",
        Kwei: "kwei",
        kwei: "kwei",
        Mwei: "mwei",
        mwei: "mwei",
        Gwei: "gwei",
        gwei: "gwei",
        microether: "szabo",
        milliether: "finney",
        ether: "ether",
    };
    const normalized = map[unit];
    if (!normalized) {
        throw new Error(`Unidad no soportada: ${unit}`);
    }
    return normalized;
}

async function transfer(wallet, dstAddress, amount, unit) {
    const provider = wallet.provider;
    const to = ethereumAddress(dstAddress);
    const unitName = normalizeUnit(unit);

    const value = ethers.parseUnits(String(amount), unitName);
    const from = wallet.address;

    const [gasPrice, nonce, network, balance] = await Promise.all([
        provider.getFeeData().then((d) => {
            if (!d.gasPrice) throw new Error("No se pudo obtener gasPrice");
            return d.gasPrice;
        }),
        provider.getTransactionCount(from),
        provider.getNetwork(),
        provider.getBalance(from),
    ]);

    const tx = {
        from,
        to,
        value,
        gasPrice,
        nonce,
        chainId: Number(network.chainId),
    };

    const gasLimit = await provider.estimateGas(tx);
    tx.gasLimit = gasLimit;

    const gasCost = gasLimit * gasPrice;
    if (balance < value + gasCost) {
        throw new Error("Saldo insuficiente");
    }

    const sentTx = await wallet.sendTransaction(tx);
    const receipt = await sentTx.wait();

    if (receipt && receipt.status === 1) {
        console.log(`Transaccion confirmada en el bloque ${receipt.blockNumber}`);
    } else {
        throw new Error("Transferencia fallida");
    }
}

async function main() {
    try {
        const args = parseArgs(process.argv);

        if (!Number.isFinite(Number(args.amount)) || Number(args.amount) < 0) {
            throw new Error("Monto invalido");
        }

        const provider = await connectToNode(args.uri);
        const wallet = await getWalletFromKeystore(args.privateKeyFile, provider);
        await transfer(wallet, args.to, args.amount, args.unit);
    } catch (err) {
        const msg = err && err.message ? err.message : String(err);

        if (
            msg.includes("connect") ||
            msg.includes("ECONNREFUSED") ||
            msg.includes("ENOENT") ||
            msg.includes("socket")
        ) {
            const uriArg = process.argv.includes("--uri")
                ? process.argv[process.argv.indexOf("--uri") + 1]
                : DEFAULT_WEB3_URI;
            console.error(`Falla al contactar el nodo en '${uriArg}'`);
        } else {
            console.error(msg);
        }
        process.exit(1);
    }
}

main();
