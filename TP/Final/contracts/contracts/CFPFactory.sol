// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "./CFP.sol";
import { IERC20 } from "@openzeppelin/contracts/token/ERC20/IERC20.sol";

/**
 * @title CFPFactory
 * @notice Fabrica de contratos CFP (Call For Proposals).
 *         Administra registro, autorizacion de creadores, y despliegue
 *         de nuevos llamados, con soporte opcional de garantia en tokens.
 *
 * El token ERC-20 usado como garantia se fija en el constructor y es
 * inmutable. Todos los CFP creados por esta fabrica usaran el mismo token.
 */
contract CFPFactory {
    event CFPCreated(address creator, bytes32 callId, CFP cfp, uint256 guaranteeAmount);
    event CreatorRegistered(address indexed creator);
    event CreatorAuthorized(address indexed creator);
    event CreatorUnauthorized(address indexed creator);

    struct CallForProposals {
        address creator;
        CFP cfp;
        uint256 guaranteeAmount;
    }

    enum AccountStatus {
        None,
        Pending,
        Authorized
    }

    mapping(address => AccountStatus) private _status;

    address private _owner;

    /// Direccion del token ERC-20 usado como garantia para todos los CFP creados
    IERC20 public immutable token;

    mapping(bytes32 => CallForProposals) private _calls;

    address[] private _creators;
    mapping(address => bool) private _isCreator;
    mapping(address => bytes32[]) private _createdBy;

    address[] private _pending;
    mapping(address => uint256) private _pendingIndex;

    /**
     * @param token_ Direccion del contrato ERC-20 usado como garantia.
     *               Puede ser address(0) si no se requiere garantia.
     */
    constructor(IERC20 token_) {
        _owner = msg.sender;
        token = token_;
    }

    function owner() public view returns (address) {
        return _owner;
    }

    function calls(bytes32 callId)
        public view returns (CallForProposals memory)
    {
        return _calls[callId];
    }

    function creators(uint index) public view returns (address) {
        return _creators[index];
    }

    /**
     * @notice Crea un llamado con garantia opcional.
     * @param callId Identificador unico del llamado
     * @param timestamp Timestamp UNIX de cierre
     * @param guaranteeAmount Monto de garantia en tokens (0 = sin garantia)
     */
    function create(bytes32 callId, uint256 timestamp, uint256 guaranteeAmount)
        public
        onlyAuthorized(msg.sender)
        callNotExists(callId)
        returns (CFP)
    {
        return _create(callId, timestamp, msg.sender, guaranteeAmount);
    }

    /**
     * @notice Crea un llamado en nombre de `creator`, con garantia opcional.
     *         Solo el owner.
     */
    function createFor(bytes32 callId, uint256 timestamp, address creator, uint256 guaranteeAmount)
        public onlyOwner onlyAuthorized(creator) callNotExists(callId)
        returns (CFP)
    {
        return _create(callId, timestamp, creator, guaranteeAmount);
    }

    function _create(bytes32 callId, uint256 timestamp, address creator, uint256 guaranteeAmount)
        private returns (CFP)
    {
        CFP cfp = new CFP(callId, timestamp, guaranteeAmount, token, creator);
        _calls[callId] = CallForProposals({
            creator: creator,
            cfp: cfp,
            guaranteeAmount: guaranteeAmount
        });

        if (!_isCreator[creator]) {
            _isCreator[creator] = true;
            _creators.push(creator);
        }
        _createdBy[creator].push(callId);

        emit CFPCreated(creator, callId, cfp, guaranteeAmount);
        return cfp;
    }

    function creatorsCount() public view returns (uint256) {
        return _creators.length;
    }

    function createdBy(address creator, uint256 index) public view returns (bytes32) {
        return _createdBy[creator][index];
    }

    function createdByCount(address creator) public view returns (uint256) {
        return _createdBy[creator].length;
    }

    /**
     * @notice Registra una propuesta en un llamado existente.
     *         Solo funciona si el llamado NO tiene garantia (guaranteeAmount == 0).
     *         Para llamados con garantia, el proponente debe interactuar
     *         directamente con el contrato CFP via registerProposalWithCollateral().
     */
    function registerProposal(bytes32 callId, bytes32 proposal) public callExists(callId)
    {
        require(
            _calls[callId].guaranteeAmount == 0,
            "Llamado con garantia: use registerProposalWithCollateral en el contrato CFP"
        );
        _calls[callId].cfp.registerProposalFor(proposal, msg.sender);
    }

    function register() public
    {
        require(_status[msg.sender] == AccountStatus.None, "Ya se ha registrado");
        _status[msg.sender] = AccountStatus.Pending;
        _pendingIndex[msg.sender] = _pending.length;
        _pending.push(msg.sender);
        emit CreatorRegistered(msg.sender);
    }

    function authorize(address account) public onlyOwner
    {
        _removeFromPendingIfExists(account);
        _status[account] = AccountStatus.Authorized;
        emit CreatorAuthorized(account);
    }

    function unauthorize(address account) public onlyOwner
    {
        _removeFromPendingIfExists(account);
        _status[account] = AccountStatus.None;
        emit CreatorUnauthorized(account);
    }

    function _removeFromPendingIfExists(address account) private {
        if (_status[account] != AccountStatus.Pending) return;

        uint256 index = _pendingIndex[account];
        uint256 last  = _pending.length - 1;

        if (index < last) {
            address moved = _pending[last];
            _pending[index] = moved;
            _pendingIndex[moved] = index;
        }
        _pending.pop();
    }

    function getAllPending() public view onlyOwner returns (address[] memory) {
        return _pending;
    }

    function getPending(uint256 index) public view onlyOwner returns (address) {
        return _pending[index];
    }

    function pendingCount() public view onlyOwner returns (uint256) {
        return _pending.length;
    }

    function isRegistered(address account) public view returns (bool) {
        return _status[account] != AccountStatus.None;
    }

    function isAuthorized(address account) public view returns (bool) {
        return _status[account] == AccountStatus.Authorized;
    }

    modifier onlyOwner() {
        require(msg.sender == _owner, "Solo el creador puede hacer esta llamada");
        _;
    }

    modifier onlyAuthorized(address account) {
        require(_status[account] == AccountStatus.Authorized, "No autorizado");
        _;
    }

    modifier callExists(bytes32 callId) {
        require(address(_calls[callId].cfp) != address(0), "El llamado no existe");
        _;
    }

    modifier callNotExists(bytes32 callId) {
        require(address(_calls[callId].cfp) == address(0), "El llamado ya existe");
        _;
    }
}
