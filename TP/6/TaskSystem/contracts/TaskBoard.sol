// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./Task.sol";

/// @title Tablero de tareas
/// @notice Crea tareas, registra sus estados y mantiene listados por etapa.
contract TaskBoard is ITaskRegistry {
     // Registra que una tarea pasó a estado InProgress.
    // Requisitos:
    //  * El emisor debe ser una tarea registrada.
    //  * La tarea no debe estar en progreso ni finalizada.
    // Efectos:
    //  * Quita la tarea de `todo`.
    //  * Actualiza su estado e índice.
    //  * La agrega al arreglo `inProgress`.
    //  * Emite `TaskMovedToInProgress`.
    function taskStarted() public  {
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
    function taskCompleted() public  {
    }
}