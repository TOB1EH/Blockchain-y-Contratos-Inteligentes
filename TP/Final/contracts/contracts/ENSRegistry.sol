// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * ENSRegistry — registro central del sistema de nombres.
 *
 * Cada nombre ENS se representa internamente como un "nodo": un hash de 32 bytes
 * calculado con el algoritmo namehash (EIP-137). El registro asocia cada nodo
 * a su propietario y al contrato resolutor que sabe interpretar sus registros.
 *
 * La jerarquía de nombres se construye con setSubnodeOwner: el propietario de
 * "test" puede crear "alice.test", "bob.test", etc., y asignarlos a quienes quiera.
 */
contract ENSRegistry {

    struct Record {
        address owner;
        address resolver;
        uint64  ttl;
    }

    // node → registro
    mapping(bytes32 => Record) private records;

    // Delegación de operador: owner puede autorizar a otra dirección a gestionar
    // todos sus nodos (útil para contratos que actúan en nombre del usuario)
    mapping(address => mapping(address => bool)) private operators;

    event NewOwner(bytes32 indexed node, bytes32 indexed label, address owner);
    event Transfer(bytes32 indexed node, address owner);
    event NewResolver(bytes32 indexed node, address resolver);
    event NewTTL(bytes32 indexed node, uint64 ttl);
    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);

    modifier authorised(bytes32 node) {
        address nodeOwner = records[node].owner;
        require(nodeOwner == msg.sender || operators[nodeOwner][msg.sender], "ENS: no autorizado");
        _;
    }

    constructor() {
        // El nodo raíz (bytes32(0)) pertenece al deployer
        records[bytes32(0)].owner = msg.sender;
    }

    // ── Lectura ───────────────────────────────────────────────────────────────

    function owner(bytes32 node) public view returns (address) {
        return records[node].owner;
    }

    function resolver(bytes32 node) public view returns (address) {
        return records[node].resolver;
    }

    function ttl(bytes32 node) public view returns (uint64) {
        return records[node].ttl;
    }

    function recordExists(bytes32 node) public view returns (bool) {
        return records[node].owner != address(0);
    }

    function isApprovedForAll(address nodeOwner, address operator) public view returns (bool) {
        return operators[nodeOwner][operator];
    }

    // ── Escritura ─────────────────────────────────────────────────────────────

    function setOwner(bytes32 node, address newOwner) public authorised(node) {
        records[node].owner = newOwner;
        emit Transfer(node, newOwner);
    }

    /**
     * Crea o actualiza el subdominio `label` bajo `node` y lo asigna a `newOwner`.
     * El subnode resultante es keccak256(node ‖ keccak256(label)).
     * Solo el propietario de `node` puede llamar esta función.
     */
    function setSubnodeOwner(bytes32 node, bytes32 label, address newOwner)
        public
        authorised(node)
        returns (bytes32)
    {
        bytes32 subnode = keccak256(abi.encodePacked(node, label));
        records[subnode].owner = newOwner;
        emit NewOwner(node, label, newOwner);
        return subnode;
    }

    function setResolver(bytes32 node, address newResolver) public authorised(node) {
        records[node].resolver = newResolver;
        emit NewResolver(node, newResolver);
    }

    function setTTL(bytes32 node, uint64 newTTL) public authorised(node) {
        records[node].ttl = newTTL;
        emit NewTTL(node, newTTL);
    }

    function setApprovalForAll(address operator, bool approved) public {
        operators[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    /**
     * Versión atómica que crea un subdominio y le asigna propietario,
     * resolutor y TTL en una sola transacción.
     */
    function setSubnodeRecord(
        bytes32 node,
        bytes32 label,
        address newOwner,
        address newResolver,
        uint64  newTTL
    ) public authorised(node) returns (bytes32) {
        bytes32 subnode = keccak256(abi.encodePacked(node, label));
        records[subnode] = Record(newOwner, newResolver, newTTL);
        emit NewOwner(node, label, newOwner);
        return subnode;
    }
}
