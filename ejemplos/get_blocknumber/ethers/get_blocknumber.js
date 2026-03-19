#!/usr/bin/env node
"use strict"

import { ethers } from "ethers";

const provider = new ethers.JsonRpcProvider("http://localhost:8545");

const blockNumber = await provider.getBlockNumber();
console.log(blockNumber);
