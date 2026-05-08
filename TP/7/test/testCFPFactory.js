import { expect } from "chai";
import hre from "hardhat";
import { HashGenerator } from "./shared.js";

let ethers;
let accounts;

before(async function () {
  ({ ethers } = await hre.network.getOrCreate());
  accounts = await ethers.getSigners();
});

const gen = new HashGenerator();

describe("CFP Factory", function () {
  describe("Inicialización del contrato", function () {
    let factory;

    before(async function () {
      const Factory = await ethers.getContractFactory("CFPFactory");
      factory = await Factory.deploy();
    });

    it("debe tener el dueño correcto", async () => {
      expect(await factory.owner()).to.equal(accounts[0].address);
    });

    it("no debe haber creadores predefinidos", async () => {
      expect(await factory.creatorsCount()).to.equal(0n);
      await expect(factory.creators(0)).to.be.rejected;
    });
  });

  describe("Gestión de llamados", function () {
    let factory;
    const cfps = [];
    let closingTime;
    const callIds = [];
    let pending = 0;

    before(async function () {
      const Factory = await ethers.getContractFactory("CFPFactory");
      factory = await Factory.deploy();
    });

    it("debe permitir el registro de creadores", async () => {
      for (let i = 0; i < accounts.length; i += 2) {
        await factory.connect(accounts[i]).register();
        pending++;
      }
    });

    it("debe identificar correctamente el estado de los registrados", async () => {
      for (let i = 0; i < accounts.length; i++) {
        expect(await factory.isRegistered(accounts[i].address)).to.equal(
          i % 2 === 0
        );
        expect(await factory.isAuthorized(accounts[i].address)).to.equal(false);
      }
    });

    it("debe devolver la cantidad de registros pendientes", async () => {
      expect(await factory.pendingCount()).to.equal(BigInt(pending));
    });

    it("debe devolver la cantidad de registros pendientes solo al dueño", async () => {
      await expect(
        factory.connect(accounts[1]).pendingCount()
      ).to.be.revertedWith("Solo el creador puede hacer esta llamada");
    });

    it("debe devolver la lista de pendientes correcta", async () => {
      const p = await factory.getAllPending();
      expect(p.length).to.equal(pending);
      for (let i = 0; i < accounts.length; i += 2) {
        expect(p).to.include(accounts[i].address);
      }
    });

    it("debe devolver correctamente los pendientes", async () => {
      const p = [];
      for (let i = 0; i < pending; i++) {
        p.push(await factory.getPending(i));
      }
      for (let i = 0; i < accounts.length; i += 2) {
        expect(p).to.include(accounts[i].address);
      }
      await expect(factory.getPending(pending)).to.be.rejected;
    });

    it("debe devolver los pendientes solo al dueño", async () => {
      await expect(
        factory.connect(accounts[1]).getAllPending()
      ).to.be.revertedWith("Solo el creador puede hacer esta llamada");
      await expect(
        factory.connect(accounts[1]).getPending(0)
      ).to.be.revertedWith("Solo el creador puede hacer esta llamada");
    });

    it("debe rechazar la creación de llamados por cuentas no autorizadas", async () => {
      const latestBlock = await ethers.provider.getBlock("latest");
      closingTime = latestBlock.timestamp + 1000;
      for (let i = 0; i < accounts.length; i++) {
        const callId = gen.get(i);
        await expect(
          factory
            .connect(accounts[i])
            .create(callId, BigInt(closingTime + i))
        ).to.be.revertedWith("No autorizado");
      }
    });

    it("debe rechazar la creación de llamados por parte del dueño para cuentas no autorizadas", async () => {
      for (let i = 0; i < accounts.length; i++) {
        const callId = gen.get(i);
        await expect(
          factory.createFor(callId, BigInt(closingTime + i), accounts[i].address)
        ).to.be.revertedWith("No autorizado");
      }
    });

    it("debe permitir al dueño autorizar creadores", async () => {
      for (const account of accounts) {
        await factory.authorize(account.address);
      }
    });

    it("debe actualizar correctamente la lista de pendientes", async () => {
      const p = await factory.getAllPending();
      expect(p.length).to.equal(0);
      expect(await factory.pendingCount()).to.equal(0n);
    });

    it("debe permitir desautorizar solo al dueño", async () => {
      await expect(
        factory.connect(accounts[1]).unauthorize(accounts[0].address)
      ).to.be.revertedWith("Solo el creador puede hacer esta llamada");
    });

    it("debe permitir desautorizar al dueño", async () => {
      await factory.unauthorize(accounts[accounts.length - 1].address);
    });

    it("debe identificar correctamente el estado de los autorizados", async () => {
      for (let i = 0; i < accounts.length; i++) {
        expect(await factory.isRegistered(accounts[i].address)).to.equal(
          i !== accounts.length - 1
        );
        expect(await factory.isAuthorized(accounts[i].address)).to.equal(
          i !== accounts.length - 1
        );
      }
    });

    it("debe permitir reautorizar", async () => {
      await factory.authorize(accounts[accounts.length - 1].address);
    });

    it("debe permitir la creación de llamados", async () => {
      const latestBlock = await ethers.provider.getBlock("latest");
      closingTime = latestBlock.timestamp + 1000;
      for (let i = 0; i < accounts.length; i++) {
        const callId = gen.get(i);
        callIds.push(callId);
        await factory
          .connect(accounts[i])
          .create(callId, BigInt(closingTime + i));
      }
    });

    it("debe permitir al dueño la creación de llamados a nombre de otro", async () => {
      for (let i = 0; i < accounts.length; i++) {
        const callId = gen.get(accounts.length + i);
        callIds.push(callId);
        await factory.createFor(
          callId,
          BigInt(closingTime + accounts.length + i),
          accounts[i].address
        );
      }
      gen.set(2 * accounts.length);
    });

    it("deber rechazar el llamado a createFor por usuarios que no son el dueño", async () => {
      await expect(
        factory
          .connect(accounts[1])
          .createFor(gen.next(), BigInt(closingTime), accounts[1].address)
      ).to.be.revertedWith("Solo el creador puede hacer esta llamada");
    });

    it("debe rechazar la creación de llamados con el mismo callId", async () => {
      await expect(
        factory.create(callIds[0], BigInt(closingTime))
      ).to.be.revertedWith("El llamado ya existe");
    });

    it("debe rechazar la creación de llamados por parte del dueño con el mismo callId", async () => {
      await expect(
        factory.createFor(callIds[0], BigInt(closingTime), accounts[1].address)
      ).to.be.revertedWith("El llamado ya existe");
    });

    it("debe devolver la cantidad correcta de creadores", async () => {
      expect(await factory.creatorsCount()).to.equal(BigInt(accounts.length));
    });

    it("debe devolver la cantidad correcta de llamados por creador", async () => {
      for (const account of accounts) {
        expect(await factory.createdByCount(account.address)).to.equal(2n);
      }
    });

    it("debe devolver el callId correcto para cada creador", async () => {
      for (let i = 0; i < accounts.length; i++) {
        expect(await factory.createdBy(accounts[i].address, 0)).to.equal(
          callIds[i]
        );
        expect(await factory.createdBy(accounts[i].address, 1)).to.equal(
          callIds[accounts.length + i]
        );
      }
    });

    it("debe devolver el creador correcto para cada llamado", async () => {
      for (let i = 0; i < callIds.length; i++) {
        const cfpData = await factory.calls(callIds[i]);
        expect(cfpData.creator).to.equal(
          accounts[i % accounts.length].address
        );
      }
    });

    it("debe devolver direcciones de contrato válidas", async () => {
      for (const callId of callIds) {
        const cfpData = await factory.calls(callId);
        const cfp = await ethers.getContractAt("CFP", cfpData.cfp);
        cfps.push(cfp);
      }
    });

    it("los contratos deben tener el creador correcto", async () => {
      const factoryAddress = await factory.getAddress();
      for (const cfp of cfps) {
        expect(await cfp.creator()).to.equal(factoryAddress);
      }
    });

    it("los contratos deben tener el callId correcto", async () => {
      for (let i = 0; i < cfps.length; i++) {
        expect(await cfps[i].callId()).to.equal(callIds[i]);
      }
    });

    it("los contratos deben tener el tiempo de cierre correcto", async () => {
      for (let i = 0; i < cfps.length; i++) {
        expect(await cfps[i].closingTime()).to.equal(
          BigInt(closingTime + i)
        );
      }
    });

    it("los contratos deben permitir registrar propuestas", async () => {
      for (const cfp of cfps) {
        const proposal = gen.next();
        await cfp.registerProposal(proposal);
      }
    });

    it("debe rechazar el registro en llamados inexistentes", async () => {
      const nonExistentCallId = gen.next();
      const proposal = gen.next();
      await expect(
        factory.registerProposal(nonExistentCallId, proposal)
      ).to.be.revertedWith("El llamado no existe");
    });

    it("debe registrar correctamente propuestas", async () => {
      for (const cfp of cfps) {
        const callId = await cfp.callId();
        const proposal = callId;
        const account =
          accounts[Math.trunc(Math.random() * accounts.length)];
        await factory.connect(account).registerProposal(callId, proposal);
        const proposalData = await cfp.proposalData(proposal);
        expect(proposalData.sender).to.equal(account.address);
      }
    });

    it("debe rechazar propuestas ya registradas", async () => {
      for (const cfp of cfps) {
        const callId = await cfp.callId();
        const proposal = callId;
        const account =
          accounts[Math.trunc(Math.random() * accounts.length)];
        await expect(
          factory.connect(account).registerProposal(callId, proposal)
        ).to.be.revertedWith("La propuesta ya ha sido registrada");
      }
    });
  });

  describe("Desautorización de creadores pendientes", function () {
    it("debe quitar de la lista de pendientes al desautorizar un creador pendiente", async () => {
      const Factory = await ethers.getContractFactory("CFPFactory");
      const factory = await Factory.deploy();

      await factory.connect(accounts[0]).register();
      expect(await factory.isRegistered(accounts[0].address)).to.be.true;
      expect(await factory.isAuthorized(accounts[0].address)).to.be.false;
      expect(await factory.pendingCount()).to.equal(1n);

      await factory.unauthorize(accounts[0].address);

      expect(await factory.isRegistered(accounts[0].address)).to.be.false;
      expect(await factory.isAuthorized(accounts[0].address)).to.be.false;
      expect(await factory.pendingCount()).to.equal(0n);
    });
  });
});
