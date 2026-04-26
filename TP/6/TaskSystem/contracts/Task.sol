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
}