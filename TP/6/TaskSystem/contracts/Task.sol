// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

// Interfaz que debe implementar el tablero para recibir
// notificaciones de cambios de estado de una tarea.
interface ITaskRegistry {
    // Notifica al tablero que la tarea pasó a estado en progreso.
    function taskStarted() external;

    // Notifica al tablero que la tarea pasó a estado finalizada.
    function taskCompleted() external;
}

/// @title Tarea individual del sistema
contract Task {
    // Variables de estado
    string  private _description;
    address private _reporter;      // quien creó la tarea
    address private _assignee;      // a quién se le asignó la tarea
    address private _board;         // la factoría que creó esta tarea

    bool    private _started;
    bool    private _completed;

    uint256 private _assignedAt;    // timestamp de la última asignación
    uint256 private _startedAt;     // timestamp de cuando se inició la tarea
    uint256 private _completedAt;   // timestamp de cuando se completó la tarea

    // Eventos: se emiten cuando la tarea cambia de estado.
    event TaskAssigned(address indexed reporter, address indexed assignee, uint256 timestamp); // Emite cuando se asigna la tarea a alguien.
    event TaskStarted(address indexed assignee, uint256 timestamp); // Emite cuando la tarea pasa a estado en progreso.
    event TaskCompleted(address indexed assignee, uint256 timestamp); // Emite cuando la tarea pasa a estado finalizada.
    // Se usan parametros indexados para facilitar la búsqueda de eventos por reporter o assignee.

    // Modifiers: validan que ciertas condiciones se cumplan antes de ejecutar una función.
    modifier onlyReporter()
    {
        require(msg.sender == _reporter, "Solo el reporter puede realizar esta accion");
        _;
    }

    modifier onlyAssignee() {
        require(msg.sender == _assignee, "Solo el assignee puede realizar esta accion");
        _;
    }

    modifier notStarted() {
        require(!_started, "La tarea ya ha comenzado");
        _;
    }

    modifier inProgress() {
        require(_started && !_completed, "La tarea no esta en progreso");
        _;
    }

    constructor(string memory description_, address reporter_) {
        _description = description_;
        _reporter = reporter_;
        _board = msg.sender; // La factoría que crea la tarea es el tablero
    }

    // Getters: funciones para obtener información sobre la tarea.
    function description() public view returns (string memory) {
        return _description;
    }

    function reporter() public view returns (address) {
        return _reporter;
    }

    function assignee() public view returns (address) {
        return _assignee;
    }

    function started() public view returns (bool) {
        return _started;
    }

    function completed() public view returns (bool) {
        return _completed;
    }

    function assignedAt() public view returns (uint256) {
        return _assignedAt;
    }

    function startedAt() public view returns (uint256) {
        return _startedAt;
    }

    function completedAt() public view returns (uint256) {
        return _completedAt;
    }

    // Asigna la tarea a un trabajador
    // Solo el reporter puede hacerlo, y solo si no comenzó
    function assign(address worker) public onlyReporter notStarted {
        // Requiere que la dirección del trabajador no sea cero para evitar asignar la tarea a una dirección inválida.
        require(worker != address(0), "Worker address cannot be zero");

        // Asignar la tarea al trabajador, actualizar el timestamp de asignación y emitir el evento correspondiente.
        _assignee   = worker;
        _assignedAt = block.timestamp;
        emit TaskAssigned(_reporter, worker, block.timestamp);
    }

    // Inicia la tarea
    // Solo el assignee puede hacerlo, solo si está pendiente
    function start() public onlyAssignee notStarted {
        _started   = true;
        _startedAt = block.timestamp;
        emit TaskStarted(_assignee, block.timestamp);
        // Notificar al board
        ITaskRegistry(_board).taskStarted();
    }

    // Completa la tarea
    // Solo el assignee puede hacerlo, solo si está en progreso
    function complete() public onlyAssignee inProgress {
        _completed   = true;
        _completedAt = block.timestamp;
        emit TaskCompleted(_assignee, block.timestamp);
        // Notificar al board
        ITaskRegistry(_board).taskCompleted();
    }
}