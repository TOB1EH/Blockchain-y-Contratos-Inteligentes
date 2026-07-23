// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./ENSRegistry.sol";

/**
 * FIFSRegistrar — registrador de nombres bajo un TLD dado.
 *
 * FIFS significa "First In First Served": el primer usuario en registrar
 * un nombre lo obtiene. Una vez registrado, solo el propietario actual
 * puede transferirlo a otra dirección.
 *
 * Este contrato gestiona los subnodos de un nodo padre (el TLD) en el registro
 * ENS. Para que funcione, el nodo padre debe tener este contrato como propietario
 * en el ENSRegistry.
 */
contract FIFSRegistrar {

    ENSRegistry public immutable registry;
    bytes32     public immutable rootNode;

    /**
     * @param _registry  Dirección del ENSRegistry
     * @param _rootNode  Nodo del TLD que este registrador gestiona (ej: namehash("test"))
     */
    constructor(ENSRegistry _registry, bytes32 _rootNode) {
        registry = _registry;
        rootNode = _rootNode;
    }

    /**
     * Registra el subdominio `label` bajo el TLD y lo asigna a `newOwner`.
     * Falla si el subdominio ya pertenece a otra cuenta.
     *
     * @param label     keccak256 de la etiqueta (ej: keccak256("alice"))
     * @param newOwner  Dirección que recibirá la propiedad del nombre
     */
    function register(bytes32 label, address newOwner) public {
        bytes32 subnode = keccak256(abi.encodePacked(rootNode, label));
        address currentOwner = registry.owner(subnode);

        require(
            currentOwner == address(0) || currentOwner == msg.sender,
            "FIFSRegistrar: nombre ya registrado"
        );

        registry.setSubnodeOwner(rootNode, label, newOwner);
    }
}
