// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./ENSRegistry.sol";
import "./interfaces/IAddrResolver.sol";
import "./interfaces/ITextResolver.sol";
import "./interfaces/INameResolver.sol";

/**
 * PublicResolver — resolutor de registros ENS.
 *
 * Implementa las tres interfaces de resolución definidas en contracts/interfaces/:
 *   - IAddrResolver  → dirección Ethereum asociada a un nombre
 *   - ITextResolver  → registros de texto arbitrarios (url, avatar, twitter, ...)
 *   - INameResolver  → nombre canónico de un nodo (usado en resolución inversa)
 *
 * Un único despliegue de este contrato sirve a todos los nombres del sistema.
 * Cualquier nombre puede apuntar a este resolutor configurando su entrada en
 * ENSRegistry con setResolver(node, publicResolver.address).
 *
 * Autorización: solo el propietario del nodo en el registro (o un operador
 * aprobado con setApprovalForAll) puede modificar sus registros.
 */
contract PublicResolver is IAddrResolver, ITextResolver, INameResolver {

    ENSRegistry public immutable registry;

    // Delegación de operador a nivel del resolutor (independiente del registro)
    mapping(address => mapping(address => bool)) private _operatorApprovals;

    mapping(bytes32 => address)                    private _addresses;
    mapping(bytes32 => mapping(string => string))  private _texts;
    mapping(bytes32 => string)                     private _names;

    event ApprovalForAll(address indexed owner, address indexed operator, bool approved);

    constructor(ENSRegistry _registry) {
        registry = _registry;
    }

    modifier authorised(bytes32 node) {
        address nodeOwner = registry.owner(node);
        require(
            nodeOwner == msg.sender || _operatorApprovals[nodeOwner][msg.sender],
            "PublicResolver: no autorizado"
        );
        _;
    }

    // ── Operadores ────────────────────────────────────────────────────────────

    function setApprovalForAll(address operator, bool approved) external {
        _operatorApprovals[msg.sender][operator] = approved;
        emit ApprovalForAll(msg.sender, operator, approved);
    }

    function isApprovedForAll(address nodeOwner, address operator) public view returns (bool) {
        return _operatorApprovals[nodeOwner][operator];
    }

    // ── IAddrResolver ─────────────────────────────────────────────────────────

    function setAddr(bytes32 node, address _addr) external override authorised(node) {
        _addresses[node] = _addr;
        emit AddrChanged(node, _addr);
    }

    function addr(bytes32 node) external view override returns (address) {
        return _addresses[node];
    }

    // ── ITextResolver ─────────────────────────────────────────────────────────

    function setText(bytes32 node, string calldata key, string calldata value)
        external override authorised(node)
    {
        _texts[node][key] = value;
        emit TextChanged(node, key, value);
    }

    function text(bytes32 node, string calldata key)
        external view override returns (string memory)
    {
        return _texts[node][key];
    }

    // ── INameResolver ─────────────────────────────────────────────────────────

    function setName(bytes32 node, string calldata _name) external override authorised(node) {
        _names[node] = _name;
        emit NameChanged(node, _name);
    }

    function name(bytes32 node) external view override returns (string memory) {
        return _names[node];
    }
}
