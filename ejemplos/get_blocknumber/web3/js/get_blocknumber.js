#!/usr/bin/env node
"use strict"

import Web3 from "web3"
var url = "http://localhost:8545"
var w3 = new Web3(url)

try {
    var result = await w3.eth.getBlockNumber()
    console.log(result)
} catch (err) {
    console.error(err)
}
