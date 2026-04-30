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
  // Obtener las direcciones de tareas segun el estado pedido (pending/in-progress/done) desde el contrato TaskBoard.
  let taskAddresses; // Array de direcciones de tareas a consultar, inicialmente vacio.
  if (state === "pending") {
    taskAddresses = await taskBoardContract.todoByAssignee(assignee);
  } else if (state === "in-progress") {
    taskAddresses = await taskBoardContract.inProgressByAssignee(assignee);
  } else if (state === "done") {
    taskAddresses = await taskBoardContract.doneByAssignee(assignee);
  }

  // Como el provider viene del TaskBoard y no de cada Task individual, se obtiene el provider del contrato TaskBoard
  // para usarlo en las funciones auxiliares que resuelven timestamps desde eventos.
  const provider = taskBoardContract.runner.provider;

  // Para cada dirección de tarea, construir su contrato ethers usando la factoria, y obtener sus datos
  // relevantes (descripción y timestamps) usando las funciones del contrato y la función auxiliar resolveTimestamps.
  // Se usa Promise.all para ejecutar las consultas en paralelo y esperar a que todas terminen antes de continuar.
  const results = await Promise.all(
    taskAddresses.map(async (taskAddress) => {
      const task = taskContractFactory(taskAddress); // Construir contrato Task para la dirección dada.
      const description = await task.description(); // Obtener la descripción de la tarea desde el contrato Task.
      const timestamps = await resolveTimestamps(task, state, timestampSource, provider); // Obtener los timestamps relevantes de la tarea usando la función auxiliar, según la fuente indicada.
      return { taskAddress, description, timestamps }; // Devolver un objeto con la dirección de la tarea, su descripción y los timestamps obtenidos.
    })
  );

  return results;
}

/* FUNCIONES AUXILIARES */

/**
 *  Función auxiliar para resolver los timestamps relevantes de una tarea según la fuente indicada (contract o events).
 *  - Si timestampSource es "contract", obtiene los timestamps directamente desde las funciones del contrato Task.
 *  - Si timestampSource es "events", obtiene los timestamps a partir de los eventos emitidos por el contrato Task.
 *  - Devuelve un objeto con los timestamps relevantes para la tarea (por ejemplo: { createdAt, startedAt, completedAt }).
 *  - Lanza error si timestampSource no es válido o si ocurre algún problema al obtener los datos.
 */
async function resolveTimestamps(task, state, timestampSource, provider) {
  if (timestampSource === "contract") {
    return resolveTimestampsFromContract(task, state, provider);
  } else {
    return resolveTimestampsFromEvents(task, state, provider);
  }
}

/**
 *  Función auxiliar para resolver los timestamps relevantes de una tarea según la fuente indicada (contract o events).
 * - Obtiene los timestamps directamente desde las funciones del contrato Task.
 * - Devuelve un objeto con los timestamps relevantes para la tarea (por ejemplo: { createdAt, startedAt, completedAt }).
 * - Lanza error si ocurre algún problema al obtener los datos.
 */
async function resolveTimestampsFromContract(task, state, provider) {
  // Siempre se leen los tres, pero solo se incluyen los que correspondan al estado pedido (pending/in-progress/done) en el objeto final.
  const assignedAt = await task.assignedAt();
  const startedAt  = await task.startedAt();
  const completedAt = await task.completedAt();

  // Convertir los timestamps a formato ISO usando toISOString
  const timestamps = {
    assignedAt: toISOString(assignedAt),
  };

  if (state === "in-progress" || state === "done") {
    timestamps.startedAt = toISOString(startedAt);
  }

  if (state === "done") {
    timestamps.completedAt = toISOString(completedAt);
  }

  return timestamps;
}

/**
 *  Función auxiliar para resolver los timestamps relevantes de una tarea según la fuente indicada (contract o events).
 * - Obtiene los timestamps a partir de los eventos emitidos por el contrato Task.
 * - Para cada evento relevante (TaskAssigned, TaskStarted, TaskCompleted), obtiene el bloque en el que se emitió y extrae su timestamp.
 * - Devuelve un objeto con los timestamps relevantes para la tarea (por ejemplo: { createdAt, startedAt, completedAt }).
 * - Lanza error si ocurre algún problema al obtener los datos.
 */
async function resolveTimestampsFromEvents(task, state, provider) {
  // Obtener el bloque del evento TaskAssigned y extraer su timestamp
  const assignedEvents = await task.queryFilter(task.filters.TaskAssigned(null, null));
  // Validar que existe el evento antes de acceder a él
  if (!assignedEvents || assignedEvents.length === 0) {
    throw new Error("No TaskAssigned event found for this task");
  }
  const assignedBlock  = await provider.getBlock(assignedEvents[0].blockNumber);
  const timestamps = {
    assignedAt: toISOString(assignedBlock.timestamp),
  };

  if (state === "in-progress" || state === "done") {
    // Obtener el bloque del evento TaskStarted y extraer su timestamp
    const startedEvents = await task.queryFilter(task.filters.TaskStarted(null));
    if (!startedEvents || startedEvents.length === 0) {
      throw new Error("No TaskStarted event found for this task");
    }
    const startedBlock  = await provider.getBlock(startedEvents[0].blockNumber);
    // Convertir el timestamp del bloque a formato ISO usando toISOString
    timestamps.startedAt = toISOString(startedBlock.timestamp);
  }

  if (state === "done") {
    // Obtener el bloque del evento TaskCompleted y extraer su timestamp
    const completedEvents = await task.queryFilter(task.filters.TaskCompleted(null));
    if (!completedEvents || completedEvents.length === 0) {
      throw new Error("No TaskCompleted event found for this task");
    }
    const completedBlock  = await provider.getBlock(completedEvents[0].blockNumber);
    timestamps.completedAt = toISOString(completedBlock.timestamp);
  }

  return timestamps;
}

/**
 * Función auxiliar para convertir un timestamp (en formato UNIX, ya sea number o BigInt) a formato ISO (string).
 * - Recibe un timestamp en formato UNIX (segundos desde epoch) que puede ser un number o un BigInt.
 * - Convierte el timestamp a milisegundos multiplicándolo por 1000, y luego lo convierte a una fecha usando new Date().
 * - Devuelve la fecha en formato ISO usando toISOString().
 * - Lanza error si el timestamp no es un número válido o si ocurre algún problema durante la conversión.
 */
function toISOString(timestamp) {
  // timestamp puede ser un BigInt (viene del contrato) o un number (viene del bloque)
  return new Date(Number(timestamp) * 1000).toISOString();
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
