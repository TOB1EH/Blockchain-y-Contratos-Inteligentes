
import hre from "hardhat";
import { encodeBytes32String } from "ethers";

async function main() {
  const { ethers } = await hre.network.connect();

  const languages = ["Alemán", "Búlgaro", "Chino", "Danés", "Español"];
  const options = languages.map(encodeBytes32String);

  const ballot = await ethers.deployContract("Ballot", [options]);

  await ballot.waitForDeployment();

  console.log(
    `Ballot deployed to ${ballot.target}`
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
