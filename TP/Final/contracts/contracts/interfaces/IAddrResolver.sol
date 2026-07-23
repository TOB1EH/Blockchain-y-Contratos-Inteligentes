// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * Resolución de dirección Ethereum (EIP-137).
 *
 * El registro de tipo "addr" es el principal de ENS: asocia un nombre a una
 * dirección Ethereum. Es el equivalente del registro A/AAAA en DNS.
 */
interface IAddrResolver {
    event AddrChanged(bytes32 indexed node, address addr);

    function setAddr(bytes32 node, address addr) external;
    function addr(bytes32 node) external view returns (address);
}
