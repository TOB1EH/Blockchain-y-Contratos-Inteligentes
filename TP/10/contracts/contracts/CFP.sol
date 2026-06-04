//SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract CFP {
    // Evento que se emite cuando alguien registra una propuesta
    event ProposalRegistered(
        bytes32 proposal,
        address sender,
        uint256 blockNumber
    );

    /* Variables de Estado */
    bytes32 private _callId;                                // identificador del llamado
    uint256 private _closingTime;                           // timestamp del cierre de la recepción de propuestas
    address private _creator;                               // dirección del creador del llamado
    bytes32[] private _proposals;                           // lista ordenada de propuestas

    mapping(bytes32 => ProposalData) private _proposalData; // mapea cada propuesta a su información asociada

    // Estructura que representa una propuesta
    struct ProposalData {
        address sender;
        uint256 blockNumber;
        uint256 timestamp;
    }

    // Estructura que representa una entrega asociada a una propuesta
    struct DeliveryData {
        bytes32 filesRoot;      // raiz del arbol de Merkle de los archivos entregados
        address sender;         // dirección del emisor de la entrega (quien entrego)
        uint256 blockNumber;    // número de bloque en el que se registró la entrega
        uint256 timestamp;      // timestamp en el que se registró la entrega
        bool delivered;         // indica si la entrega ha sido realizada o no (bandera)
    }

    // Mapea cada propuesta a su entrega asociada.
    // Se usa clave bytes32 para mapear la propuesta, ya que es el tipo de dato que se
    // usa para identificar las propuestas (El proposalId, que es unico para cada propuesta)
    mapping(bytes32 => DeliveryData) private _deliveries;

    // Evento que se emite cuando alguien registra una entrega asociada a una propuesta
    event FilesDelivered(
        bytes32 indexed proposalId,
        bytes32 filesRoot,
        address sender,
        uint256 timestamp
    );

    /**
     * Permite registrar la entrega de archivos asociada a una propuesta.
     * @param proposalId identificador de la propuesta a la que se asocia la entrega
     * @param filesRoot raíz del árbol de Merkle de los archivos entregados
     */
    function registerDelivery(bytes32 proposalId, bytes32 filesRoot) public {
        require(block.timestamp > _closingTime, "La convocatoria no ha cerrado");
        require(_proposalData[proposalId].blockNumber != 0, "La propuesta no existe");
        require(!_deliveries[proposalId].delivered, "La entrega ya fue registrada");

        // Se crea la estructura de datos de la entrega y se almacena en el mapping de
        // entregas, asociada a la propuesta correspondiente (proposalId)
        _deliveries[proposalId] = DeliveryData({
            filesRoot:   filesRoot,
            sender:      msg.sender,
            blockNumber: block.number,
            timestamp:   block.timestamp,
            delivered:   true
        });

        // Se emite el evento FilesDelivered con la información de la entrega registrada
        emit FilesDelivered(proposalId, filesRoot, msg.sender, block.timestamp);
    }

    /**
     * Devuelve los datos asociados a la entrega de archivos de una propuesta.
     * @param proposalId identificador de la propuesta de la que se quieren obtener los datos de entrega
     */
    function deliveryData(bytes32 proposalId) public view returns (DeliveryData memory) {
        return _deliveries[proposalId];
    }


    // Devuelve los datos asociados con una propuesta
    function proposalData(bytes32 proposal) public view returns (ProposalData memory) {
        return _proposalData[proposal];
    }

    // Devuelve la propuesta que está en la posición `index` de la lista de propuestas registradas
    function proposals(uint index) public view returns (bytes32) {
        return _proposals[index];
    }

    // Timestamp del cierre de la recepción de propuestas
    function closingTime() public view returns (uint256) {
        return _closingTime;
    }

    // Identificador de este llamado
    function callId() public view returns (bytes32) {
        return _callId;
    }

    // Creador de este llamado
    function creator() public view returns (address) {
        return _creator;
    }


    /** Construye un llamado con un identificador y un tiempo de cierre.
     *  Si el `timestamp` del bloque actual es mayor o igual al tiempo de cierre especificado,
     *  revierte con el mensaje "El cierre de la convocatoria no puede estar en el pasado".
     */
    constructor(bytes32 callId_, uint256 closingTime_) {
        require(block.timestamp < closingTime_,
                "El cierre de la convocatoria no puede estar en el pasado");
        _callId         = callId_;
        _closingTime    = closingTime_;
        _creator        = msg.sender;
    }

    // Devuelve la cantidad de propuestas presentadas
    function proposalCount() public view returns (uint256) {
        return _proposals.length;
    }

    /** Permite registrar una propuesta espec.
     *  Registra al emisor del mensaje como emisor de la propuesta.
     *  Si el timestamp del bloque actual es mayor que el del cierre del llamado,
     *  revierte con el error "Convocatoria cerrada"
     *  Si ya se ha registrado una propuesta igual, revierte con el mensaje
     *  "La propuesta ya ha sido registrada"
     *  Emite el evento `ProposalRegistered`
     */
    function registerProposal(bytes32 proposal)
    // Verifica que el timestamp del bloque actual sea menor o igual al tiempo de cierre, y que la propuesta no haya sido registrada previamente
        public beforeClose notRegistered(proposal)
    {
        _register(proposal, msg.sender);
    }

    /** Permite registrar una propuesta especificando un emisor.
     *  Sólo puede ser ejecutada por el creador del llamado. Si no es así, revierte
     *  con el mensaje "Solo el creador puede hacer esta llamada"
     *  Si el timestamp del bloque actual es mayor que el del cierre del llamado,
     *  revierte con el error "Convocatoria cerrada"
     *  Si ya se ha registrado una propuesta igual, revierte con el mensaje
     *  "La propuesta ya ha sido registrada"
     *  Emite el evento `ProposalRegistered`
     */
    function registerProposalFor(bytes32 proposal, address sender)
        public onlyCreator beforeClose notRegistered(proposal)
    {
        _register(proposal, sender);
    }

    /** Devuelve el timestamp en el que se ha registrado una propuesta.
     *  Si la propuesta no está registrada, devuelve cero.
     */
    function proposalTimestamp(bytes32 proposal) public view returns (uint256) {
        return _proposalData[proposal].timestamp;
    }

    /**
     * Registra una propuesta con un identificador y un emisor.
     * @param proposal identificador de la propuesta a registrar
     * @param sender dirección del emisor de la propuesta
     */
    function _register(bytes32 proposal, address sender) private {
        // Registra la propuesta con su información asociada
        _proposalData[proposal] = ProposalData({
            sender:      sender,
            blockNumber: block.number,
            timestamp:   block.timestamp
        });
        // Agrega la propuesta a la lista de propuestas registradas
        _proposals.push(proposal);
        emit ProposalRegistered(proposal, sender, block.number);
    }

    /* Modifiers */
    modifier onlyCreator() {
        require(msg.sender == _creator, "Solo el creador puede hacer esta llamada");
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
