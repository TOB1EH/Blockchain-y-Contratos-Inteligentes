// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./Task.sol";

/// @title Tablero de tareas
/// @notice Crea tareas, registra sus estados y mantiene listados por etapa.
contract TaskBoard is ITaskRegistry {

    enum TaskStatus {
        None,
        ToDo,
        InProgress,
        Done
    }
    struct TaskInfo {
        TaskStatus status;
        uint index; // índice de la tarea en su arreglo correspondiente
    }
    // Mapeo de tareas registradas: dirección de la tarea => información de la tarea
    mapping(address => TaskInfo) private _taskInfo;

    // Arreglos de tareas por estado
    address[] private _todo;
    address[] private _inProgress;
    address[] private _done;

    // Eventos que se emiten cuando una tarea cambia de estado.
    event TaskCreated(address taskAddress, address reporter, string description);
    event TaskMovedToInProgress(address taskAddress, uint256 index);
    event TaskMovedToDone(address taskAddress, uint256 index);

    // Modifiers
    modifier onlyRegisteredTask() {
        require(
            _taskInfo[msg.sender].status != TaskStatus.None,
            "El emisor del mensaje no es una tarea creada por este tablero"
        );
        _;
    }

    modifier taskIsToDo() {
        require(
            _taskInfo[msg.sender].status == TaskStatus.ToDo,
            "La tarea no esta en estado pendiente"
        );
        _;
    }

    modifier taskIsInProgress() {
        require(
            _taskInfo[msg.sender].status == TaskStatus.InProgress,
            "La tarea no esta en progreso"
        );
        _;
    }

    modifier notInProgress() {
        require(
            _taskInfo[msg.sender].status != TaskStatus.InProgress,
            "La tarea ya esta en progreso"
        );
        _;
    }

    modifier notDone() {
        require(
            _taskInfo[msg.sender].status != TaskStatus.Done,
            "La tarea ya fue completada"
        );
        _;
    }

    // Crea una nueva tarea y la agrega a ToDo
    function createTask(string memory description) public returns (address taskAddress) {
        // Requiere que la descripción no esté vacía para evitar crear tareas sin información.
        require(bytes(description).length > 0, "Description cannot be empty");
        
        // Crear la tarea usando la factoría, registrar su estado e índice, agregarla al arreglo de pendientes y emitir el evento correspondiente.
        Task task = new Task(description, msg.sender);
        taskAddress = address(task);

        _taskInfo[taskAddress] = TaskInfo(TaskStatus.ToDo, _todo.length);
        _todo.push(taskAddress);

        emit TaskCreated(taskAddress, msg.sender, description);
    }

    // Registra que una tarea pasó a estado InProgress.
    // Requisitos:
    //  * El emisor debe ser una tarea registrada.
    //  * La tarea no debe estar en progreso ni finalizada.
    // Efectos:
    //  * Quita la tarea de `todo`.
    //  * Actualiza su estado e índice.
    //  * La agrega al arreglo `inProgress`.
    //  * Emite `TaskMovedToInProgress`.
    function taskStarted() public onlyRegisteredTask notInProgress notDone {
       address taskAddress = msg.sender;

        // Quitar de _todo usando swap con el último
        _removeFromArray(taskAddress, _todo);

        // Agregar a _inProgress
        _taskInfo[taskAddress].status = TaskStatus.InProgress;
        _taskInfo[taskAddress].index  = _inProgress.length;
        _inProgress.push(taskAddress);

        emit TaskMovedToInProgress(taskAddress, _taskInfo[taskAddress].index);
    }

    // Registra que una tarea pasó a estado Done.
    // Requisitos:
    //  * El emisor debe ser una tarea registrada.
    //  * La tarea no debe estar finalizada.
    //  * La tarea debe estar en progreso.
    // Efectos:
    //  * Quita la tarea de `inProgress`.
    //  * Actualiza su estado e índice.
    //  * La agrega al arreglo `done`.
    //  * Emite `TaskMovedToDone`.
    function taskCompleted() public onlyRegisteredTask notDone taskIsInProgress {
        address taskAddress = msg.sender;

        // Quitar de _inProgress usando swap con el último
        _removeFromArray(taskAddress, _inProgress);

        // Agregar a _done
        _taskInfo[taskAddress].status = TaskStatus.Done;
        _taskInfo[taskAddress].index  = _done.length;
        _done.push(taskAddress);

        emit TaskMovedToDone(taskAddress, _taskInfo[taskAddress].index);
    }

    function tasks(address taskAddress) public view returns (TaskInfo memory) {
        return _taskInfo[taskAddress];
    }

    // Getters de listas
    function todo(uint index) public view returns (address) {
        return _todo[index];
    }

    function inProgress(uint index) public view returns (address) {
        return _inProgress[index];
    }

    function done(uint index) public view returns (address) {
        return _done[index];
    }

    function todoCount() public view returns (uint256) {
        return _todo.length;
    }

    function inProgressCount() public view returns (uint256) {
        return _inProgress.length;
    }

    function doneCount() public view returns (uint256) {
        return _done.length;
    }

    // Filtros por assignee: misma estrategia de dos pasadas que winningProposals
    function todoByAssignee(address worker) public view returns (address[] memory) {
        return _filterByAssignee(_todo, worker);
    }

    function inProgressByAssignee(address worker) public view returns (address[] memory) {
        return _filterByAssignee(_inProgress, worker);
    }

    function doneByAssignee(address worker) public view returns (address[] memory) {
        return _filterByAssignee(_done, worker);
    }

    // Helpers privados
    function _filterByAssignee(
        address[] storage list,
        address worker
    ) private view returns (address[] memory result) {
        // Pasada 1: contar coincidencias
        uint count = 0;
        for (uint i = 0; i < list.length; i++) {
            if (Task(list[i]).assignee() == worker) {
                count++;
            }
        }
        // Pasada 2: llenar array solo si hay resultados
        if (count == 0) {
            return new address[](0);
        }

        result = new address[](count);
        uint j = 0;
        for (uint i = 0; i < list.length; i++) {
            if (Task(list[i]).assignee() == worker) {
                result[j] = list[i];
                j++;
            }
        }
    }

    function _removeFromArray(address taskAddress, address[] storage array) private {
        uint index = _taskInfo[taskAddress].index;
        uint last  = array.length - 1;
        if (index < last) {
            // Mover el último al lugar del que se va
            array[index] = array[last];
            // Actualizar el índice del que se movió
            _taskInfo[array[index]].index = index;
        }
        array.pop();
    }
}