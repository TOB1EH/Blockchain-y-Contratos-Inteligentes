// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * Resolución de nombre (EIP-181, resolución inversa).
 *
 * Almacena el nombre canónico asociado a un nodo. Se usa principalmente en
 * resolución inversa: ReverseRegistrar crea el nodo
 * "<addr_hex>.addr.reverse" y guarda en él el nombre primario de esa dirección
 * mediante esta interfaz.
 *
 * Flujo completo de resolución inversa:
 *   1. alice llama a ReverseRegistrar.setName("alice.test")
 *   2. ReverseRegistrar crea el nodo namehash("<alice>.addr.reverse")
 *   3. ReverseRegistrar llama a INameResolver.setName(node, "alice.test")
 *   4. Una aplicación consulta INameResolver.name(node) para mostrar "alice.test"
 */
interface INameResolver {
    event NameChanged(bytes32 indexed node, string name);

    function setName(bytes32 node, string calldata name) external;
    function name(bytes32 node) external view returns (string memory);
}
