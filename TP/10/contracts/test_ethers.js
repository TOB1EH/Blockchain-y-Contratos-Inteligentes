import { ethers } from "ethers";
const MNEMONIC = "test test test test test test test test test test test junk";
const adminWallet = ethers.HDNodeWallet.fromPhrase(MNEMONIC, "", "m/44'/60'/0'/0/2");
console.log(adminWallet.address);
