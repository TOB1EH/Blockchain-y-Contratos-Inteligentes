//SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.19;

/// @title Votación
contract Ballot {

    /* Variables para guardar si la votacion empezo o termino */
    bool private _started;
    bool private _ended;

    // Esta estructura representa a un votante
    struct Voter {
        bool canVote; // si es verdadero, la persona puede votar
        bool voted; // si es verdadero, la persona ya votó
        uint vote; // índice de la propuesta elegida.
    }

    // Este tipo representa a una propuesta
    struct Proposal {
        bytes32 name; // nombre (hasta 32 bytes)
        uint voteCount; // votos recibidos por la propuesta
    }

    address public chairperson;

    // Variable de estado con los votantes
    mapping(address => Voter) public voters;
    // Cantidad de votantes
    uint public numVoters;

    // Arreglo dinámico de propuestas.
    Proposal[] public proposals;

    /// Crea una nueva votación para elegir entre `proposalNames`.
    constructor(bytes32[] memory proposalNames) {
        chairperson = msg.sender;
        require(
            proposalNames.length > 1,
            "There should be at least two proposals."
        );
        for (uint i = 0; i < proposalNames.length; i++) {
            // `Proposal({...})` crea un objeto temporal
            // de tipo Proposal y  `proposals.push(...)`
            // lo agrega al final de `proposals`.
            proposals.push(Proposal({name: proposalNames[i], voteCount: 0}));
        }
    }

    // Le da a `voter` el derecho a votar.
    // Solamente puede ser ejecutado por `chairperson`.
    // No se puede hacer si
    //  * El votante ya puede votar
    //  * La votación ya comenzó
    // Actualiza numVoters
    function giveRightToVote(address voter) public onlyChairperson {
        require(!_started, "Voting has already started.");
        // Se elimina porque si el votante no puede votar (canVote = false), entonces
        // tampoco pudo haber votado (voted = false). Por lo tanto, no es necesario
        // verificar que el votante no haya votado.
        // require(!voters[voter].voted, "The voter already voted.");
        require(!voters[voter].canVote, "Voter already has right to vote.");
        voters[voter].canVote = true;
        numVoters += 1;
    }

    // Quita a `voter` el derecho a votar.
    // Solamente puede ser ejecutado por `chairperson`.
    // No se puede hacer si
    //  * El votante no puede votar
    //  * La votación ya comenzó
    // Actualiza numVoters
    function withdrawRightToVote(address voter) public onlyChairperson{
        require(!_started, "Voting has already started."); // No se puede ejecutar si la votación ya comenzó
        require(voters[voter].canVote, "Voter has no right to vote."); // No se puede ejecutar si el votante no puede votar
        voters[voter].canVote = false; // Se le quita el derecho a votar
        numVoters -= 1;
    }

    // Le da a todas las direcciones contenidas en `list` el derecho a votar.
    // Solamente puede ser ejecutado por `chairperson`.
    // No se puede ejecutar si la votación ya comenzó
    // Si el votante ya puede votar, no hace nada.
    // Actualiza numVoters
    function giveAllRightToVote(address[] memory list) public onlyChairperson {
        require(!_started, "Voting has already started.");
        for (uint i = 0; i < list.length; i++) {
            if (!voters[list[i]].canVote) { // Si el votante "i" no tiene derecho a votar
                voters[list[i]].canVote = true; // Se le da derecho a votar
                numVoters += 1; // Se actualiza el contador de votantes
            }
        }
    }

    // Devuelve la cantidad de propuestas
    function numProposals() public view returns (uint) {
        return proposals.length;
    }

    // Habilita el comienzo de la votación
    // Solo puede ser invocada por `chairperson`
    // No puede ser invocada una vez que la votación ha comenzado
    function start() public onlyChairperson {
        require(!_started, "Voting has already started.");
        _started = true;
    }

    // Indica si la votación ha comenzado
    function started() public view returns (bool) {
        return _started;
    }

    // Finaliza la votación
    // Solo puede ser invocada por `chairperson`
    // Solo puede ser invocada una vez que la votación ha comenzado
    // No puede ser invocada una vez que la votación ha finalizado
    function end() public onlyChairperson {
        require(_started, "Voting has not started yet.");
        require(!_ended, "Voting has already ended.");
        _ended = true;
    }

    // Indica si la votación ha finalizado
    function ended() public view returns (bool) {
        return _ended;
    }

    // Vota por la propuesta `proposals[proposal].name`.
    // Requiere que la votación haya comenzado y no haya terminado
    // Si `proposal` está fuera de rango, lanza
    // una excepción y revierte los cambios.
    // El votante tiene que estar habilitado
    // No se puede votar dos veces
    // No se puede votar si la votación aún no comenzó
    // No se puede votar si la votación ya terminó
    function vote(uint proposal) public {
        require(_started, "Voting has not started yet."); // No se puede votar si la votación aún no comenzó
        require(!_ended, "Voting has already ended."); // No se puede votar si la votación ya terminó

        // Se crea una variable de tipo Voter llamada "sender" que hace referencia al votante que envía la transacción (msg.sender).
        Voter storage sender = voters[msg.sender];
        require(sender.canVote, "Has no right to vote");
        require(!sender.voted, "Already voted.");
        sender.voted = true;
        sender.vote = proposal;

        proposals[proposal].voteCount += 1;
    }

    /// Calcula la propuestas ganadoras
    /// Devuelve un array con los índices de las propuestas ganadoras.
    // Solo se puede ejecutar si la votación terminó.
    // Si no hay votos, devuelve un array de longitud 0
    // Si hay un empate en el primer puesto, la longitud
    // del array es la cantidad de propuestas que empatan
    function winningProposals() public view returns (uint[] memory winningProposal_) {
        require(_ended, "Voting has not ended yet.");

        // Encontrar el maximo de votos
        uint maxVotes = 0;
        for (uint i = 0; i < proposals.length; i++) {
            if (proposals[i].voteCount > maxVotes) {
                maxVotes = proposals[i].voteCount;
            }
        }


        // Si no hay votos, devolver array vacio
        if (maxVotes == 0) {
            return new uint[](0);
        }

        // Contas cuantas propuestas tienen el maximo de votos
        uint count = 0;
        for (uint i = 0; i < proposals.length; i++) {
            if (proposals[i].voteCount == maxVotes) {
                count += 1;
            }
        }

        // Llenar el array con los indices de las propuestas ganadoras
        winningProposal_ = new uint[](count);
        uint index = 0;
        for (uint i = 0; i < proposals.length; i++) {
            if (proposals[i].voteCount == maxVotes) {
                winningProposal_[index] = i;
                index++;
            }
        }
    }

    // Devuelve un array con los nombres de las
    // propuestas ganadoras.
    // Solo se puede ejecutar si la votación terminó.
    // Si no hay votos, devuelve un array de longitud 0
    // Si hay un empate en el primer puesto, la longitud
    // del array es la cantidad de propuestas que empatan
    function winners() public view returns (bytes32[] memory winners_) {
        require(_ended, "Voting has not ended yet.");

        // Se obtiene el array con los índices de las propuestas ganadoras
        uint[] memory winningIndices = winningProposals();


        winners_ = new bytes32[](winningIndices.length); // Se crea un array de bytes32 con la misma longitud que el array de índices ganadores
        // Se llena el array de nombres de las propuestas ganadoras utilizando los índices obtenidos previamente
        for (uint i = 0; i < winningIndices.length; i++) {
            winners_[i] = proposals[winningIndices[i]].name;
        }
    }

    // Se define el modificador `onlyChairperson` para reutilizar la verificación de que
    // el remitente de la transacción es el presidente. Este modificador se puede aplicar
    // a cualquier función que deba ser restringida al presidente.
    modifier onlyChairperson() {
        require(
            // `msg.sender` es una variable global que representa la dirección del remitente de la transacción. En este caso, se verifica que el remitente sea el presidente (chairperson) antes de permitir la ejecución de la función.
            msg.sender == chairperson,
            "Only chairperson can invoke this function."
        );
        _;
    }
}
