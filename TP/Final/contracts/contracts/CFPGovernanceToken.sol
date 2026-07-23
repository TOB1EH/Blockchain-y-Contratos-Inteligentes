// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import { ERC20 } from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import { Ownable } from "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title CFPGovernanceToken
 * @notice Token ERC-20 con precio fijo en ETH, compra y redencion.
 *         Usado como garantia de oferta en llamados que requieren deposito
 *         previo de tokens (guaranteeAmount > 0).
 *
 * El precio se establece en el constructor como TOKENS_PER_ETH:
 *   1 ETH = TOKENS_PER_ETH tokens (en unidades base, con 18 decimales)
 *
 * La compra (buy) acuna nuevos tokens a cambio de ETH.
 * La redencion (redeem) quema tokens y devuelve ETH al precio fijo.
 */
contract CFPGovernanceToken is ERC20, Ownable {

    /// Cantidad de tokens (en unidades minimas) que se reciben por 1 ETH
    uint256 public immutable tokensPerEth;

    /// Suministro inicial acunado al deployer: 1.000.000 tokens
    uint256 private constant INITIAL_SUPPLY = 1_000_000 * 10 ** 18;

    event TokensPurchased(address indexed buyer, uint256 ethAmount, uint256 tokenAmount);
    event TokensRedeemed(address indexed seller, uint256 tokenAmount, uint256 ethAmount);

    /**
     * @param _tokensPerEth  Cantidad de unidades base del token que se obtienen por 1 ETH.
     *                       Ej: 1000 significa 1 ETH = 1000 CFPT (con 18 decimales cada uno).
     */
    constructor(uint256 _tokensPerEth)
        ERC20("CFP Governance Token", "CFPT")
        Ownable(msg.sender)
    {
        require(_tokensPerEth > 0, "El precio debe ser mayor a cero");
        tokensPerEth = _tokensPerEth;
        _mint(msg.sender, INITIAL_SUPPLY);
    }

    /**
     * @notice Compra tokens enviando ETH.
     *         El ETH queda retenido en el contrato para futuras redenciones.
     */
    function buy() external payable {
        require(msg.value > 0, "Debes enviar ETH para comprar tokens");
        uint256 amount = msg.value * tokensPerEth;
        _mint(msg.sender, amount);
        emit TokensPurchased(msg.sender, msg.value, amount);
    }

    /**
     * @notice Redime (quema) tokens y devuelve ETH al precio fijo.
     *         Requiere que el contrato tenga suficiente ETH (de compras previas).
     * @param amount Cantidad de tokens a redimir (en unidades minimas, 18 decimales)
     */
    function redeem(uint256 amount) external {
        require(amount > 0, "Cantidad debe ser mayor a cero");
        require(balanceOf(msg.sender) >= amount, "Saldo insuficiente");
        uint256 ethAmount = amount / tokensPerEth;
        require(ethAmount > 0, "Monto demasiado pequeno para redimir");
        require(address(this).balance >= ethAmount, "El contrato no tiene suficientes ETH");

        _burn(msg.sender, amount);
        (bool ok, ) = msg.sender.call{value: ethAmount}("");
        require(ok, "Transferencia de ETH fallida");
        emit TokensRedeemed(msg.sender, amount, ethAmount);
    }

    /**
     * @notice Retira el ETH acumulado por ventas. Solo el owner.
     * @param to Direccion que recibira los fondos
     */
    function withdraw(address payable to) external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "No hay fondos para retirar");
        (bool ok, ) = to.call{value: balance}("");
        require(ok, "Transferencia fallida");
    }
}
