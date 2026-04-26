import hre from "hardhat";

async function main() {
  const { ethers } = await hre.network.getOrCreate();

  const TaskBoard = await ethers.getContractFactory("TaskBoard");
  const taskBoard = await TaskBoard.deploy();

  await taskBoard.waitForDeployment();

  console.log(`TaskBoard desplegado en: ${await taskBoard.getAddress()}`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});