import { defineConfig } from "hardhat/config";
import hardhatEthers from "@nomicfoundation/hardhat-ethers";
import hardhatIgnition from "@nomicfoundation/hardhat-ignition";
import hardhatNetworkHelpers from "@nomicfoundation/hardhat-network-helpers";
import hardhatEthersChaiMatchers from "@nomicfoundation/hardhat-ethers-chai-matchers";
import hardhatMocha from "@nomicfoundation/hardhat-mocha";

export default defineConfig({
  plugins: [
    hardhatEthers,
    hardhatIgnition,
    hardhatNetworkHelpers,
    hardhatEthersChaiMatchers,
    hardhatMocha,
  ],
  solidity: "0.8.28",
});
