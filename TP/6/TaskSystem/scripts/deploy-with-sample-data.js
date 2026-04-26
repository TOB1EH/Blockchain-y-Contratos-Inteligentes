import hre from "hardhat";

let ethers;

async function createAndAssignTask(taskBoard, reporter, description, assigneeAddress) {
  await taskBoard.connect(reporter).createTask(description);

  const todoIndex = (await taskBoard.todoCount()) - 1n;
  const taskAddress = await taskBoard.todo(Number(todoIndex));
  const task = await ethers.getContractAt("Task", taskAddress);

  await task.connect(reporter).assign(assigneeAddress);

  return { task, taskAddress };
}

async function main() {
  ({ ethers } = await hre.network.getOrCreate());

  const [reporter, assignee1, assignee2, assignee3] = await ethers.getSigners();

  const TaskBoard = await ethers.getContractFactory("TaskBoard");
  const taskBoard = await TaskBoard.deploy();
  await taskBoard.waitForDeployment();

  // Responsable 1: una tarea pendiente y una finalizada.
  const a1Pending = await createAndAssignTask(
    taskBoard,
    reporter,
    "[A1] Preparar plan de sprint",
    assignee1.address
  );
  const a1Done = await createAndAssignTask(
    taskBoard,
    reporter,
    "[A1] Documentar API publica",
    assignee1.address
  );
  await a1Done.task.connect(assignee1).start();
  await a1Done.task.connect(assignee1).complete();

  // Responsable 2: una tarea pendiente y una en progreso.
  const a2Pending = await createAndAssignTask(
    taskBoard,
    reporter,
    "[A2] Configurar CI",
    assignee2.address
  );
  const a2InProgress = await createAndAssignTask(
    taskBoard,
    reporter,
    "[A2] Integrar pruebas de carga",
    assignee2.address
  );
  await a2InProgress.task.connect(assignee2).start();

  // Responsable 3: una tarea en progreso y una finalizada.
  const a3InProgress = await createAndAssignTask(
    taskBoard,
    reporter,
    "[A3] Refactorizar modulo de autenticacion",
    assignee3.address
  );
  await a3InProgress.task.connect(assignee3).start();

  const a3Done = await createAndAssignTask(
    taskBoard,
    reporter,
    "[A3] Ajustar logging de auditoria",
    assignee3.address
  );
  await a3Done.task.connect(assignee3).start();
  await a3Done.task.connect(assignee3).complete();

  const taskBoardAddress = await taskBoard.getAddress();

  console.log("TaskBoard desplegado para pruebas interactivas");
  console.log(`TASKBOARD_ADDRESS=${taskBoardAddress}`);
  console.log(`ASSIGNEE_1=${assignee1.address}`);
  console.log(`ASSIGNEE_2=${assignee2.address}`);
  console.log(`ASSIGNEE_3=${assignee3.address}`);

  console.log("\nResumen de tareas creadas:");
  console.log(`- A1 pending: ${a1Pending.taskAddress}`);
  console.log(`- A1 done: ${a1Done.taskAddress}`);
  console.log(`- A2 pending: ${a2Pending.taskAddress}`);
  console.log(`- A2 in-progress: ${a2InProgress.taskAddress}`);
  console.log(`- A3 in-progress: ${a3InProgress.taskAddress}`);
  console.log(`- A3 done: ${a3Done.taskAddress}`);

  console.log("\nEjemplos de uso del script de consulta:");
  console.log(
    `npm run list-tasks -- --board ${taskBoardAddress} --assignee ${assignee1.address} --state done --timestamps contract`
  );
  console.log(
    `npm run list-tasks -- --board ${taskBoardAddress} --assignee ${assignee2.address} --state in-progress --timestamps events`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
