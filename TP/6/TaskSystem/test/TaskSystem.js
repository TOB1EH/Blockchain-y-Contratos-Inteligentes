import { expect } from "chai";
import { anyValue } from "@nomicfoundation/hardhat-ethers-chai-matchers/withArgs";
import hre from "hardhat";

let ethers;

before(async function () {
  ({ ethers } = await hre.network.getOrCreate());
});

async function loadFixture(fixture) {
  const { networkHelpers } = await hre.network.getOrCreate();
  return networkHelpers.loadFixture(fixture);
}

describe("Sistema Descentralizado de Gestión de Tareas", function () {
  
  // Utilizamos un fixture para desplegar el contrato una sola vez y reiniciar el estado en cada prueba
  async function deployTaskSystemFixture() {
    const [reporter, assignee, unauthorized] = await ethers.getSigners();

    // Desplegamos el tablero principal
    const TaskBoard = await ethers.getContractFactory("TaskBoard");
    const taskBoard = await TaskBoard.deploy();

    return { taskBoard, reporter, assignee, unauthorized };
  }

  describe("Despliegue y Creación de Tareas", function () {
    it("Debería crear una tarea y registrarla en estado ToDo", async function () {
      const { taskBoard, reporter } = await loadFixture(deployTaskSystemFixture);
      
      const description = "Diseñar la base de datos";
      
      // El reporter crea la tarea
      await taskBoard.connect(reporter).createTask(description);
      
      // Verificamos que se haya agregado a la lista ToDo
      const taskAddress = await taskBoard.todo(0);
      expect(taskAddress).to.not.equal(ethers.ZeroAddress);
    });

    it("La tarea creada debe tener la descripción y el reporter correctos", async function () {
      const { taskBoard, reporter } = await loadFixture(deployTaskSystemFixture);
      
      await taskBoard.connect(reporter).createTask("Aprender Solidity");
      const taskAddress = await taskBoard.todo(0);
      
      // Instanciamos el contrato Task creado usando la interfaz de Ethers
      const Task = await ethers.getContractAt("Task", taskAddress);
      
      expect(await Task.description()).to.equal("Aprender Solidity");
      expect(await Task.reporter()).to.equal(reporter.address);
      expect(await Task.started()).to.be.false;
      expect(await Task.completed()).to.be.false;
    });
  });

  describe("Asignación de Tareas", function () {
    it("El reporter debería poder asignar la tarea a un trabajador", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);
      
      await taskBoard.connect(reporter).createTask("Configurar servidor");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      expect(await task.assignee()).to.equal(assignee.address);
    });

    it("Debería revertir si alguien que no es el reporter intenta asignar la tarea", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);
      
      await taskBoard.connect(reporter).createTask("Configurar servidor");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      // Usamos el modifier onlyReporter, por lo que debe revertir
      await expect(
        task.connect(unauthorized).assign(assignee.address)
      ).to.be.rejected;
    });

    it("Debería revertir con el mensaje correcto si alguien que no es el reporter intenta asignar la tarea", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Configurar servidor");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await expect(
        task.connect(unauthorized).assign(assignee.address)
      ).to.be.revertedWith("Solo el reporter puede realizar esta accion");
    });

    it("Debería revertir si el reporter intenta reasignar una tarea que ya comenzó", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Configurar servidor");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();

      await expect(
        task.connect(reporter).assign(unauthorized.address)
      ).to.be.revertedWith("La tarea ya ha comenzado");
    });
  });

  describe("Flujo de Estado: Start y Complete", function () {
    it("El assignee debería poder iniciar la tarea y actualizar el tablero", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);
      
      await taskBoard.connect(reporter).createTask("Escribir tests");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      
      // El assignee inicia la tarea
      await task.connect(assignee).start();

      expect(await task.started()).to.be.true;

      // Verificamos que el TaskBoard movió la tarea al arreglo inProgress
      // Dependiendo de cómo implementen el deleteEntry, el arreglo todo podría estar vacío o tener la dirección en el índice 0 reemplazada.
      // Aquí verificamos directamente que esté en inProgress.
      const inProgressTask = await taskBoard.inProgress(0);
      expect(inProgressTask).to.equal(taskAddress);
    });

    it("Debería revertir si se intenta iniciar una tarea ya iniciada (isPending)", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);
      
      await taskBoard.connect(reporter).createTask("Escribir tests");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();

      // Intentar iniciar de nuevo debe fallar
      await expect(
        task.connect(assignee).start()
      ).to.be.rejected;
    });

    it("Debería revertir con el mensaje correcto si alguien que no es el assignee intenta iniciar la tarea", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Escribir tests");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);

      await expect(
        task.connect(unauthorized).start()
      ).to.be.revertedWith("Solo el assignee puede realizar esta accion");
    });

    it("Debería revertir si se intenta iniciar una tarea sin assignee asignado", async function () {
      const { taskBoard, reporter, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Escribir tests");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await expect(
        task.connect(unauthorized).start()
      ).to.be.revertedWith("Solo el assignee puede realizar esta accion");
    });

    it("El assignee debería poder completar la tarea y actualizar el tablero", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);
      
      await taskBoard.connect(reporter).createTask("Auditar contrato");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();
      
      // El assignee completa la tarea
      await task.connect(assignee).complete();

      expect(await task.completed()).to.be.true;

      // Verificamos que el TaskBoard movió la tarea al arreglo done
      const doneTask = await taskBoard.done(0);
      expect(doneTask).to.equal(taskAddress);
    });

    it("Debería revertir si se intenta completar una tarea sin haberla iniciado (inProgress)", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);
      
      await taskBoard.connect(reporter).createTask("Auditar contrato");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      
      // Intentar completar directamente debe fallar
      await expect(
        task.connect(assignee).complete()
      ).to.be.rejected;
    });

    it("Debería revertir con el mensaje correcto si alguien que no es el assignee intenta completar la tarea", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Auditar contrato");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();

      await expect(
        task.connect(unauthorized).complete()
      ).to.be.revertedWith("Solo el assignee puede realizar esta accion");
    });

    it("Debería revertir si se intenta completar una tarea ya finalizada", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Auditar contrato");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();
      await task.connect(assignee).complete();

      await expect(
        task.connect(assignee).complete()
      ).to.be.revertedWith("La tarea no esta en progreso");
    });

    it("Debería mantener registradas las otras tareas al mover una tarea a inProgress y luego a done", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Primera tarea");
      await taskBoard.connect(reporter).createTask("Segunda tarea");

      const firstTaskAddress = await taskBoard.todo(0);
      const secondTaskAddress = await taskBoard.todo(1);

      const firstTask = await ethers.getContractAt("Task", firstTaskAddress);
      const secondTask = await ethers.getContractAt("Task", secondTaskAddress);

      await firstTask.connect(reporter).assign(assignee.address);
      await secondTask.connect(reporter).assign(unauthorized.address);

      await firstTask.connect(assignee).start();

      expect(await taskBoard.inProgress(0)).to.equal(firstTaskAddress);
      expect(await taskBoard.todo(0)).to.equal(secondTaskAddress);

      await firstTask.connect(assignee).complete();

      expect(await taskBoard.done(0)).to.equal(firstTaskAddress);
      expect(await taskBoard.todo(0)).to.equal(secondTaskAddress);
    });
  });

  describe("Seguridad del Registro", function () {
    it("Debería impedir que una cuenta cualquiera llame a las funciones del registro directamente", async function () {
      const { taskBoard, unauthorized } = await loadFixture(deployTaskSystemFixture);
      
      // Un usuario que no es una tarea creada por la factoría intenta modificar el estado
      await expect(
        taskBoard.connect(unauthorized).taskStarted()
      ).to.be.rejected;

      await expect(
        taskBoard.connect(unauthorized).taskCompleted()
      ).to.be.rejected;
    });

    it("Debería impedir completar directamente desde el registro una tarea que aún está en ToDo", async function () {
      const { taskBoard, reporter } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Pendiente");
      const taskAddress = await taskBoard.todo(0);
      await ethers.provider.send("hardhat_setBalance", [
        taskAddress,
        "0x1000000000000000000",
      ]);
      await ethers.provider.send("hardhat_impersonateAccount", [taskAddress]);
      const taskSigner = await ethers.getSigner(taskAddress);

      await expect(
        taskBoard.connect(taskSigner).taskCompleted()
      ).to.be.revertedWith("La tarea no esta en progreso");

      await ethers.provider.send("hardhat_stopImpersonatingAccount", [taskAddress]);
    });

    it("Debería impedir iniciar directamente desde el registro una tarea ya en InProgress", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("En progreso");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();

      await ethers.provider.send("hardhat_setBalance", [
        taskAddress,
        "0x1000000000000000000",
      ]);
      await ethers.provider.send("hardhat_impersonateAccount", [taskAddress]);
      const taskSigner = await ethers.getSigner(taskAddress);

      await expect(
        taskBoard.connect(taskSigner).taskStarted()
      ).to.be.revertedWith("La tarea ya esta en progreso");

      await ethers.provider.send("hardhat_stopImpersonatingAccount", [taskAddress]);
    });

    it("Debería impedir iniciar directamente desde el registro una tarea ya finalizada", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Finalizada");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();
      await task.connect(assignee).complete();

      await ethers.provider.send("hardhat_setBalance", [
        taskAddress,
        "0x1000000000000000000",
      ]);
      await ethers.provider.send("hardhat_impersonateAccount", [taskAddress]);
      const taskSigner = await ethers.getSigner(taskAddress);

      await expect(
        taskBoard.connect(taskSigner).taskStarted()
      ).to.be.revertedWith("La tarea ya fue completada");

      await ethers.provider.send("hardhat_stopImpersonatingAccount", [taskAddress]);
    });

    it("Debería impedir completar directamente desde el registro una tarea ya finalizada", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Finalizada dos veces");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();
      await task.connect(assignee).complete();

      await ethers.provider.send("hardhat_setBalance", [
        taskAddress,
        "0x1000000000000000000",
      ]);
      await ethers.provider.send("hardhat_impersonateAccount", [taskAddress]);
      const taskSigner = await ethers.getSigner(taskAddress);

      await expect(
        taskBoard.connect(taskSigner).taskCompleted()
      ).to.be.revertedWith("La tarea ya fue completada");

      await ethers.provider.send("hardhat_stopImpersonatingAccount", [taskAddress]);
    });
  });

  describe("Invariantes del Tablero", function () {
    it("Debería registrar status ToDo e índices consecutivos al crear múltiples tareas", async function () {
      const { taskBoard, reporter } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Tarea A");
      await taskBoard.connect(reporter).createTask("Tarea B");
      await taskBoard.connect(reporter).createTask("Tarea C");

      const taskA = await taskBoard.todo(0);
      const taskB = await taskBoard.todo(1);
      const taskC = await taskBoard.todo(2);

      const infoA = await taskBoard.tasks(taskA);
      const infoB = await taskBoard.tasks(taskB);
      const infoC = await taskBoard.tasks(taskC);

      expect(infoA.status).to.equal(1n);
      expect(infoA.index).to.equal(0n);
      expect(infoB.status).to.equal(1n);
      expect(infoB.index).to.equal(1n);
      expect(infoC.status).to.equal(1n);
      expect(infoC.index).to.equal(2n);
    });

    it("Debería actualizar índices correctamente en ToDo cuando se mueve una tarea a InProgress", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Tarea A");
      await taskBoard.connect(reporter).createTask("Tarea B");
      await taskBoard.connect(reporter).createTask("Tarea C");

      const taskAAddress = await taskBoard.todo(0);
      const taskBAddress = await taskBoard.todo(1);
      const taskCAddress = await taskBoard.todo(2);

      const taskA = await ethers.getContractAt("Task", taskAAddress);
      const taskB = await ethers.getContractAt("Task", taskBAddress);
      const taskC = await ethers.getContractAt("Task", taskCAddress);

      await taskA.connect(reporter).assign(assignee.address);
      await taskB.connect(reporter).assign(unauthorized.address);
      await taskC.connect(reporter).assign(reporter.address);

      await taskA.connect(assignee).start();

      const movedToIndex0 = await taskBoard.todo(0);
      const remainingAtIndex1 = await taskBoard.todo(1);

      expect(movedToIndex0).to.equal(taskCAddress);
      expect(remainingAtIndex1).to.equal(taskBAddress);

      const infoA = await taskBoard.tasks(taskAAddress);
      const infoB = await taskBoard.tasks(taskBAddress);
      const infoC = await taskBoard.tasks(taskCAddress);

      expect(infoA.status).to.equal(2n);
      expect(infoA.index).to.equal(0n);
      expect(infoB.status).to.equal(1n);
      expect(infoB.index).to.equal(1n);
      expect(infoC.status).to.equal(1n);
      expect(infoC.index).to.equal(0n);
    });

    it("Debería registrar status Done y conservar consistencia de índices al completar", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Tarea A");
      await taskBoard.connect(reporter).createTask("Tarea B");

      const taskAAddress = await taskBoard.todo(0);
      const taskBAddress = await taskBoard.todo(1);

      const taskA = await ethers.getContractAt("Task", taskAAddress);
      const taskB = await ethers.getContractAt("Task", taskBAddress);

      await taskA.connect(reporter).assign(assignee.address);
      await taskB.connect(reporter).assign(assignee.address);

      await taskA.connect(assignee).start();
      await taskB.connect(assignee).start();
      await taskA.connect(assignee).complete();

      const infoA = await taskBoard.tasks(taskAAddress);
      const infoB = await taskBoard.tasks(taskBAddress);

      expect(infoA.status).to.equal(3n);
      expect(infoA.index).to.equal(0n);
      expect(await taskBoard.done(0)).to.equal(taskAAddress);

      expect(infoB.status).to.equal(2n);
      expect(infoB.index).to.equal(0n);
      expect(await taskBoard.inProgress(0)).to.equal(taskBAddress);
    });
  });

  describe("Conteos de Listas", function () {
    it("Debería reflejar los conteos al crear tareas", async function () {
      const { taskBoard, reporter } = await loadFixture(deployTaskSystemFixture);

      expect(await taskBoard.todoCount()).to.equal(0n);
      expect(await taskBoard.inProgressCount()).to.equal(0n);
      expect(await taskBoard.doneCount()).to.equal(0n);

      await taskBoard.connect(reporter).createTask("Tarea 1");
      await taskBoard.connect(reporter).createTask("Tarea 2");

      expect(await taskBoard.todoCount()).to.equal(2n);
      expect(await taskBoard.inProgressCount()).to.equal(0n);
      expect(await taskBoard.doneCount()).to.equal(0n);
    });

    it("Debería actualizar conteos al mover de ToDo a InProgress", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Mover a progreso");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();

      expect(await taskBoard.todoCount()).to.equal(0n);
      expect(await taskBoard.inProgressCount()).to.equal(1n);
      expect(await taskBoard.doneCount()).to.equal(0n);
    });

    it("Debería actualizar conteos al mover de InProgress a Done", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Mover a done");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();
      await task.connect(assignee).complete();

      expect(await taskBoard.todoCount()).to.equal(0n);
      expect(await taskBoard.inProgressCount()).to.equal(0n);
      expect(await taskBoard.doneCount()).to.equal(1n);
    });
  });

  describe("Listas por Responsable Asignado", function () {
    it("Debería devolver tareas ToDo filtradas por responsable asignado", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("T1");
      await taskBoard.connect(reporter).createTask("T2");
      await taskBoard.connect(reporter).createTask("T3");
      await taskBoard.connect(reporter).createTask("T4 sin asignar");

      const t1 = await taskBoard.todo(0);
      const t2 = await taskBoard.todo(1);
      const t3 = await taskBoard.todo(2);
      const t4 = await taskBoard.todo(3);

      const task1 = await ethers.getContractAt("Task", t1);
      const task2 = await ethers.getContractAt("Task", t2);
      const task3 = await ethers.getContractAt("Task", t3);
      const task4 = await ethers.getContractAt("Task", t4);

      await task1.connect(reporter).assign(assignee.address);
      await task2.connect(reporter).assign(unauthorized.address);
      await task3.connect(reporter).assign(assignee.address);

      const todoAssignee = await taskBoard.todoByAssignee(assignee.address);
      const todoUnauthorized = await taskBoard.todoByAssignee(unauthorized.address);
      const todoReporter = await taskBoard.todoByAssignee(reporter.address);

      expect(todoAssignee.length).to.equal(2);
      expect(todoAssignee[0]).to.equal(t1);
      expect(todoAssignee[1]).to.equal(t3);

      expect(todoUnauthorized.length).to.equal(1);
      expect(todoUnauthorized[0]).to.equal(t2);

      expect(todoReporter.length).to.equal(0);
      expect(await task4.assignee()).to.equal(ethers.ZeroAddress);
    });

    it("Debería mover una tarea entre listas filtradas del mismo responsable", async function () {
      const { taskBoard, reporter, assignee, unauthorized } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("A");
      await taskBoard.connect(reporter).createTask("B");

      const taskAAddress = await taskBoard.todo(0);
      const taskBAddress = await taskBoard.todo(1);

      const taskA = await ethers.getContractAt("Task", taskAAddress);
      const taskB = await ethers.getContractAt("Task", taskBAddress);

      await taskA.connect(reporter).assign(assignee.address);
      await taskB.connect(reporter).assign(unauthorized.address);

      await taskA.connect(assignee).start();

      const todoAssignee = await taskBoard.todoByAssignee(assignee.address);
      const inProgressAssignee = await taskBoard.inProgressByAssignee(assignee.address);

      expect(todoAssignee.length).to.equal(0);
      expect(inProgressAssignee.length).to.equal(1);
      expect(inProgressAssignee[0]).to.equal(taskAAddress);

      await taskA.connect(assignee).complete();

      const doneAssignee = await taskBoard.doneByAssignee(assignee.address);
      const inProgressAfterDone = await taskBoard.inProgressByAssignee(assignee.address);

      expect(doneAssignee.length).to.equal(1);
      expect(doneAssignee[0]).to.equal(taskAAddress);
      expect(inProgressAfterDone.length).to.equal(0);
    });
  });

  describe("Timestamps y Estado Derivado", function () {
    it("Debería iniciar con timestamps en cero y estado no iniciado/no completado", async function () {
      const { taskBoard, reporter } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Tarea con tiempos");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      expect(await task.assignedAt()).to.equal(0n);
      expect(await task.startedAt()).to.equal(0n);
      expect(await task.completedAt()).to.equal(0n);
      expect(await task.started()).to.be.false;
      expect(await task.completed()).to.be.false;
    });

    it("Debería registrar assignedAt al asignar y mantener startedAt/completedAt en cero", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Asignacion con timestamp");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      const assignTx = await task.connect(reporter).assign(assignee.address);
      const assignReceipt = await assignTx.wait();
      const assignBlock = await ethers.provider.getBlock(assignReceipt.blockNumber);

      expect(await task.assignedAt()).to.equal(BigInt(assignBlock.timestamp));
      expect(await task.startedAt()).to.equal(0n);
      expect(await task.completedAt()).to.equal(0n);
      expect(await task.started()).to.be.false;
      expect(await task.completed()).to.be.false;
    });

    it("Debería registrar startedAt al iniciar y reflejar started() en true", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Inicio con timestamp");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);

      const startTx = await task.connect(assignee).start();
      const startReceipt = await startTx.wait();
      const startBlock = await ethers.provider.getBlock(startReceipt.blockNumber);

      expect(await task.startedAt()).to.equal(BigInt(startBlock.timestamp));
      expect(await task.completedAt()).to.equal(0n);
      expect(await task.started()).to.be.true;
      expect(await task.completed()).to.be.false;
    });

    it("Debería registrar completedAt al completar y mantener coherencia temporal", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Fin con timestamp");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();

      const startedAt = await task.startedAt();

      const completeTx = await task.connect(assignee).complete();
      const completeReceipt = await completeTx.wait();
      const completeBlock = await ethers.provider.getBlock(completeReceipt.blockNumber);

      const completedAt = await task.completedAt();

      expect(completedAt).to.equal(BigInt(completeBlock.timestamp));
      expect(completedAt).to.be.greaterThanOrEqual(startedAt);
      expect(await task.started()).to.be.true;
      expect(await task.completed()).to.be.true;
    });
  });

  describe("Eventos", function () {
    it("Debería emitir TaskCreated al crear una tarea", async function () {
      const { taskBoard, reporter } = await loadFixture(deployTaskSystemFixture);

      const description = "Implementar API";

      const tx = taskBoard.connect(reporter).createTask(description);

      await expect(tx)
        .to.emit(taskBoard, "TaskCreated")
        .withArgs(anyValue, reporter.address, description);
    });

    it("Debería emitir TaskAssigned al asignar una tarea", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Configurar CI");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await expect(task.connect(reporter).assign(assignee.address))
        .to.emit(task, "TaskAssigned")
        .withArgs(reporter.address, assignee.address, anyValue);
    });

    it("Debería emitir eventos de Task y TaskBoard al iniciar una tarea", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Revisar seguridad");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);

      await expect(task.connect(assignee).start())
        .to.emit(task, "TaskStarted")
        .withArgs(assignee.address, anyValue)
        .and.to.emit(taskBoard, "TaskMovedToInProgress")
        .withArgs(taskAddress, 0);
    });

    it("Debería emitir eventos de Task y TaskBoard al completar una tarea", async function () {
      const { taskBoard, reporter, assignee } = await loadFixture(deployTaskSystemFixture);

      await taskBoard.connect(reporter).createTask("Documentar modulo");
      const taskAddress = await taskBoard.todo(0);
      const task = await ethers.getContractAt("Task", taskAddress);

      await task.connect(reporter).assign(assignee.address);
      await task.connect(assignee).start();

      await expect(task.connect(assignee).complete())
        .to.emit(task, "TaskCompleted")
        .withArgs(assignee.address, anyValue)
        .and.to.emit(taskBoard, "TaskMovedToDone")
        .withArgs(taskAddress, 0);
    });
  });
});
