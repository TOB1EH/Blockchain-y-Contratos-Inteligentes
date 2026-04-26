import { expect } from "chai";

import { listTasksByAssignee } from "../scripts/list-tasks-by-assignee.js";

describe("listTasksByAssignee (unit)", function () {
  const boardAddress = "0x1000000000000000000000000000000000000001";
  const assignee = "0x2000000000000000000000000000000000000002";
  const taskAddress = "0x3000000000000000000000000000000000000003";

  function buildMocks() {
    const callLog = {
      board: {
        todoByAssignee: 0,
        inProgressByAssignee: 0,
        doneByAssignee: 0,
      },
      task: {
        description: 0,
        assignedAt: 0,
        startedAt: 0,
        completedAt: 0,
        queryFilter: 0,
      },
      provider: {
        getBlock: 0,
        getCode: 0,
      },
    };

    const provider = {
      async getBlock(blockNumber) {
        callLog.provider.getBlock += 1;

        const byNumber = {
          10: { timestamp: 1700000000 },
          11: { timestamp: 1700000100 },
          12: { timestamp: 1700000200 },
        };

        return byNumber[Number(blockNumber)] || { timestamp: 1700000000 };
      },
      async getCode(address) {
        callLog.provider.getCode += 1;

        if (address.toLowerCase() === boardAddress.toLowerCase()) {
          return "0x1234";
        }

        return "0x";
      },
    };

    const taskBoardContract = {
      runner: {
        provider,
      },
      async getAddress() {
        return boardAddress;
      },
      async todoByAssignee(receivedAssignee) {
        callLog.board.todoByAssignee += 1;
        expect(receivedAssignee).to.equal(assignee);
        return [taskAddress];
      },
      async inProgressByAssignee(receivedAssignee) {
        callLog.board.inProgressByAssignee += 1;
        expect(receivedAssignee).to.equal(assignee);
        return [taskAddress];
      },
      async doneByAssignee(receivedAssignee) {
        callLog.board.doneByAssignee += 1;
        expect(receivedAssignee).to.equal(assignee);
        return [taskAddress];
      },
    };

    const taskContract = {
      filters: {
        TaskAssigned: (reporter, receivedAssignee) => ({ name: "TaskAssigned", reporter, assignee: receivedAssignee }),
        TaskStarted: (receivedAssignee) => ({ name: "TaskStarted", assignee: receivedAssignee }),
        TaskCompleted: (receivedAssignee) => ({ name: "TaskCompleted", assignee: receivedAssignee }),
      },
      async description() {
        callLog.task.description += 1;
        return "Tarea mock";
      },
      async assignedAt() {
        callLog.task.assignedAt += 1;
        return 1700000000n;
      },
      async startedAt() {
        callLog.task.startedAt += 1;
        return 1700000100n;
      },
      async completedAt() {
        callLog.task.completedAt += 1;
        return 1700000200n;
      },
      async queryFilter(filter) {
        callLog.task.queryFilter += 1;

        if (filter.name === "TaskAssigned") {
          return [{ blockNumber: 10 }];
        }

        if (filter.name === "TaskStarted") {
          return [{ blockNumber: 11 }];
        }

        if (filter.name === "TaskCompleted") {
          return [{ blockNumber: 12 }];
        }

        return [];
      },
    };

    function taskContractFactory(address) {
      if (address.toLowerCase() === taskAddress.toLowerCase()) {
        return taskContract;
      }

      throw new Error(`Unexpected contract address: ${address}`);
    }

    return { taskBoardContract, taskContractFactory, callLog };
  }

  it("usa lecturas directas de contrato cuando timestampSource=contract", async function () {
    const { taskBoardContract, taskContractFactory, callLog } = buildMocks();

    const result = await listTasksByAssignee({
      taskBoardContract,
      taskContractFactory,
      assignee,
      state: "in-progress",
      timestampSource: "contract",
    });

    expect(result).to.have.length(1);
    expect(result[0].taskAddress).to.equal(taskAddress);
    expect(result[0].description).to.equal("Tarea mock");
    expect(result[0].timestamps).to.deep.equal({
      assignedAt: "2023-11-14T22:13:20.000Z",
      startedAt: "2023-11-14T22:15:00.000Z",
    });

    expect(callLog.board.inProgressByAssignee).to.equal(1);
    expect(callLog.board.todoByAssignee).to.equal(0);
    expect(callLog.board.doneByAssignee).to.equal(0);

    expect(callLog.task.assignedAt).to.equal(1);
    expect(callLog.task.startedAt).to.equal(1);
    expect(callLog.task.completedAt).to.equal(1);
    expect(callLog.task.queryFilter).to.equal(0);
    expect(callLog.provider.getBlock).to.equal(0);
  });

  it("usa análisis de eventos cuando timestampSource=events", async function () {
    const { taskBoardContract, taskContractFactory, callLog } = buildMocks();

    const result = await listTasksByAssignee({
      taskBoardContract,
      taskContractFactory,
      assignee,
      state: "done",
      timestampSource: "events",
    });

    expect(result).to.have.length(1);
    expect(result[0].taskAddress).to.equal(taskAddress);
    expect(result[0].description).to.equal("Tarea mock");
    expect(result[0].timestamps).to.deep.equal({
      assignedAt: "2023-11-14T22:13:20.000Z",
      startedAt: "2023-11-14T22:15:00.000Z",
      completedAt: "2023-11-14T22:16:40.000Z",
    });

    expect(callLog.board.doneByAssignee).to.equal(1);
    expect(callLog.board.todoByAssignee).to.equal(0);
    expect(callLog.board.inProgressByAssignee).to.equal(0);

    expect(callLog.task.queryFilter).to.equal(3);
    expect(callLog.provider.getBlock).to.equal(3);
    expect(callLog.task.assignedAt).to.equal(0);
    expect(callLog.task.startedAt).to.equal(0);
    expect(callLog.task.completedAt).to.equal(0);
  });

  it("usa el método de estado pending y devuelve solo assignedAt", async function () {
    const { taskBoardContract, taskContractFactory, callLog } = buildMocks();

    const result = await listTasksByAssignee({
      taskBoardContract,
      taskContractFactory,
      assignee,
      state: "pending",
      timestampSource: "contract",
    });

    expect(callLog.board.todoByAssignee).to.equal(1);
    expect(callLog.board.inProgressByAssignee).to.equal(0);
    expect(callLog.board.doneByAssignee).to.equal(0);

    expect(result[0].timestamps).to.deep.equal({
      assignedAt: "2023-11-14T22:13:20.000Z",
    });
  });
});
