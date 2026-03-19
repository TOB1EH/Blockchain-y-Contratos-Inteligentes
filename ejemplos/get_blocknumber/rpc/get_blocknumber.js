#!/usr/bin/env node
/* Este script obtiene el número de bloque actual de la red Ethereum 
 * utilizando JSON-RPC. 
 * Por simplicidad, el código *no maneja errores*.
 * En una implementación real, deberían manejarse los errores adecuadamente.
 * Este script asume que el nodo Ethereum está corriendo en localhost:8545.
*/

import axios from 'axios'

async function rpcreq(opname, params) {
    var body = {
        jsonrpc: "2.0",
        id: 1,
        method: opname,
        params: params
    }
    let response = await axios.post(
        'http://localhost:8545',
        body
    );
    return response.data.result;
};

let blockNumber = await rpcreq('eth_blockNumber', []);
console.log(parseInt(blockNumber, 16));
