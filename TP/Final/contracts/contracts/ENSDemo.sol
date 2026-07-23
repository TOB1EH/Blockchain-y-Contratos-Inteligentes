// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./ENSRegistry.sol";
import "./interfaces/IAddrResolver.sol";

/**
 * ENSDemo ilustra cómo un contrato puede usar el registro ENS para:
 *   1. Resolver un nombre a una dirección (lookup directo).
 *   2. Verificar la propiedad de un nodo.
 *
 * El patrón de resolución es siempre en dos pasos:
 *   1. Consultar el registro para obtener la dirección del resolutor.
 *   2. Consultar el resolutor (a través de IAddrResolver) para obtener el dato.
 *
 * Nótese que este contrato depende de IAddrResolver, no de PublicResolver.
 * Cualquier contrato que implemente IAddrResolver puede ser usado como resolutor,
 * lo que hace al sistema extensible sin modificar los consumidores.
 */
contract ENSDemo {
    ENSRegistry public immutable registry;

    constructor(ENSRegistry _registry) {
        registry = _registry;
    }

    /**
     * Resuelve un nombre a una dirección Ethereum.
     *
     * @param node  Resultado de namehash(nombre), por ejemplo namehash("alice.test")
     * @return      La dirección asociada al nombre, o address(0) si no está configurada
     */
    function resolve(bytes32 node) external view returns (address) {
        address resolverAddr = registry.resolver(node);
        if (resolverAddr == address(0)) return address(0);
        return IAddrResolver(resolverAddr).addr(node);
    }

    /**
     * Retorna el propietario de un nodo en el registro ENS.
     */
    function ownerOf(bytes32 node) external view returns (address) {
        return registry.owner(node);
    }
}
