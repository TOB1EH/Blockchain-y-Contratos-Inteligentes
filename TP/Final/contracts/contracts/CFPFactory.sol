//SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./CFP.sol";

contract CFPFactory {
    // Evento que se emite cuando se crea un llamado a presentación de propuestas
    event CFPCreated(address creator, bytes32 callId, CFP cfp);

    // Evento que se emite cuando alguien se registra para crear llamados
    event CreatorRegistered(address indexed creator);

    // Evento que se emite cuando el dueño de la factoría autoriza a una cuenta para crear llamados
    event CreatorAuthorized(address indexed creator);

    // Evento que se emite cuando el dueño de la factoría quita la autorización a una cuenta para crear llamados
    event CreatorUnauthorized(address indexed creator);

    // Estructura que representa un llamado
    struct CallForProposals {
        address creator;
        CFP cfp;
    }

    /* Estado de cuenta */
    enum AccountStatus {
        None,           // No se ha registrado
        Pending,        // Se ha registrado pero no se ha autorizado
        Authorized      // Se ha autorizado a crear llamados
    }

    mapping(address => AccountStatus) private _status; // Mapea cada cuenta a su estado de registro

    /* Variable de estados */
    address private _owner; // dirección del dueño de la factoría

    mapping(bytes32 => CallForProposals) private _calls; // mapea cada callId a su llamado asociado

    address[] private _creators; // lista ordenada de creadores (sin repeticiones)
    mapping(address => bool) private _isCreator; // mapea cada cuenta a un booleano que indica si es creador o no
    mapping(address => bytes32[]) private _createdBy; // mapea cada creador a la lista ordenada de callIds de los llamados que ha creado

    address[] private _pending; // lista ordenada de cuentas que se han registrado pero no se han autorizado (sin repeticiones)
    mapping(address => uint256) private _pendingIndex; // mapea cada cuenta pendiente a su índice en la lista de pendientes (más 1, para distinguir el caso en que no está pendiente)

    /**
     * Construye la factoría, estableciendo al emisor del mensaje como dueño de la factoría.
     */
    constructor() {
        _owner = msg.sender;
    }

    // Dirección del dueño de la factoría
    function owner() public view returns (address) {
        return _owner;
    }

    // Devuelve el llamado asociado con un callId
    function calls(bytes32 callId)
    // Devuelve el llamado asociado con un callId, o un llamado vacío si no existe un llamado con ese callId
        public view returns (CallForProposals memory)
    {
        return _calls[callId];
    }

    // Devuelve la dirección de un creador de la lista de creadores
    function creators(uint index) public view returns (address) {
        return _creators[index];
    }

    /** Crea un llamado, con un identificador y un tiempo de cierre
     *  Si ya existe un llamado con ese identificador, revierte con el mensaje de error "El llamado ya existe"
     *  Si el emisor no está autorizado a crear llamados, revierte con el mensaje "No autorizado"
     */
    function create(bytes32 callId, uint256 timestamp)
        public
        onlyAuthorized(msg.sender) // Verifica que el emisor del mensaje esté autorizado a crear llamados
        callNotExists(callId) // Verifica que no exista un llamado con el mismo callId
        returns (CFP)
    {
        return _create(callId, timestamp, msg.sender);
    }

    /**
     * Crea un llamado, estableciendo a `creator` como creador del mismo.
     * Sólo puede ser invocada por el dueño de la factoría.
     * Se comporta en todos los demás aspectos como `createFor(bytes32 callId, uint timestamp)`
     */
    function createFor(bytes32 callId, uint256 timestamp, address creator)
    // Verifica que el emisor del mensaje sea el dueño de la factoría, y que `creator` esté autorizado a crear llamados, y que no exista un llamado con el mismo callId
        public onlyOwner onlyAuthorized(creator) callNotExists(callId)
        returns (CFP)
    {
        return _create(callId, timestamp, creator);
    }

    /**
     * Crea un llamado, estableciendo a `creator` como creador del mismo.
     * @param callId identificador del llamado a crear
     * @param timestamp timestamp de cierre del llamado a crear
     * @param creator dirección del creador del llamado a crear
     * @return cfp el llamado creado
     */
    function _create(bytes32 callId, uint256 timestamp, address creator)
        private returns (CFP)
    {
        // Crea el llamado y lo registra en el mapeo de llamados
        CFP cfp = new CFP(callId, timestamp);
        _calls[callId] = CallForProposals({ creator: creator, cfp: cfp });

        // Si el creador no estaba registrado como creador, lo registra y lo agrega a la lista de creadores
        if (!_isCreator[creator]) {
            _isCreator[creator] = true;
            _creators.push(creator);
        }
        _createdBy[creator].push(callId); // Agrega el callId a la lista de llamados creados por el creador

        emit CFPCreated(creator, callId, cfp); // Emite el evento de creación de llamado
        return cfp;
    }

    // Devuelve la cantidad de cuentas que han creado llamados.
    function creatorsCount() public view returns (uint256) {
        return _creators.length;
    }

    /// Devuelve el identificador del llamado que está en la posición `index` de la lista de llamados creados por `creator`
    function createdBy(
        address creator,
        uint256 index
    ) public view returns (bytes32) {
        return _createdBy[creator][index];
    }

    // Devuelve la cantidad de llamados creados por `creator`
    function createdByCount(address creator) public view returns (uint256)
    {
        return _createdBy[creator].length;
    }

    /** Permite a un usuario registrar una propuesta, para un llamado con identificador `callId`.
     *  Si el llamado no existe, revierte con el mensaje  "El llamado no existe".
     *  Registra la propuesta en el llamado asociado con `callId` y pasa como creador la dirección del emisor del mensaje.
     */
    function registerProposal(bytes32 callId, bytes32 proposal) public callExists(callId)
    {
        _calls[callId].cfp.registerProposalFor(proposal, msg.sender);
    }

    /** Permite que una cuenta se registre para poder crear llamados.
     *  El registro queda en estado pendiente hasta que el dueño de la factoría lo autorice.
     *  Si ya se ha registrado, revierte con el mensaje "Ya se ha registrado"
     */
    function register() public
    {
        // Verifica que la cuenta no se haya registrado previamente, es decir, que su estado sea None
        require(_status[msg.sender] == AccountStatus.None, "Ya se ha registrado");
        _status[msg.sender] = AccountStatus.Pending; // Cambia el estado de la cuenta a Pending
        _pendingIndex[msg.sender] = _pending.length; // Guarda el índice de la cuenta en la lista de pendientes
        _pending.push(msg.sender); // Agrega la cuenta a la lista de pendientes
        emit CreatorRegistered(msg.sender); // Emite el evento de registro de creador
    }

    /** Autoriza a una cuenta a crear llamados.
     *  Sólo puede ser ejecutada por el dueño de la factoría.
     *  En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
     *  Si la cuenta se ha registrado y está pendiente, la quita de la lista de pendientes.
     */
    function authorize(address account) public onlyOwner
    {
        _removeFromPendingIfExists(account);
        _status[account] = AccountStatus.Authorized; // Cambia el estado de la cuenta a Authorized
        emit CreatorAuthorized(account); // Emite el evento de autorización de creador
    }

    /** Quita la autorización de una cuenta para crear llamados.
     *  Sólo puede ser ejecutada por el dueño de la factoría.
     *  En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
     *  Si la cuenta se ha registrado y está pendiente, la quita de la lista de pendientes.
     */
    function unauthorize(address account) public onlyOwner
    {
        _removeFromPendingIfExists(account);
        _status[account] = AccountStatus.None;
        emit CreatorUnauthorized(account); // Emite el evento de desautorización de creador
    }

    /**
     * Si la cuenta se ha registrado y está pendiente, la quita de la lista de pendientes.
     * @param account dirección de la cuenta a quitar de la lista de pendientes, si es que está pendiente
     */
    function _removeFromPendingIfExists(address account) private {
        // Si la cuenta no está pendiente, no hace nada
        if (_status[account] != AccountStatus.Pending) return;

        // Por el contrario si la cuenta está pendiente, la quita de la lista de pendientes:
        uint256 index = _pendingIndex[account];
        uint256 last  = _pending.length - 1;

        // Para quitar la cuenta de la lista de pendientes, mueve la última cuenta de la lista a la posición de la cuenta a quitar, y luego quita la última posición de la lista
        if (index < last) {
            address moved = _pending[last];
            _pending[index] = moved;
            _pendingIndex[moved] = index;
        }
        _pending.pop();
    }

    // Devuelve la lista de todas las registraciones pendientes.
    // Sólo puede ser ejecutada por el dueño de la factoría
    // En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
    function getAllPending() public view onlyOwner returns (address[] memory) {
        return _pending;
    }

    // Devuelve la registración pendiente con índice `index`
    // Sólo puede ser ejecutada por el dueño de la factoría
    // En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
    function getPending(uint256 index) public view onlyOwner returns (address) {
        return _pending[index];
    }

    // Devuelve la cantidad de registraciones pendientes.
    // Sólo puede ser ejecutada por el dueño de la factoría
    // En caso contrario revierte con el mensaje "Solo el creador puede hacer esta llamada".
    function pendingCount() public view onlyOwner returns (uint256) {
        return _pending.length;
    }

    // Devuelve verdadero si una cuenta se ha registrado, tanto si su estado es pendiente como si ya se la ha autorizado.
    function isRegistered(address account) public view returns (bool) {
        // Devuelve verdadero si el estado de la cuenta es distinto de None, es decir, si es Pending o Authorized
        return _status[account] != AccountStatus.None;
    }

    // Devuelve verdadero si una cuenta está autorizada a crear llamados.
    function isAuthorized(address account) public view returns (bool) {
        return _status[account] == AccountStatus.Authorized;
    }

    /* Modifiers */
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
