# Trabajo práctico 6

Este sistema representa un sistema descentralizado de gestión de tareas.

El contrato `TaskBoard` implementa la interface `ITaskRegistry` definida en `Task.sol`, permite crear instancias del contrato `Task` provisto, y brinda cierta información sobre el estado de las tareas creadas.

## Consigna

1. Implemente los contratos `TaskBoard` y `Task` de acuerdo a las especificaciones, de manera que pasen todos los casos de prueba. Todos los prerequisitos de las funciones debe especificarse mediante modificadores (_modifiers_).
2. Implemente la función `listTaskByAssignee()` del script `list-tasks-by-assignee.js` de manera que cumpla las especificaciones y pase todos los casos de prueba.

## Contratos

### El contrato `Task`

Este contrato modela el ciclo de vida de una tarea individual. La tarea se describe mediante una `string` que se pasa como parámetro del constructor. El constructor recibe además un segundo parámetro que corresponde a la dirección del _solicitante_ (quien reporta o crea la tarea).

El creador de la tarea puede asignarla a un trabajador mediante el método `assign`, que recibe la dirección del usuario asignado. El trabajador asignado es el único responsable de iniciar y completar la tarea cambiando sus estados.

#### Métodos

##### `function description() public view returns (string memory)`

Devuelve una `string` que representa la descripción de la tarea provista en el constructor.

##### `function reporter() public view returns (address)`

Devuelve la dirección del usuario que reportó o creó la tarea.

##### `function assignee() public view returns (address)`

Devuelve la dirección del usuario asignado para resolver la tarea.

##### `function assign(address worker) public`

Asigna la tarea a un trabajador específico.

* Sólo puede ser invocada por el _solicitante_.
* Sólo se puede invocar si la tarea está en estado pendiente (no ha comenzado).

##### `function start() public`

Habilita el comienzo de la resolución de la tarea.

* Sólo puede ser invocada por el _responsable asignado_ (trabajador asignado).
* Sólo puede ser llamada si la tarea está en estado pendiente.
* Cambia el estado interno a iniciada.
* Invoca el método `taskStarted()` de la factoría (el tablero) que creó esta tarea. Esto significa que si el contrato no fue creado por una factoría que implemente la interface `ITaskRegistry`, el método va a fallar.

##### `function started() public view returns (bool)`

Devuelve verdadero si la tarea ha comenzado, y falso en caso contrario.

##### `function complete() public`

Marca la tarea como completada.

* Sólo puede ser invocada por el _responsable asignado_.
* Sólo puede ser invocada si la tarea ya ha comenzado y está en progreso.
* Cambia el estado interno a completada.
* Invoca el método `taskCompleted()` de la factoría que creó esta tarea.

##### `function completed() public view returns (bool)`

Devuelve verdadero si la tarea ha terminado, y falso en caso contrario.

##### `function assignedAt() public view returns (uint256)`

Devuelve el timestamp Unix (en segundos) del momento en que la tarea fue asignada mediante `assign`. Devuelve cero si la tarea no ha sido asignada aún.

##### `function startedAt() public view returns (uint256)`

Devuelve el timestamp Unix (en segundos) del momento en que la tarea fue iniciada mediante `start`. Devuelve cero si la tarea no ha comenzado aún.

##### `function completedAt() public view returns (uint256)`

Devuelve el timestamp Unix (en segundos) del momento en que la tarea fue completada mediante `complete`. Devuelve cero si la tarea no ha finalizado aún.

#### Eventos del contrato `Task`

##### `event TaskAssigned(address reporter, address assignee, uint256 timestamp)`

Se emite cuando el solicitante asigna la tarea mediante `assign`.

* `reporter`: dirección del solicitante que realiza la asignación.
* `assignee`: dirección del responsable asignado.
* `timestamp`: momento de la asignación como timestamp Unix en segundos (`block.timestamp`).

##### `event TaskStarted(address assignee, uint256 timestamp)`

Se emite cuando el responsable asignado inicia la tarea mediante `start`.

* `assignee`: dirección del responsable asignado que inicia la tarea.
* `timestamp`: momento de inicio como timestamp Unix en segundos.

##### `event TaskCompleted(address assignee, uint256 timestamp)`

Se emite cuando el responsable asignado completa la tarea mediante `complete`.

* `assignee`: dirección del responsable asignado que completa la tarea.
* `timestamp`: momento de finalización como timestamp Unix en segundos.

#### Errores

Los contratos producen los siguientes errores (dependiendo de la implementación de sus modificadores):

* Cuando alguien que no es el _solicitante_ intenta realizar una actividad reservada al mismo:
  * `"Solo el reporter puede realizar esta acción"`
* Cuando alguien que no es el _responsable asignado_ intenta realizar una actividad reservada al mismo:
  * `"Solo el assignee puede realizar esta acción"`
* Cuando se realiza una acción que requiere que la tarea no haya comenzado, y eso ya ha ocurrido:
  * `"La tarea ya ha comenzado"`
* Cuando se realiza una acción que requiere que la tarea esté en progreso, y no lo está (o ya finalizó):
  * `"La tarea no está en progreso"`

### La interface `ITaskRegistry`

Esta interface requiere que se implementen los siguientes métodos:

#### `function taskStarted() external`

Esta función es invocada por el contrato `Task` para indicar que la tarea ha pasado a estado "En progreso".

#### `function taskCompleted() external`

Esta función es invocada por el contrato `Task` para indicar que la tarea ha finalizado.

### El contrato `TaskBoard`

La factoría crea instancias del contrato `Task` y almacena información sobre su estado en el tablero. Se asume que la tarea puede estar en uno de tres estados:

* `ToDo`:
  * La tarea ha sido creada, pero su resolución no ha comenzado.
  * El _solicitante_ puede asignar a un trabajador.
* `InProgress`:
  * El trabajador ha comenzado la tarea.
  * Se encuentra en pleno desarrollo.
* `Done`:
  * La tarea ha sido completada por el trabajador.
  * Sólo se puede consultar la información histórica.

#### Métodos de TaskBoard

##### `function createTask(string memory description) public returns (address taskAddress)`

Esta función crea una tarea (es decir, una instancia del contrato `Task`) pasándole la descripción `description` y el emisor del mensaje (quien será el _solicitante_) como argumentos del constructor. Devuelve la dirección del contrato creado.

##### `function todo(uint index) public view returns (address taskAddress)`

Devuelve el contrato que está en la posición `index` de la lista de tareas por hacer (`ToDo`).

##### `function inProgress(uint index) public view returns (address taskAddress)`

Devuelve el contrato que está en la posición `index` de la lista de tareas en progreso (`InProgress`).

##### `function done(uint index) public view returns (address taskAddress)`

Devuelve el contrato que está en la posición `index` de la lista de tareas finalizadas (`Done`).

##### `function todoCount() public view returns (uint256)`

Devuelve la cantidad total de tareas actualmente en la lista `ToDo`.

##### `function inProgressCount() public view returns (uint256)`

Devuelve la cantidad total de tareas actualmente en la lista `InProgress`.

##### `function doneCount() public view returns (uint256)`

Devuelve la cantidad total de tareas actualmente en la lista `Done`.

##### `function todoByAssignee(address worker) public view returns (address[] memory)`

Devuelve la lista de tareas en `ToDo` cuyo responsable asignado coincide con `worker`.

##### `function inProgressByAssignee(address worker) public view returns (address[] memory)`

Devuelve la lista de tareas en `InProgress` cuyo responsable asignado coincide con `worker`.

##### `function doneByAssignee(address worker) public view returns (address[] memory)`

Devuelve la lista de tareas en `Done` cuyo responsable asignado coincide con `worker`.

#### Eventos del contrato `TaskBoard`

##### `event TaskCreated(address taskAddress, address reporter, string description)`

Se emite cuando el tablero crea una nueva tarea mediante `createTask`.

* `taskAddress`: dirección del contrato `Task` creado.
* `reporter`: dirección del solicitante que crea la tarea.
* `description`: descripción textual usada al crear la tarea.

##### `event TaskMovedToInProgress(address taskAddress, uint256 index)`

Se emite cuando una tarea pasa de `ToDo` a `InProgress` mediante `taskStarted`.

* `taskAddress`: dirección del contrato `Task` que cambió de estado.
* `index`: posición final de la tarea dentro del arreglo `inProgress`.

##### `event TaskMovedToDone(address taskAddress, uint256 index)`

Se emite cuando una tarea pasa de `InProgress` a `Done` mediante `taskCompleted`.

* `taskAddress`: dirección del contrato `Task` que cambió de estado.
* `index`: posición final de la tarea dentro del arreglo `done`.

## Resumen de eventos

| Contrato    | Evento                  | Parámetros                                                        | Emitido en              |
|-------------|-------------------------|-------------------------------------------------------------------|-------------------------|
| `Task`      | `TaskAssigned`          | `address reporter`, `address assignee`, `uint256 timestamp`       | `assign()`              |
| `Task`      | `TaskStarted`           | `address assignee`, `uint256 timestamp`                           | `start()`               |
| `Task`      | `TaskCompleted`         | `address assignee`, `uint256 timestamp`                           | `complete()`            |
| `TaskBoard` | `TaskCreated`           | `address taskAddress`, `address reporter`, `string description`   | `createTask()`          |
| `TaskBoard` | `TaskMovedToInProgress` | `address taskAddress`, `uint256 index`                            | `taskStarted()`         |
| `TaskBoard` | `TaskMovedToDone`       | `address taskAddress`, `uint256 index`                            | `taskCompleted()`       |

## Despliegue sin Ignition

Este proyecto no usa `ignition/`. El despliegue se realiza con scripts en `scripts/`.

### Scripts disponibles

#### `npm run deploy`

Despliega solamente el contrato `TaskBoard`.

#### `npm run deploy:sample`

Despliega `TaskBoard`, crea tareas de ejemplo para tres responsables asignados distintos y las deja en estados mixtos (`pending`, `in-progress`, `done`).

Además imprime:

* `TASKBOARD_ADDRESS`
* `ASSIGNEE_1`
* `ASSIGNEE_2`
* `ASSIGNEE_3`

#### `npm run deploy:sample:localhost`

Igual que `deploy:sample`, pero forzando la red `localhost`:

```bash
npm run deploy:sample:localhost
```

Este comando es el recomendado para pruebas interactivas junto con `npx hardhat node`.

#### `npm run list-tasks -- ...`

Ejecuta el script de consulta de tareas por responsable asignado y estado.

Parámetros:

* `--board`: dirección de `TaskBoard`.
* `--assignee`: dirección del responsable asignado a consultar.
* `--state`: `pending`, `in-progress` o `done`.
* `--timestamps`: `contract` (leer timestamps on-chain) o `events` (inferir timestamps desde eventos).
* `--rpc` (opcional): URI JSON-RPC, por defecto `http://localhost:8545`.

Ejemplo:

```bash
npm run list-tasks -- \
  --board 0x5FbDB2315678afecb367f032d93F642f64180aa3 \
  --assignee 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
  --state done \
  --timestamps contract \
  --rpc http://localhost:8545
```

### Desplegar `TaskBoard`

1. Instalar dependencias:

    ```bash
    npm install
    ```

2. Ejecutar el script de despliegue (asegúrate de crear uno en `scripts/deploy.js`):

    ```bash
    npm run deploy
    ```
  
El comando imprime la dirección del contrato desplegado.
