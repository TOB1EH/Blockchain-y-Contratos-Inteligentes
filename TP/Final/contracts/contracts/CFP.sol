// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title CFP (Call For Proposals)
 * @notice Contrato individual de llamado a presentacion de propuestas.
 *         Soporta dos modos: sin garantia (legacy) y con garantia en tokens ERC-20.
 *
 * Modo garantia (guaranteeAmount > 0):
 *   - El proponente debe transferir guaranteeAmount tokens al contrato
 *     como deposito de oferta.
 *   - Si la propuesta es finalizada (finalize()) por el creador, el
 *     proponente recupera su garantia via claimRefund().
 *   - registerProposal() (public) funciona solo si guaranteeAmount == 0.
 *   - registerProposalFor() (creator only) funciona solo si guaranteeAmount == 0.
 *   - registerProposalWithCollateral() reemplaza al registro publico
 *     cuando hay garantia, transfiriendo los tokens al hacer el registro.
 */
contract CFP {
    event ProposalRegistered(
        bytes32 proposal,
        address sender,
        uint256 blockNumber
    );

    bytes32 private _callId;
    uint256 private _closingTime;
    address private _creator;
    address private _factory;
    bytes32[] private _proposals;

    struct ProposalData {
        address sender;
        uint256 blockNumber;
        uint256 timestamp;
    }

    mapping(bytes32 => ProposalData) private _proposalData;

    struct DeliveryData {
        bytes32 filesRoot;
        address sender;
        uint256 blockNumber;
        uint256 timestamp;
        bool delivered;
    }

    mapping(bytes32 => DeliveryData) private _deliveries;

    event FilesDelivered(
        bytes32 indexed proposalId,
        bytes32 filesRoot,
        address sender,
        uint256 timestamp
    );

    function registerDelivery(bytes32 proposalId, bytes32 filesRoot) public {
        require(block.timestamp > _closingTime, "La convocatoria no ha cerrado");
        require(!finalized, "Llamado finalizado: no se aceptan mas entregas");
        require(_proposalData[proposalId].blockNumber != 0, "La propuesta no existe");
        require(!_deliveries[proposalId].delivered, "La entrega ya fue registrada");

        _deliveries[proposalId] = DeliveryData({
            filesRoot:   filesRoot,
            sender:      msg.sender,
            blockNumber: block.number,
            timestamp:   block.timestamp,
            delivered:   true
        });

        emit FilesDelivered(proposalId, filesRoot, msg.sender, block.timestamp);
    }

    function deliveryData(bytes32 proposalId) public view returns (DeliveryData memory) {
        return _deliveries[proposalId];
    }

    function proposalData(bytes32 proposal) public view returns (ProposalData memory) {
        return _proposalData[proposal];
    }

    function proposals(uint index) public view returns (bytes32) {
        return _proposals[index];
    }

    function closingTime() public view returns (uint256) {
        return _closingTime;
    }

    function callId() public view returns (bytes32) {
        return _callId;
    }

    function creator() public view returns (address) {
        return _creator;
    }

    function factory() public view returns (address) {
        return _factory;
    }

    /** --- GARANTIA --- */

    /// Monto de tokens requerido como garantia (0 = sin garantia)
    uint256 public immutable guaranteeAmount;

    /// Direccion del token ERC-20 usado como garantia
    IERC20 public immutable token;

    /// Indica si el creador ya finalizo la seleccion (no se aceptan mas entregas)
    bool public finalized;

    /// Mapea una propuesta a si el proponente ya reclamo su reembolso
    mapping(bytes32 => bool) public refundClaimed;

    /// Conjunto de proponentes que depositaron garantia (para iteracion)
    address[] public proposers;
    mapping(address => bool) private _isProposer;

    /// Propuestas aceptadas por el creador al finalizar
    bytes32[] public acceptedProposals;

    event ProposalRegisteredWithCollateral(bytes32 indexed proposal, address indexed sender, uint256 amount);
    event CallFinalized(bytes32 indexed callId);
    event RefundClaimed(bytes32 indexed proposal, address indexed sender, uint256 amount);

    /**
     * @param callId_ Identificador unico del llamado
     * @param closingTime_ Timestamp UNIX de cierre de recepcion de propuestas
     * @param guaranteeAmount_ Monto de garantia en tokens (0 = sin garantia)
     * @param token_ Direccion del contrato ERC-20 usado como garantia (se ignora si guaranteeAmount_ == 0)
     */
    constructor(bytes32 callId_, uint256 closingTime_, uint256 guaranteeAmount_, IERC20 token_, address creator_) {
        require(block.timestamp <= closingTime_,
                "El cierre de la convocatoria no puede estar en el pasado");
        _callId         = callId_;
        _closingTime    = closingTime_;
        _creator        = creator_;
        _factory        = msg.sender;

        guaranteeAmount = guaranteeAmount_;
        token = token_;
    }

    function proposalCount() public view returns (uint256) {
        return _proposals.length;
    }

    function registerProposal(bytes32 proposal)
        public beforeClose notRegistered(proposal)
    {
        require(guaranteeAmount == 0, "Use registerProposalWithCollateral para llamados con garantia");
        _register(proposal, msg.sender);
    }

    function registerProposalFor(bytes32 proposal, address sender)
        public onlyCreator beforeClose notRegistered(proposal)
    {
        require(guaranteeAmount == 0, "Use registerProposalWithCollateral para llamados con garantia");
        _register(proposal, sender);
    }

    /**
     * @notice Registra una propuesta con deposito de garantia en tokens.
     *         El proponente debe haber aprobado al contrato para transferir
     *         guaranteeAmount tokens previamente (ERC-20 approve).
     *         Solo disponible cuando guaranteeAmount > 0.
     * @param proposal Identificador de la propuesta
     */
    function registerProposalWithCollateral(bytes32 proposal)
        public beforeClose notRegistered(proposal)
    {
        require(guaranteeAmount > 0, "Llamado sin garantia: use registerProposal");
        require(msg.sender != _creator, "El creador del llamado no puede presentar propuestas");
        require(
            token.transferFrom(msg.sender, address(this), guaranteeAmount),
            "Transferencia de tokens fallida"
        );

        _register(proposal, msg.sender);

        if (!_isProposer[msg.sender]) {
            _isProposer[msg.sender] = true;
            proposers.push(msg.sender);
        }

        emit ProposalRegisteredWithCollateral(proposal, msg.sender, guaranteeAmount);
    }

    /**
     * @notice Finaliza el llamado: el creador selecciona las propuestas ganadoras
     *         y desbloquea los reembolsos para las demas.
     *         Requiere que el llamado tenga garantia y que el creador lo ejecute.
     */
    function finalize(bytes32[] calldata _acceptedProposals) public onlyCreator {
        require(guaranteeAmount > 0, "Llamado sin garantia no requiere finalizacion");
        require(!finalized, "El llamado ya fue finalizado");
        require(block.timestamp > _closingTime, "La convocatoria no ha cerrado");
        finalized = true;
        for (uint256 i = 0; i < _acceptedProposals.length; i++) {
            acceptedProposals.push(_acceptedProposals[i]);
        }
        emit CallFinalized(_callId);
    }

    /**
     * @notice Reclama el reembolso de la garantia asociada a una propuesta.
     *         Solo disponible si el llamado esta finalizado y la propuesta existe.
     *         El reembolso NO se devuelve si la propuesta fue aceptada.
     * @param proposal Identificador de la propuesta
     */
    function claimRefund(bytes32 proposal) public {
        require(finalized, "El llamado no ha sido finalizado");
        require(!refundClaimed[proposal], "El reembolso ya fue reclamado");

        ProposalData memory data = _proposalData[proposal];
        require(data.sender != address(0), "La propuesta no existe");
        require(data.sender == msg.sender, "Solo el proponente puede reclamar el reembolso");

        bool isAccepted = false;
        for (uint256 i = 0; i < acceptedProposals.length; i++) {
            if (acceptedProposals[i] == proposal) {
                isAccepted = true;
                break;
            }
        }
        require(!isAccepted, "Propuesta aceptada: no se reembolsa la garantia");

        refundClaimed[proposal] = true;

        require(
            token.transfer(msg.sender, guaranteeAmount),
            "Transferencia de tokens fallida"
        );
        emit RefundClaimed(proposal, msg.sender, guaranteeAmount);
    }

    function isProposalAccepted(bytes32 proposal) public view returns (bool) {
        for (uint256 i = 0; i < acceptedProposals.length; i++) {
            if (acceptedProposals[i] == proposal) return true;
        }
        return false;
    }

    function proposalTimestamp(bytes32 proposal) public view returns (uint256) {
        return _proposalData[proposal].timestamp;
    }

    function _register(bytes32 proposal, address sender) private {
        _proposalData[proposal] = ProposalData({
            sender:      sender,
            blockNumber: block.number,
            timestamp:   block.timestamp
        });
        _proposals.push(proposal);
        emit ProposalRegistered(proposal, sender, block.number);
    }

    modifier onlyCreator() {
        require(msg.sender == _creator || msg.sender == _factory, "Solo el creador puede hacer esta llamada");
        _;
    }

    modifier beforeClose() {
        require(block.timestamp <= _closingTime, "Convocatoria cerrada");
        _;
    }

    modifier notRegistered(bytes32 proposal) {
        require(_proposalData[proposal].blockNumber == 0, "La propuesta ya ha sido registrada");
        _;
    }
}
