// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./ENSRegistry.sol";
import "./interfaces/INameResolver.sol";

/**
 * ReverseRegistrar — permite asociar una dirección Ethereum a un nombre ENS.
 *
 * La resolución "directa" va de nombre → dirección (via addr() en el resolutor).
 * La resolución "inversa" va de dirección → nombre, y es lo que permite que
 * una aplicación muestre "alice.test" en lugar de "0x70997...C8" para una cuenta.
 *
 * ENS reserva el dominio especial "addr.reverse" para este propósito. Cada
 * dirección tiene un nodo inverso calculado como:
 *
 *   namehash("<addr_lowercase_sin_0x>.addr.reverse")
 *
 * Este contrato debe ser el propietario del nodo "addr.reverse" en el registro,
 * de modo que pueda crear subnodos para cada dirección.
 *
 * Para que setName() funcione, el contrato necesita un resolutor configurado
 * (setDefaultResolver) que implemente la función setName(bytes32, string).
 */
contract ReverseRegistrar {

    // Nodo de "addr.reverse" — calculado offline como namehash("addr.reverse")
    bytes32 public constant ADDR_REVERSE_NODE =
        0x91d1777781884d03a6757a803996e38de2a42967fb37eeaca72729271025a9e2;

    ENSRegistry   public immutable registry;
    INameResolver public defaultResolver;

    event ReverseClaimed(address indexed addr, bytes32 indexed node);
    event DefaultResolverChanged(address resolver);

    constructor(ENSRegistry _registry) {
        registry = _registry;
    }

    function setDefaultResolver(INameResolver _resolver) external {
        defaultResolver = _resolver;
        emit DefaultResolverChanged(address(_resolver));
    }

    /**
     * Registra el nombre primario del llamante.
     * Crea el nodo inverso para msg.sender y almacena `name` en el resolutor.
     *
     * @param name  El nombre ENS a asociar, ej: "alice.test"
     * @return node El nodo inverso creado
     */
    function setName(string calldata name) external returns (bytes32) {
        return _setName(msg.sender, msg.sender, name);
    }

    /**
     * Calcula el nodo inverso de una dirección:
     *   keccak256(ADDR_REVERSE_NODE ‖ keccak256(<addr_hex_lowercase>))
     */
    function node(address addr) public pure returns (bytes32) {
        return keccak256(
            abi.encodePacked(ADDR_REVERSE_NODE, _labelHash(addr))
        );
    }

    // ── Internos ──────────────────────────────────────────────────────────────

    function _setName(address addr, address owner, string calldata name)
        internal
        returns (bytes32)
    {
        require(address(defaultResolver) != address(0), "ReverseRegistrar: sin resolutor");

        bytes32 labelHash = _labelHash(addr);

        // Creamos el subnode con este contrato como propietario temporal para
        // poder llamar a resolver.setName() con autorización.
        bytes32 reverseNode = registry.setSubnodeRecord(
            ADDR_REVERSE_NODE,
            labelHash,
            address(this),
            address(defaultResolver),
            0
        );

        defaultResolver.setName(reverseNode, name);

        // Transferimos la propiedad al destinatario final
        registry.setOwner(reverseNode, owner);

        emit ReverseClaimed(addr, reverseNode);
        return reverseNode;
    }

    /**
     * Devuelve el keccak256 de la representación hex en minúsculas de una
     * dirección (sin el prefijo "0x"), que es el label del nodo inverso.
     */
    function _labelHash(address addr) internal pure returns (bytes32) {
        return keccak256(_toHexString(addr));
    }

    function _toHexString(address addr) internal pure returns (bytes memory) {
        bytes memory result = new bytes(40);
        bytes16 hexChars = "0123456789abcdef";
        uint160 value = uint160(addr);
        for (int i = 39; i >= 0; i--) {
            result[uint(i)] = hexChars[value & 0xf];
            value >>= 4;
        }
        return result;
    }
}
