#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { ethers } from "ethers";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const DEFAULT_RPC_URL = "http://localhost:8545";
const VALID_STATES = new Set(["pending", "in-progress", "done"]);
const VALID_TIMESTAMP_MODES = new Set(["contract", "events"]);

function printUsageAndExit(message) {
  if (message) {
    console.error(`Error: ${message}`);
  }

  console.error(`
Usage:
  node scripts/list-tasks-by-assignee.js \
    --board <task_board_address> \
    --assignee <address> \
    --state <pending|in-progress|done> \
    --timestamps <contract|events> \
    [--rpc <uri>]

Examples:
  node scripts/list-tasks-by-assignee.js \
    --board 0x1234...abcd \
    --assignee 0xabcd...1234 \
    --state pending \
    --timestamps contract

  node scripts/list-tasks-by-assignee.js \
    --board 0x1234...abcd \
    --assignee 0xabcd...1234 \
    --state done \
    --timestamps events \
    --rpc http://localhost:8545
`);

  process.exit(1);
}

function parseArgs(argv) {
  const args = {
    rpc: DEFAULT_RPC_URL,
  };

  for (let i = 0; i < argv.length; i++) {
    const token = argv[i];

    if (!token.startsWith("--")) {
      continue;
    }

    const key = token.slice(2);
    const value = argv[i + 1];

    if (!value || value.startsWith("--")) {
      printUsageAndExit(`Missing value for argument '${token}'`);
    }

    args[key] = value;
    i += 1;
  }

  if (!args.board) {
    printUsageAndExit("Argument '--board' is required");
  }

  if (!args.assignee) {
    printUsageAndExit("Argument '--assignee' is required");
  }

  if (!args.state || !VALID_STATES.has(args.state)) {
    printUsageAndExit("Argument '--state' must be one of: pending, in-progress, done");
  }

  if (!args.timestamps || !VALID_TIMESTAMP_MODES.has(args.timestamps)) {
    printUsageAndExit("Argument '--timestamps' must be one of: contract, events");
  }

  if (!ethers.isAddress(args.board)) {
    printUsageAndExit("'--board' is not a valid Ethereum address");
  }

  if (!ethers.isAddress(args.assignee)) {
    printUsageAndExit("'--assignee' is not a valid Ethereum address");
  }

  return args;
}

function loadArtifactJson(relativePath) {
  const artifactPath = path.join(__dirname, "..", relativePath);
  const raw = fs.readFileSync(artifactPath, "utf8");
  return JSON.parse(raw);
}

/**
 * Obtiene la lista de tareas de un responsable asignado para un estado dado.
 *
 * Especificación:
 * - Entrada:
 *   - taskBoardContract: instancia ethers de TaskBoard ya construida.
 *   - taskContractFactory: función que recibe la dirección de una Task y devuelve
 *     su contrato ethers ya conectado al mismo provider.
 *   - assignee: dirección del responsable asignado a consultar.
 *   - state: "pending" | "in-progress" | "done".
 *   - timestampSource: "contract" | "events".
 * - Salida:
 *   - Promise<Array<{ taskAddress: string, description: string, timestamps: object }>>
 * - Errores:
 *   - Lanza error si faltan dependencias requeridas.
 *   - Lanza error si no hay contrato desplegado en la dirección de TaskBoard
 *     para el provider configurado.
 */
async function listTasksByAssignee({
  taskBoardContract,
  taskContractFactory,
  assignee,
  state,
  timestampSource,
}) {
  // TODO (estudiante): implementar validaciones de entrada.
  void taskBoardContract;
  void taskContractFactory;
  void assignee;
  void state;
  void timestampSource;

  // TODO (estudiante): implementar consulta por estado, armado de contratos Task
  // y resolucion de timestamps por contrato o por eventos.
  throw new Error("listTasksByAssignee() no implementada");
}

// Punto de entrada CLI: parsea argumentos, arma contratos/factorías
// y escribe en stdout un JSON con los resultados de la consulta.
async function main() {
  // Lee y valida los argumentos recibidos por linea de comandos.
  const args = parseArgs(process.argv.slice(2));

  // Carga el artefacto (ABI + metadata) del contrato TaskBoard.
  const taskBoardArtifact = loadArtifactJson(path.join("artifacts", "contracts", "TaskBoard.sol", "TaskBoard.json"));
  // Carga el artefacto (ABI + metadata) del contrato Task.
  const taskArtifact = loadArtifactJson(path.join("artifacts", "contracts", "Task.sol", "Task.json"));

  // Crea un provider JSON-RPC usando la URI indicada (o la default).
  const provider = new ethers.JsonRpcProvider(args.rpc);
  // Construye la instancia de TaskBoard usando direccion + ABI + provider.
  const taskBoardContract = new ethers.Contract(args.board, taskBoardArtifact.abi, provider);
  // Define una factoria para construir contratos Task por direccion.
  const taskContractFactory = (taskAddress) => new ethers.Contract(taskAddress, taskArtifact.abi, provider);

  // Ejecuta la consulta principal y obtiene las tareas filtradas.
  const tasks = await listTasksByAssignee({
    // Inyecta el contrato TaskBoard ya construido.
    taskBoardContract,
    // Inyecta la factoria para construir contratos Task.
    taskContractFactory,
    // Inyecta la direccion del responsable asignado a consultar.
    assignee: args.assignee,
    // Inyecta el estado a consultar (pending/in-progress/done).
    state: args.state,
    // Inyecta la fuente de timestamps (contract/events).
    timestampSource: args.timestamps,
  });

  // Construye el objeto de salida final en formato JSON.
  const output = {
    // Incluye la URI RPC utilizada en la consulta.
    rpc: args.rpc,
    // Incluye la direccion del TaskBoard consultado.
    board: args.board,
    // Incluye la direccion del responsable asignado consultado.
    assignee: args.assignee,
    // Incluye el estado por el que se filtro la busqueda.
    state: args.state,
    // Incluye la fuente usada para calcular timestamps.
    timestampSource: args.timestamps,
    // Incluye la cantidad total de tareas devueltas.
    count: tasks.length,
    // Incluye la lista de tareas resultante.
    tasks,
  };

  // Imprime el JSON formateado (indentacion de 2 espacios) por stdout.
  console.log(JSON.stringify(output, null, 2));
}

if (process.argv[1] && path.resolve(process.argv[1]) === __filename) {
  main().catch((error) => {
    console.error(`Error: ${error.message}`);
    process.exit(1);
  });
}

export {
  listTasksByAssignee,
};
