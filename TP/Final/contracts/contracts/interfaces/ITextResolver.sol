// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

/**
 * Resolución de registros de texto (EIP-634).
 *
 * Permite almacenar metadatos arbitrarios asociados a un nombre mediante pares
 * clave-valor. Claves convencionales definidas por la comunidad ENS:
 *
 *   "url"         sitio web del propietario
 *   "avatar"      URL de imagen de perfil
 *   "description" descripción en texto libre
 *   "twitter"     handle de Twitter, sin el símbolo arroba
 *   "github"      nombre de usuario de GitHub
 *   "email"       dirección de correo
 */
interface ITextResolver {
    event TextChanged(bytes32 indexed node, string indexed key, string value);

    function setText(bytes32 node, string calldata key, string calldata value) external;
    function text(bytes32 node, string calldata key) external view returns (string memory);
}
