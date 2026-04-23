// This setup uses Hardhat Ignition to manage smart contract deployments.
// Learn more about it at https://hardhat.org/ignition

import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";
import { encodeBytes32String } from "ethers";


export default buildModule("BallotModule", (m) => {
  const languages = ["Alemán", "Búlgaro", "Catalán", "Danés", "Español"];
  const options = languages.map((language) => encodeBytes32String(language));

  const ballot = m.contract("Ballot", [options]);

  return { ballot };
});
