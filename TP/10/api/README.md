# Trabajo Práctico 10 - API REST

## Consigna

Implementar una API REST que interactúe con los contratos `CFP` y `CFPFactory` del directorio `contracts` y permita acceder a sus funcionalidades.

En la API los *hashes*, direcciones y transacciones se expresarán como cadenas hexadecimales de la longitud adecuada y el prefijo "0x". Los valores enteros se expresarán como números decimales. La información temporal (por ejemplo, fecha y hora del cierre de convocatoria), deberá expresarse en formato ISO 8601 en UTC. Las cadenas de caracteres se asumen codificadas en UTF-8.

El contrato `CFPFactory` estará desplegado en un nodo que recibe requerimientos RPC en `http://localhost:8545`. La API debe conectarse con el nodo mediante HTTP, y debe responder a requerimientos escuchando en el puerto 5000 de `localhost`.

La API deberá trabajar con una cuenta local, es decir, debe poder interactuar con un nodo que no tiene definida ninguna cuenta. Esta cuenta se obtendrá de la frase mnemónica definida en la variable de entorno `CFP_MNEMONIC`. Se asume que la cuenta que ha desplegado el contrato es la que tiene el índice 0 (`m/44'/60'/0'/0/0`). La forma de obtener esta cuenta se describe más adelante.

La ABI de los contratos puede obtenerse de los archivos JSON creados por Hardhat en el directorio `artifacts` del proyecto del TP anterior (por ejemplo, `artifacts/contracts/CFPFactory.sol/CFPFactory.json`, campo `abi`). El servidor puede almacenar la ABI en el código fuente, o en un archivo de configuración del proyecto.

La dirección del contrato `CFPFactory` desplegado debe ser leída de la variable de entorno `CFP_FACTORY_ADDRESS`.

Además de registrar y leer información en el contrato, el servidor guardará parte de la información en una base de datos local. A los efectos de simplificar el trabajo práctico, utilizaremos una base de datos `SQLite`, que trabaja con archivos locales y no requiere del uso de un servidor externo.

Cualquier otra información que requiera el servidor para ser ejecutado debe ser provista en línea de comandos, por variables de entorno o por un archivo de configuración. En ningún caso debe ser necesario modificar el código para que el servidor se ejecute. Cualquier requerimiento debe estar documentado en el `README.md`.

La API debe proveer los siguientes *endpoints*:

### `/create`

* Registra un llamado a presentación de propuestas en la API. El llamado queda almacenado localmente con estado `"pending"` hasta que el creador lo despliegue en la cadena invocando directamente `factory.create(callId, closingTime)` o `factory.createFor(callId, closingTime, creator)`.
* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `callId`: Hash que identifica al llamado. Debe ser exactamente `keccak256(rlp([title_utf8, description_utf8]))`, donde `title` y `description` son los demás campos del cuerpo **después de eliminar el whitespace al final**, y `rlp` es la codificación RLP estándar de la lista de dos elementos binarios.
  * `title`: Título del llamado. Se eliminan los espacios en blanco al final antes de validar. El título vacío no es válido. No puede superar 512 bytes codificado en UTF-8.
  * `description`: Descripción del llamado. Se eliminan los espacios en blanco al final antes de validar. La descripción vacía es válida. No puede superar 4096 bytes codificado en UTF-8.
   * `signature`: Firma EIP-712 de tipo `CreateRequest`. El dominio compartido se define más abajo. El mensaje contiene los campos:
     * `"operation"`: `"create"`
     * `"contract"`: dirección del contrato `CFPFactory` (address)
     * `"callId"`: el identificador del llamado (`bytes32`)
     La API recupera la dirección firmante a partir de la firma y verifica que esté autorizada en el contrato `CFPFactory`.
* Retorno exitoso:
  * Código HTTP: 201
  * Cuerpo: Un objeto JSON con un campo "message" con valor OK.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                                         | Código | Mensaje              |
    |-----------------------------------------------|--------|----------------------|
    | Content-Type incorrecto                       | 400    | INVALID_MIMETYPE     |
    | campo requerido ausente                       | 400    | MISSING_FIELD        |
    | título vacío (tras eliminar whitespace)       | 400    | INVALID_TITLE        |
    | título supera 512 bytes en UTF-8              | 400    | TITLE_TOO_LONG       |
    | descripción supera 4096 bytes en UTF-8        | 400    | DESCRIPTION_TOO_LONG |
    | callId mal formado                            | 400    | INVALID_CALLID       |
    | callId inconsistente con título y descripción | 400    | INVALID_CALLID       |
    | callId ya registrado en la API                | 403    | ALREADY_CREATED      |
    | emisor no autorizado                          | 403    | UNAUTHORIZED         |
    | firma inválida                                | 400    | INVALID_SIGNATURE    |
    | desconocida                                   | 500    | INTERNAL_ERROR       |

### `/register`

* Permite a un usuario registrarse en el sistema. El nombre del solicitante se almacena localmente asociado a su dirección. La respuesta incluye el estado de registro del solicitante al momento de la llamada. Los posibles estados son:
  * `pending`: el solicitante aún no se ha registrado en el contrato.
  * `registered`: el solicitante se ha registrado en el contrato pero todavía no ha sido autorizado por el administrador.
  * `authorized`: el solicitante ha sido autorizado por el administrador para crear llamados.
* Una cuenta desautorizada puede volver a registrarse llamando nuevamente a este endpoint. El registro anterior se reemplaza por uno nuevo.
* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `address`: Dirección del solicitante.
  * `name`: Nombre del solicitante. Se almacena localmente asociado a la dirección. Se eliminan los espacios en blanco al final antes de validar. El nombre vacío no es válido. No puede superar 512 bytes codificado en UTF-8.
   * `signature`: Firma EIP-712 de tipo `RegisterRequest`. El dominio compartido se define más abajo. El mensaje contiene los campos:
     * `"operation"`: `"register"`
     * `"contract"`: dirección del contrato `CFPFactory`
     * `"nonce"`: `0` (nonce inicial para registro)
     * `"name"`: nombre del solicitante

     La API recupera la dirección firmante y verifica que coincida con el campo `address`. Tras un registro exitoso el nonce de la dirección pasa a 1.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo `status` cuyo valor es `"pending"`, `"registered"` o `"authorized"`.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                            | Código | Mensaje              |
    |----------------------------------|--------|----------------------|
    | Content-Type incorrecto          | 400    | INVALID_MIMETYPE     |
    | campo requerido ausente          | 400    | MISSING_FIELD        |
    | nombre vacío                     | 400    | INVALID_NAME         |
    | nombre demasiado largo           | 400    | NAME_TOO_LONG        |
    | dirección inválida               | 400    | INVALID_ADDRESS      |
    | ya está registrado en el sistema | 403    | ALREADY_IN_SYSTEM    |
    | firma inválida                   | 400    | INVALID_SIGNATURE    |
    | desconocida                      | 500    | INTERNAL_ERROR       |

### `/registrations/:address` (GET)

* Retorna información sobre el estado de registro de una dirección. Si la dirección tiene un registro local (fue dada de alta mediante `POST /register`), devuelve también el nombre y el nonce. En caso contrario, consulta el contrato y devuelve únicamente el estado.
* Método: `GET`
* Argumento: `:address` corresponde a una dirección.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con el campo `status` (siempre presente) y, si la dirección tiene registro local, también `name` y `nonce`:
    * `status`: Estado de registro de la dirección. Puede ser `"pending"`, `"registered"`, `"authorized"` o `"archived"` (cuenta desautorizada que tiene llamados creados; debe volver a registrarse para operar).
    * `name`: Nombre asociado a la dirección (solo si tiene registro local).
    * `nonce`: Nonce actual de la dirección, como número entero (solo si tiene registro local). Vale 1 inmediatamente después del registro y se incrementa en 1 con cada actualización exitosa. El cliente debe leer este valor antes de firmar una actualización de nombre.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa              | Código | Mensaje          |
    |--------------------|--------|------------------|
    | dirección inválida | 400    | INVALID_ADDRESS  |
    | desconocida        | 500    | INTERNAL_ERROR   |

### `/registrations/:address` (PATCH)

* Actualiza el nombre asociado a una dirección registrada. Requiere que el solicitante pruebe su identidad mediante una firma.
* Método: `PATCH`
* Content-type: `application/json`
* Argumento: `:address` corresponde a la dirección cuyo nombre se desea actualizar.
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `name`: Nuevo nombre del solicitante. Se eliminan los espacios en blanco al final antes de validar. El nombre vacío no es válido. No puede superar 512 bytes codificado en UTF-8.
   * `signature`: Firma EIP-712 de tipo `RegisterRequest`. El dominio compartido se define más abajo. El mensaje contiene los campos:
     * `"operation"`: `"update"`
     * `"contract"`: dirección del contrato `CFPFactory`
     * `"nonce"`: nonce actual de la dirección (obtenido mediante `GET /registrations/:address`)
     * `"name"`: nuevo nombre

     La API verifica que la dirección recuperada de la firma coincida con `:address`, y que el nonce de la firma coincida con el nonce almacenado. Tras una actualización exitosa el nonce se incrementa, invalidando la firma utilizada.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo "message" con valor OK.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código | Mensaje              |
    |--------------------------|--------|----------------------|
    | Content-Type incorrecto  | 400    | INVALID_MIMETYPE     |
    | campo requerido ausente  | 400    | MISSING_FIELD        |
    | nombre vacío             | 400    | INVALID_NAME         |
    | nombre demasiado largo   | 400    | NAME_TOO_LONG        |
    | dirección inválida       | 400    | INVALID_ADDRESS      |
    | firma inválida           | 400    | INVALID_SIGNATURE    |
    | dirección no registrada  | 404    | NOT_REGISTERED       |
    | overflow de nonce        | 400    | NONCE_OVERFLOW       |
    | desconocida              | 500    | INTERNAL_ERROR       |

### `/register-proposal`

* Permite a un usuario registrar una propuesta en un determinado llamado. Este registro es anónimo, es decir, la dirección que quedará registrada en el contrato es la utilizada por el servidor de la API.
* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `callId`: Hash que identifica al llamado.
  * `title`: Título de la propuesta. Se eliminan los espacios en blanco al final antes de validar. El título vacío no es válido. No puede superar 512 bytes codificado en UTF-8.
  * `description`: Descripción de la propuesta. Se eliminan los espacios en blanco al final antes de validar. La descripción vacía es válida. No puede superar 4096 bytes codificado en UTF-8.
  * `files`: Lista de hashes keccak256 (formato `0x…`) de los archivos adjuntos. La lista puede tener como máximo 125 elementos, de modo que el árbol de Merkle no supere 128 hojas en total. No se permiten hashes duplicados dentro de la lista.
* El servidor calcula el identificador de propuesta como la raíz del árbol de Merkle construido con las siguientes hojas, **ordenadas lexicográficamente**:
  * `callId` (ya es un hash de 32 bytes; se usa directamente como hoja)
  * `keccak256(title)` (título codificado en UTF-8)
  * `keccak256(description)` (descripción codificada en UTF-8)
  * Cada elemento de `files` (ya es un hash keccak256)

  Incluir el `callId` como hoja liga el `proposalId` a un llamado específico, evitando que propuestas con igual contenido presentadas en distintas convocatorias compartan identificador (lo cual revelaría sus contenidos al abrirse la primera).

  La construcción del árbol es compatible con la biblioteca OpenZeppelin: los nodos internos se calculan como `keccak256(min(a,b) ++ max(a,b))`.
* Retorno exitoso:
  * Código HTTP: 201
  * Cuerpo: Un objeto JSON con los siguientes campos:
    * `message`: valor OK.
    * `proposalId`: hash raíz del árbol de Merkle, que identifica en forma unívoca a la propuesta (`0x…`).
    * `proof`: objeto cuyas claves son los hashes de las hojas y cuyos valores son las pruebas de Merkle (listas de hashes `0x…`). Las claves presentes son:
      * `callId` en minúsculas
      * `keccak256(title)` (UTF-8), en formato `0x…` en minúsculas
      * `keccak256(description)` (UTF-8), en formato `0x…` en minúsculas
      * Cada elemento de `files` en minúsculas

      Cada prueba contiene únicamente los hashes hermanos en el camino hacia la raíz, sin incluir la hoja misma. Para verificar que una hoja `L` pertenece al árbol con raíz `proposalId` se puede usar `MerkleProof.verify(proof[L], proposalId, L)`.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                                  | Código | Mensaje              |
    |----------------------------------------|--------|----------------------|
    | Content-Type incorrecto                | 400    | INVALID_MIMETYPE     |
    | campo requerido ausente                | 400    | MISSING_FIELD        |
    | título vacío (tras eliminar whitespace)| 400    | INVALID_TITLE        |
    | título supera 512 bytes en UTF-8       | 400    | TITLE_TOO_LONG       |
    | descripción supera 4096 bytes en UTF-8 | 400    | DESCRIPTION_TOO_LONG |
    | callId mal formado                     | 400    | INVALID_CALLID       |
    | callId inexistente                     | 404    | CALLID_NOT_FOUND     |
    | hash de archivo mal formado            | 400    | INVALID_PROPOSAL     |
    | hashes de archivos duplicados          | 400    | INVALID_PROPOSAL     |
    | más de 125 archivos                    | 400    | TOO_MANY_FILES       |
    | propuesta ya existente                 | 403    | ALREADY_REGISTERED   |
    | desconocida                            | 500    | INTERNAL_ERROR       |

### `/admin/nonce`

* Retorna el nonce actual del administrador, necesario para firmar las operaciones `/authorize` y `/unauthorize`.
* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo entero:
    * `nonce`: valor actual del nonce del administrador. Vale 1 al inicio y se incrementa en 1 tras cada operación de autorización o desautorización exitosa.

### `/admin/address`

* Devuelve la dirección del administrador de la API. La interfaz web lo usa para determinar si la cuenta conectada corresponde al administrador.
* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo `address` que contiene la dirección del administrador.

### `/creators`

* Lista todos los creadores registrados en la API (excluye archivados).
* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo `creators` que contiene una lista de objetos con `address`, `name`, `status` y `nonce`.

### `/admin/pending`

* Lista las solicitudes de registro pendientes de autorización (estado `registered` en la DB).
* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo `pending` que contiene una lista de objetos con `address`, `name`, `status` y `nonce`.

### `/authorize/:address`

* Permite al administrador autorizar a una dirección para crear llamados.
* Método: `POST`
* Content-type: `application/json`
* Argumento: `:address` corresponde a la dirección a autorizar.
* Cuerpo: Un objeto JSON con el siguiente campo:
   * `signature`: Firma EIP-712 de tipo `AdminActionRequest`. El dominio compartido se define más abajo. El mensaje contiene los campos:
     * `"operation"`: `"authorize"`
     * `"contract"`: dirección del contrato `CFPFactory`
     * `"nonce"`: nonce actual del administrador (obtenido mediante `GET /admin/nonce`)
     * `"target"`: dirección a autorizar

     La API verifica que la dirección recuperada de la firma coincida con `CFP_ADMIN_ADDRESS`. Tras una operación exitosa el nonce se incrementa, invalidando la firma utilizada.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo "message" con valor OK.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                           | Código | Mensaje          |
    |---------------------------------|--------|------------------|
    | Content-Type incorrecto         | 400    | INVALID_MIMETYPE |
    | campo requerido ausente         | 400    | MISSING_FIELD    |
    | dirección inválida              | 400    | INVALID_ADDRESS  |
    | firma inválida                  | 400    | INVALID_SIGNATURE|
    | overflow de nonce               | 400    | NONCE_OVERFLOW   |
    | dirección no registrada en API  | 404    | NOT_REGISTERED   |
    | desconocida                     | 500    | INTERNAL_ERROR   |

### `/unauthorize/:address`

* Permite al administrador revocar la autorización de una dirección.
* Método: `POST`
* Content-type: `application/json`
* Argumento: `:address` corresponde a la dirección a desautorizar.
* Cuerpo: Un objeto JSON con el siguiente campo:
   * `signature`: Firma EIP-712 de tipo `AdminActionRequest`. Idéntica a `/authorize/:address` pero con `"operation": "unauthorize"`.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo "message" con valor OK.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                                           | Código | Mensaje           |
    |-------------------------------------------------|--------|-------------------|
    | Content-Type incorrecto                         | 400    | INVALID_MIMETYPE  |
    | campo requerido ausente                         | 400    | MISSING_FIELD     |
    | dirección inválida                              | 400    | INVALID_ADDRESS   |
    | firma inválida                                  | 400    | INVALID_SIGNATURE |
    | overflow de nonce                               | 400    | NONCE_OVERFLOW    |
    | dirección no registrada en la API o archivada   | 404    | NOT_REGISTERED    |
    | desconocida                                     | 500    | INTERNAL_ERROR    |

### `/authorized/:address`

* Método: `GET`
* Argumento: `:address` corresponde a una dirección
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo booleano
    * "authorized", el estado de autorización de la dirección provista.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código |  Mensaje             |
    |--------------------------|--------|----------------------|
    |dirección inválida        | 400    | INVALID_ADDRESS      |
    |desconocida               | 500    | INTERNAL_ERROR       |

### `/calls/:call_id`

* Retorna la información de un llamado registrado en la API mediante `POST /create`. Los llamados creados directamente en el contrato sin pasar por la API no son accesibles por este endpoint (ver `/closing-time` y `/proposal-data` para acceso directo al contrato).
* Método: `GET`
* Argumento: `:call_id` es el hash que identifica a un llamado.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON cuyo contenido varía según el estado del llamado:
    * Si el llamado está pendiente de despliegue en la cadena (`"status": "pending"`):
      * `"title"`: Título del llamado, de tipo `string`.
      * `"description"`: Descripción del llamado, de tipo `string`.
      * `"status"`: `"pending"`.
    * Si el llamado ya fue desplegado en la cadena (`"status": "created"`):
      * `"creator"`: Dirección del creador, de tipo `string`.
      * `"cfp"`: Dirección del contrato CFP que representa al llamado, de tipo `string`.
      * `"title"`: Título del llamado, de tipo `string`.
      * `"description"`: Descripción del llamado, de tipo `string`.
      * `"status"`: `"created"`.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa              | Código |  Mensaje             |
    |--------------------|--------|----------------------|
    | callId mal formado | 400    | INVALID_CALLID       |
    | callId inexistente | 404    | CALLID_NOT_FOUND     |
    | desconocida        | 500    | INTERNAL_ERROR       |

### `/closing-time/:call_id`

* Método: `GET`
* Argumento: `:call_id` es el hash que identifica a un llamado
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo de tipo `string`:
    * "closingTime", la fecha y hora de cierre del llamado, en formato ISO 8601.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código |  Mensaje             |
    |--------------------------|--------|----------------------|
    |callId mal formado        | 400    | INVALID_CALLID       |
    |callId inexistente        | 404    | CALLID_NOT_FOUND     |
    |desconocida               | 500    | INTERNAL_ERROR       |

### `/verify-proof`

* Verifica que una hoja pertenezca a un árbol de Merkle cuya raíz es el `proposalId` indicado. El algoritmo es compatible con `MerkleProof.verify` de OpenZeppelin: cada nodo interno se calcula como `keccak256(min(a, b) ++ max(a, b))`.
* Método: `POST`
* Content-type: `application/json`
* Cuerpo: Un objeto JSON con los siguientes campos:
  * `proposalId`: raíz del árbol de Merkle (`0x…`), tal como la devuelve `POST /register-proposal`.
  * `leaf`: hash de la hoja a verificar (`0x…`).
  * `proof`: lista de hashes hermanos en el camino desde la hoja hasta la raíz (`0x…` cada uno), tal como la devuelve `POST /register-proposal` o `GET /proposal-data`. La lista puede tener como máximo 7 elementos (log₂ 128).
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo booleano:
    * `valid`: `true` si la prueba es válida, `false` en caso contrario.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

  | Causa                                            | Código | Mensaje          |
  |--------------------------------------------------|--------|------------------|
  | Content-Type incorrecto                          | 400    | INVALID_MIMETYPE |
  | campo requerido ausente                          | 400    | MISSING_FIELD    |
  | proposalId, leaf o elemento de proof mal formado | 400    | INVALID_PROPOSAL |
  | proof supera 7 elementos                         | 400    | PROOF_TOO_LONG   |

### `/contract-address`

* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo de tipo `string`:
    * "address", dirección del contrato factoría.

### `/contract-owner`

* Método: `GET`
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo de tipo `string`:
    * "address", dirección del dueño del contrato factoría.

### `/proposal-data/:call_id/:proposal`

* Método: `GET`
* Argumentos:
  * `:call_id` es el hash que identifica a un llamado.
  * `:proposal` es el hash que identifica una propuesta (raíz del árbol de Merkle, devuelta por `POST /register-proposal`).
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con los siguientes campos:
    * `sender`: dirección que registró la propuesta (la cuenta del servidor de la API).
    * `blockNumber`: número de bloque en el cual se registró.
    * `timestamp`: fecha y hora de registro en formato ISO 8601.
    * `estado`: estado del llamado al momento de la consulta: `"open"` si la convocatoria sigue abierta, `"closed"` si ya cerró.
    * `title`: título de la propuesta (sólo si fue registrada vía `POST /register-proposal`).
    * `description`: descripción de la propuesta (ídem).
    * `proof`: pruebas de Merkle para las hojas de datos identificatorios, con el mismo formato que devuelve `POST /register-proposal` pero incluyendo únicamente las claves:
      * `callId` en minúsculas
      * `keccak256(title)` en formato `0x…` en minúsculas
      * `keccak256(description)` en formato `0x…` en minúsculas

      Este campo sólo está presente si la propuesta fue registrada vía `POST /register-proposal`.
* Retorno fallido:
  * Código HTTP: Según la tabla siguiente.
  * Cuerpo: Un objeto JSON con un campo "message" con valor indicado en la tabla siguiente.

    | Causa                    | Código |  Mensaje             |
    |--------------------------|--------|----------------------|
    |callId mal formado        | 400    | INVALID_CALLID       |
    |callId inexistente        | 404    | CALLID_NOT_FOUND     |
    |propuesta mal formada     | 400    | INVALID_PROPOSAL     |
    |propuesta inexistente     | 404    | PROPOSAL_NOT_FOUND   |
    |desconocida               | 500    | INTERNAL_ERROR       |

## Firma EIP-712

En el Práctico 10 se migró de EIP-191 (mensajes planos con prefijo `\x19Ethereum Signed Message`) a EIP-712 (mensajes tipados estructurados). El cambio afecta a todos los endpoints que reciben una firma: `POST /create`, `POST /register`, `PATCH /registrations/:address`, `POST /authorize/:address` y `POST /unauthorize/:address`.

### Dominio compartido

Todas las firmas EIP-712 comparten el mismo dominio:

```json
{
  "name": "CFP API",
  "version": "1",
  "chainId": <id de la cadena>,
  "verifyingContract": "<dirección del contrato CFPFactory>"
}
```

### Tipos de mensaje

**`CreateRequest`** — usado en `POST /create`:

| Campo | Tipo | Valor |
|-------|------|-------|
| `operation` | `string` | `"create"` |
| `contract` | `address` | Dirección del contrato `CFPFactory` |
| `callId` | `bytes32` | Hash que identifica al llamado |

**`RegisterRequest`** — usado en `POST /register` y `PATCH /registrations/:address`:

| Campo | Tipo | Registro | Actualización |
|-------|------|----------|---------------|
| `operation` | `string` | `"register"` | `"update"` |
| `contract` | `address` | Dirección del `CFPFactory` | Dirección del `CFPFactory` |
| `nonce` | `uint256` | `0` | Nonce actual (de `GET /registrations/:address`) |
| `name` | `string` | Nombre del solicitante | Nuevo nombre |

**`AdminActionRequest`** — usado en `POST /authorize/:address` y `POST /unauthorize/:address`:

| Campo | Tipo | Autorizar | Desautorizar |
|-------|------|-----------|--------------|
| `operation` | `string` | `"authorize"` | `"unauthorize"` |
| `contract` | `address` | Dirección del `CFPFactory` | Dirección del `CFPFactory` |
| `nonce` | `uint256` | Nonce actual del admin (de `GET /admin/nonce`) | Nonce actual del admin |
| `target` | `address` | Dirección a autorizar | Dirección a desautorizar |

### Implementación en el servidor

La API utiliza `encode_typed_data` de `eth_account` para construir los mensajes EIP-712 y `Account.recover_message` para recuperar la dirección firmante. Las definiciones de tipos están centralizadas en la variable `TYPE_DEFINITIONS` y el helper `make_eip712_message()` construye el mensaje completo a partir del tipo primario y los datos.

## Diferencias con el Práctico 8

### Endpoints modificados

#### `/create`

En el Práctico 8, este endpoint creaba el llamado directamente en el contrato. En el Práctico 9, almacena el llamado localmente con estado `"pending"` y deja la creación on-chain a cargo del creador.

El cuerpo cambia por completo: se eliminan `closingTime` y el `callId` libre, y se incorporan `title` y `description`. El `callId` ya no es arbitrario: debe ser exactamente `keccak256(rlp([title_utf8, description_utf8]))`, y la API lo verifica. La firma ahora solo cubre los 32 bytes del `callId` (en lugar de dirección+callId+closingTime).

Se establecen límites de longitud: `title` no puede superar 512 bytes en UTF-8 y `description` no puede superar 4096 bytes en UTF-8.

Se eliminan los errores `INVALID_TIME_FORMAT` e `INVALID_CLOSING_TIME`, que ya no tienen sentido.

#### `/register`

En el Práctico 8, el registro autorizaba al solicitante de inmediato. En el Práctico 9, el registro queda en estado `"pending"` hasta que el administrador lo autorice. El cuerpo incorpora el campo obligatorio `name`, el mensaje a firmar cambia (ahora cubre el prefijo `registerPOST`, la dirección del contrato, el nonce y el nombre), y la respuesta ya no es `{ message: "OK" }` sino `{ status: "pending" | "registered" | "authorized" }`. Se suman los errores `INVALID_NAME` y `NAME_TOO_LONG`.

#### `/register-proposal`

En el Práctico 8, el cliente calculaba y proveía el hash de la propuesta en el campo `proposal`. En el Práctico 9, el cliente envía `title`, `description` y `files`, y el servidor construye el identificador de propuesta como raíz del árbol de Merkle compatible con OpenZeppelin. La respuesta incluye el `proposalId` calculado y las pruebas de Merkle (`proof`) para cada hoja.

Se establecen límites de longitud: `title` no puede superar 512 bytes en UTF-8, `description` no puede superar 4096 bytes en UTF-8, y `files` no puede tener más de 125 elementos, de modo que el árbol de Merkle no supere 128 hojas en total.

#### `/calls/:call_id`

En el Práctico 8, este endpoint solo devolvía `creator` y `cfp` para llamados ya creados en el contrato. En el Práctico 9 gestiona dos estados: los llamados `"pending"` devuelven `title`, `description` y `status`; los `"created"` devuelven además `creator` y `cfp`.

#### `/proposal-data/:call_id/:proposal`

El campo `:proposal` ahora es la raíz del árbol de Merkle devuelta por `POST /register-proposal`. La respuesta se enriquece con el campo `estado` (`"open"` o `"closed"`) y, si la propuesta fue registrada a través de la API, también con `title`, `description` y `proof`.

### Endpoints nuevos

* **`GET /registrations/:address`**: Consulta el estado de registro de una dirección, con nombre y nonce si tiene registro local.
* **`PATCH /registrations/:address`**: Actualiza el nombre asociado a una dirección registrada. Requiere firma con nonce.
* **`GET /admin/nonce`**: Retorna el nonce actual del administrador, necesario para firmar las operaciones de autorización.
* **`POST /authorize/:address`**: Permite al administrador autorizar una dirección para crear llamados, mediante firma con nonce de administrador.
* **`POST /unauthorize/:address`**: Permite al administrador revocar la autorización de una dirección.
* **`POST /verify-proof`**: Verifica si un hash pertenece a un árbol de Merkle dado su `proposalId` (raíz) y la prueba de Merkle. La prueba no puede tener más de 7 elementos (log₂ 128).

### Endpoints Etapa 3

#### `POST /deliver`

* Registra la entrega post-cierre de los archivos comprometidos en una propuesta. El servidor verifica la integridad de los archivos contra el recibo original, calcula la raíz de Merkle de los archivos, envía una transacción on-chain a `CFP.registerDelivery()` y almacena los archivos en disco.
* Método: `POST`
* Content-type: `multipart/form-data`
* Cuerpo:
  * `receipt`: String JSON con el recibo original devuelto por `POST /register-proposal`. Debe contener `proposalId` y `proof`.
  * `files`: Uno o más archivos físicos. Cada archivo se verifica contra su hash keccak256 contenido en el recibo.
* Retorno exitoso:
  * Código HTTP: 201
  * Cuerpo: Un objeto JSON con los campos:
    * `message`: valor OK.
    * `filesRoot`: raíz del árbol de Merkle de los archivos entregados (`0x…`).
    * `proposalId`: identificador de la propuesta entregada.
    * `txHash`: hash de la transacción on-chain de `registerDelivery()` (`0x…`).
    * `blockNumber`: número de bloque en el que se minó la transacción.
* Retorno fallido:

  | Causa                              | Código | Mensaje              |
  |-----------------------------------|--------|----------------------|
  | Content-Type incorrecto           | 400    | INVALID_MIMETYPE     |
  | campo requerido ausente           | 400    | MISSING_FIELD        |
  | recibo mal formado o proposalId inválido | 400 | INVALID_PROPOSAL |
  | propuesta no encontrada en BD     | 404    | PROPOSAL_NOT_FOUND   |
  | llamado no encontrado             | 404    | CALLID_NOT_FOUND     |
  | convocatoria no cerrada           | 403    | CALL_NOT_CLOSED      |
  | entrega ya registrada             | 403    | ALREADY_DELIVERED    |
  | hash de archivo no coincide con recibo | 400 | INVALID_PROPOSAL   |
  | desconocida                       | 500    | INTERNAL_ERROR       |

#### `GET /deliveries/<proposal_id>`

* Devuelve la información de la entrega post-cierre de una propuesta.
* Método: `GET`
* Argumento: `:proposal_id` es el hash que identifica a la propuesta.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con los campos:
    * `sender`: dirección que registró la entrega (cuenta del servidor).
    * `filesRoot`: raíz del árbol de Merkle de los archivos entregados.
    * `deliveredAt`: fecha y hora de la entrega en formato ISO 8601.
    * `callId`: hash del llamado asociado a la propuesta entregada.
    * `files`: lista de objetos con `hash` y `name` para cada archivo.
* Retorno fallido:

  | Causa                     | Código | Mensaje             |
  |---------------------------|--------|---------------------|
  | proposalId mal formado   | 400    | INVALID_PROPOSAL    |
  | entrega no registrada     | 404    | NOT_DELIVERED       |
  | desconocida               | 500    | INTERNAL_ERROR      |

#### `GET /calls/<call_id>/deliveries`

* Devuelve la lista de entregas post-cierre para un llamado. Cada entrega contiene los datos de la propuesta entregada y la lista de archivos disponibles para descarga pública.
* Método: `GET`
* Argumento: `:call_id` es el hash que identifica al llamado.
* Retorno exitoso:
  * Código HTTP: 200
  * Cuerpo: Un objeto JSON con un campo `deliveries` que contiene una lista de objetos con:
    * `proposalId`: identificador de la propuesta entregada.
    * `filesRoot`: raíz del árbol de Merkle de los archivos entregados.
    * `deliveredAt`: fecha y hora de la entrega en formato ISO 8601.
    * `files`: lista de objetos con `hash` y `name` para cada archivo.
* Retorno fallido:

  | Causa              | Código | Mensaje             |
  |--------------------|--------|---------------------|
  | callId mal formado | 400    | INVALID_CALLID      |
  | desconocida        | 500    | INTERNAL_ERROR      |

#### `GET /deliveries/<proposal_id>/files/<file_hash>`

* Permite descargar un archivo entregado, identificado por su hash keccak256.
* Método: `GET`
* Argumentos:
  * `:proposal_id` hash de la propuesta.
  * `:file_hash` hash keccak256 del archivo a descargar.
* Retorno exitoso:
  * Código HTTP: 200
  * Contenido: el archivo binario.
  * Header `Content-Disposition`: incluye el nombre original del archivo.
* Retorno fallido:

  | Causa                            | Código | Mensaje        |
  |----------------------------------|--------|----------------|
  | proposalId o fileHash inválido   | 400    | INVALID_PROPOSAL |
  | archivo no encontrado            | 404    | NOT_FOUND      |
  | desconocida                      | 500    | INTERNAL_ERROR |

### Configuración

Se agrega la variable de entorno `CFP_ADMIN_ADDRESS`, que contiene la dirección autorizada a firmar las operaciones `/authorize` y `/unauthorize`.

### Mensajes

Se eliminan `INVALID_TIME_FORMAT` e `INVALID_CLOSING_TIME`. Se incorporan `INVALID_NAME`, `NAME_TOO_LONG`, `TITLE_TOO_LONG`, `DESCRIPTION_TOO_LONG`, `TOO_MANY_FILES`, `PROOF_TOO_LONG`, `NOT_REGISTERED` y `NONCE_OVERFLOW`.

### Diferencias con el Práctico 9

#### Migración a EIP-712

Todos los endpoints que procesan firmas (create, register, registrations PATCH, authorize, unauthorize) migraron de EIP-191 a EIP-712. El cambio principal es que el mensaje a firmar ya no es una concatenación plana de bytes con prefijo `\x19Ethereum Signed Message`, sino un mensaje tipado estructurado con dominio y tipos definidos. Esto permite que MetaMask muestre al usuario los campos del mensaje de forma legible antes de firmar.

#### Nuevos endpoints

* **`GET /admin/address`**: Devuelve la dirección del administrador. La interfaz web lo usa para determinar si la cuenta conectada es la administradora.
* **`GET /creators`**: Lista todos los creadores registrados (excluye archivados). Usado por la vista pública del frontend.
* **`GET /admin/pending`**: Lista las solicitudes pendientes de autorización. Usado por el panel de administración.

#### Endpoints modificados

* **`POST /register`**: Incorpora validación `ADMIN_CANNOT_REGISTER`: si la dirección firmante coincide con `CFP_ADMIN_ADDRESS`, se rechaza con 403. La cuenta administradora no puede registrarse como creador.
* **`PATCH /registrations/:address`**: Idéntica validación: si `:address` es la cuenta admin, se rechaza con 403.
* **`POST /authorize/:address`**: Ahora requiere que la dirección a autorizar no esté archivada (`status != "archived"`). Si lo está, devuelve `NOT_REGISTERED` (404).

#### Configuración

Se agregó la variable de entorno `CFP_CONTRACTS_DIR` (por defecto `../contracts`) que permite especificar la ruta al directorio de contratos compilados. La ruta de la base de datos se configura con `CFP_DB_PATH` (por defecto `cfp.db`).

El script de despliegue (`scripts/deploy.js` en `contracts`) ahora deriva la cuenta administradora como Account 2 (`m/44'/60'/0'/0/2`) y la imprime como `CFP_ADMIN_ADDRESS`. Las tres variables (`CFP_MNEMONIC`, `CFP_FACTORY_ADDRESS`, `CFP_ADMIN_ADDRESS`) se imprimen listas para exportar.

#### Nuevos mensajes

Se incorpora `ADMIN_CANNOT_REGISTER`: "La cuenta administradora no puede registrarse como creador".

## Base de datos

El servidor mantiene una base de datos local para almacenar información complementaria que no está disponible en el contrato. La base de datos se crea automáticamente si no existe y contiene al menos los siguientes datos por dirección registrada: nombre, nonce actual y estado de registro.

### Tabla `calls`

Almacena los metadatos de los llamados registrados vía `POST /create`.

| Campo       | Tipo    | Descripción                                    |
|-------------|---------|------------------------------------------------|
| `call_id`   | TEXT PK | Hash que identifica al llamado                 |
| `title`     | TEXT    | Título del llamado                             |
| `description` | TEXT  | Descripción del llamado                        |
| `creator`   | TEXT    | Dirección del creador                          |
| `status`    | TEXT    | `"pending"` o `"created"`                      |

### Tabla `proposals`

Almacena los metadatos de las propuestas registradas vía `POST /register-proposal`.

| Campo         | Tipo    | Descripción                                      |
|---------------|---------|--------------------------------------------------|
| `proposal_id` | TEXT PK | Hash raíz del árbol de Merkle de la propuesta    |
| `call_id`     | TEXT FK | Hash del llamado asociado                        |
| `title`       | TEXT    | Título de la propuesta                           |
| `description` | TEXT    | Descripción de la propuesta                      |
| `sender`      | TEXT    | Dirección que registró la propuesta              |

### Tabla `deliveries`

Almacena los registros de entrega post-cierre vía `POST /deliver`.

| Campo         | Tipo    | Descripción                                      |
|---------------|---------|--------------------------------------------------|
| `proposal_id` | TEXT PK | Hash de la propuesta entregada                   |
| `call_id`     | TEXT    | Hash del llamado asociado                        |
| `sender`      | TEXT    | Dirección que registró la entrega                |
| `files_root`  | TEXT    | Raíz del árbol de Merkle de los archivos         |
| `delivered_at`| DATETIME | Fecha y hora de la entrega                      |

### Tabla `proposal_uploads`

Almacena los archivos subidos durante el registro de propuestas (`POST /register-proposal`). La API retiene estos archivos temporalmente para calcular sus hashes; no se descargan públicamente hasta la entrega post-cierre.

| Campo         | Tipo    | Descripción                                      |
|---------------|---------|--------------------------------------------------|
| `id`          | INTEGER PK | Identificador autoincremental                  |
| `proposal_id` | TEXT FK | Hash de la propuesta                            |
| `file_hash`   | TEXT    | Hash keccak256 del archivo                      |
| `file_name`   | TEXT    | Nombre original del archivo                     |

### Tabla `proposal_files`

Almacena los archivos físicos entregados en una entrega post-cierre.

| Campo         | Tipo    | Descripción                                      |
|---------------|---------|--------------------------------------------------|
| `id`          | INTEGER PK | Identificador autoincremental                  |
| `proposal_id` | TEXT FK | Hash de la propuesta                            |
| `file_hash`   | TEXT    | Hash keccak256 del archivo                      |
| `file_name`   | TEXT    | Nombre original del archivo                     |
| `file_path`   | TEXT    | Ruta en disco del archivo almacenado            |

### Estados de registro

Los posibles estados en la base de datos son:

* `pending` — La dirección llamó a `POST /register` pero aún no invocó `register()` en el contrato.
* `registered` — La dirección invocó `register()` en el contrato y está pendiente de autorización.
* `authorized` — La dirección fue autorizada por el administrador para crear llamados.
* `archived` — La dirección fue desautorizada y tiene llamados creados. Sus datos se preservan para consulta. Para volver a operar debe registrarse nuevamente.

Cuando el administrador desautoriza una cuenta mediante `POST /unauthorize/:address`:

* Si la cuenta tiene llamados creados (`createdByCount() > 0`), su registro pasa al estado `archived`.
* Si la cuenta no tiene llamados, su registro se elimina de la base de datos.

La ruta del archivo de base de datos debe poder configurarse en línea de comandos, por variable de entorno o por archivo de configuración. Los casos de prueba leen esa ruta desde la variable de entorno `CFP_DB_PATH` (valor por defecto: `cfp.db`).

## Event listener

El servidor mantiene la base de datos sincronizada con el contrato escuchando los eventos `CreatorRegistered`, `CreatorAuthorized`, `CreatorUnauthorized` y `CFPCreated`. Existen dos estrategias para implementar esto.

### Estrategia push: filtros de suscripción (`eth_newFilter` + `eth_getFilterChanges`)

El nodo expone `eth_newFilter` para crear un filtro persistente y `eth_getFilterChanges` para obtener los eventos nuevos desde la última consulta. En **web3.py** se accede a través de `create_filter` / `get_new_entries`; en **ethers v6**, `contract.on("EventName", handler)` usa esta misma infraestructura internamente.

```python
# web3.py — estrategia push
event_filter = contract.events.CreatorRegistered.create_filter(fromBlock="latest")

while True:
    for evt in event_filter.get_new_entries():   # eth_getFilterChanges
        handle(evt)
    time.sleep(1)
```

```javascript
// ethers v6 — estrategia push
factory.on("CreatorRegistered", (creator, event) => handle(creator, event));
```

**Limitación con Hardhat:** Hardhat no implementa completamente `eth_getFilterChanges`: en lugar de devolver una lista vacía cuando no hay eventos nuevos, devuelve `null`. Esto provoca que `get_new_entries()` lance una excepción y que el handler de ethers v6 falle con `TypeError: results is not iterable`. Esta estrategia **no funciona** con un nodo Hardhat.

### Estrategia poll: consulta de logs (`eth_getLogs`)

En lugar de mantener un filtro en el nodo, el servidor recuerda el último bloque procesado y consulta periódicamente los logs desde ese bloque hasta el bloque actual. En **web3.py** se usa `get_logs` (o el equivalente `contract.events.EventName.get_logs`); en **ethers v6**, `contract.queryFilter`.

```python
# web3.py — estrategia poll
last_block = web3.eth.block_number
while True:
    time.sleep(1)
    current_block = web3.eth.block_number
    if current_block > last_block:
        for evt in contract.events.CreatorRegistered.get_logs(  # eth_getLogs
                fromBlock=last_block + 1, toBlock=current_block):
            handle(evt)
        last_block = current_block
```

```javascript
// ethers v6 — estrategia poll
let lastBlock = await provider.getBlockNumber();
while (true) {
  await new Promise(r => setTimeout(r, 1000));
  const currentBlock = await provider.getBlockNumber();
  if (currentBlock > lastBlock) {
    for (const evt of await factory.queryFilter("CreatorRegistered",  // eth_getLogs
                                                 lastBlock + 1, currentBlock))
      handle(evt);
    lastBlock = currentBlock;
  }
}
```

Esta estrategia funciona con cualquier nodo, incluyendo Hardhat, y es la recomendada para este trabajo práctico.

## Cuentas y roles

El servidor trabaja con dos roles de cuenta bien diferenciados.

### Owner del contrato

El servidor deriva la cuenta en el índice 0 del mnemónico (`m/44'/60'/0'/0/0`) a partir de `CFP_MNEMONIC`. Esta cuenta debe ser la misma que desplegó el contrato `CFPFactory`, ya que es la que figura como `owner` en el contrato. Al iniciar, el servidor verifica que la cuenta derivada coincida con `factory.owner()`; si no coincide, el servidor se detiene con un error.

El servidor usa esta cuenta para firmar todas las transacciones que envía al contrato: `authorize()`, `unauthorize()`, `createFor()` y `registerProposal()`.

### Administrador de la API

`CFP_ADMIN_ADDRESS` contiene la dirección de la cuenta que actúa como administrador de la API. Esta cuenta **no** es el owner del contrato en la cadena — simplemente es quien tiene la potestad de solicitar al servidor que ejecute operaciones de autorización.

Cuando un cliente llama a `POST /authorize/:address` o `POST /unauthorize/:address`, debe incluir una firma generada con la clave privada del administrador. El servidor verifica que esa firma provenga de `CFP_ADMIN_ADDRESS` y, si es válida, usa su propia cuenta (el owner, índice 0) para enviar la transacción correspondiente al contrato.

El servidor solo necesita conocer la **dirección** del administrador, no su clave privada. La clave privada la posee quien opere como administrador y la usa para firmar las solicitudes HTTP.

### Uso en los tests

Los tests asumen que las tres cuentas se derivan del mismo mnemónico:

| Índice | Path HD                    | Rol                                      |
|--------|----------------------------|------------------------------------------|
| 0      | `m/44'/60'/0'/0/0`         | Owner del contrato; firma transacciones  |
| 1      | `m/44'/60'/0'/0/1`         | Funder: transfiere ETH a cuentas de test |
| 2      | `m/44'/60'/0'/0/2`         | Administrador: firma solicitudes HTTP    |

Los tests obtienen el administrador derivando la cuenta en el índice 2 del mnemónico. La dirección de esa cuenta debe coincidir con el valor de `CFP_ADMIN_ADDRESS` al ejecutar los tests.

## Ejecución de los casos de prueba

Los tests están en `test_apiserver.py` y se ejecutan con `pytest`. Antes de lanzarlos deben cumplirse los siguientes requisitos.

### 1. Dependencias Python

```bash
pip install -r requirements.txt
```

### 2. Variables de entorno

| Variable              | Requerida | Descripción                                                               |
|-----------------------|-----------|---------------------------------------------------------------------------|
| `CFP_MNEMONIC`        | Sí        | Mnemónico BIP39 del que se derivan las cuentas del sistema                |
| `CFP_FACTORY_ADDRESS` | Sí        | Dirección del contrato `CFPFactory` desplegado en el nodo local           |
| `CFP_ADMIN_ADDRESS`   | Sí        | Dirección de la cuenta administradora; debe ser el índice 2 del mnemónico |
| `CFP_WEB3_URI`        | No        | URL del nodo Ethereum RPC; por defecto `http://localhost:8545`            |

`CFP_ADMIN_ADDRESS` debe coincidir exactamente con la dirección derivada en el índice 2 del mnemónico (`m/44'/60'/0'/0/2`), ya que los tests generan la firma del administrador a partir de esa cuenta. Las mismas variables deben estar definidas también para el servidor.

### 3. Nodo Ethereum local

Los tests se conectan al nodo indicado por `CFP_WEB3_URI` (por defecto `http://localhost:8545`). La forma recomendada es Hardhat Node, lanzado desde el directorio `contracts`:

```bash
cd ../contracts
npx hardhat node
```

Hardhat Node pre-carga con ETH todas las cuentas derivadas del mnemónico estándar, incluyendo el owner (índice 0), el funder (índice 1) y el administrador (índice 2). El funder es necesario porque los tests crean cuentas efímeras y las fondean con ETH para pagar el gas de las transacciones on-chain.

### 4. Contrato desplegado

El contrato `CFPFactory` debe estar desplegado en el nodo local con la **cuenta en el índice 0 del mnemónico** como deployer (es la que el contrato registra como `owner`). Desde el directorio `contracts`:

```bash
cd ../contracts
npm run deploy
```

La dirección impresa por el script debe asignarse a `CFP_FACTORY_ADDRESS`.

### 5. Artefactos compilados

El test `test_verify_proposal_proofs_onchain` despliega en tiempo de ejecución el contrato auxiliar `MerkleVerifier`, que envuelve `MerkleProof.verify` de OpenZeppelin. Para ello lee su artefacto compilado desde:

```text
../contracts/artifacts/contracts/MerkleVerifier.sol/MerkleVerifier.json
```

Este archivo se genera al compilar los contratos. `npm run deploy` ya incluye la compilación, así que si se siguió el paso anterior el artefacto ya está presente. Si fuera necesario compilar sin desplegar:

```bash
cd ../contracts
npx hardhat compile
```

### 6. Servidor API en ejecución

Los tests envían solicitudes HTTP a `http://127.0.0.1:5000`, por lo que el servidor debe estar corriendo antes de lanzar `pytest`. Las variables de entorno requeridas son `CFP_MNEMONIC`, `CFP_FACTORY_ADDRESS` y `CFP_ADMIN_ADDRESS`.

### Orden de arranque completo

```bash
# 1. Compilar contratos y desplegar (anotar la dirección impresa)
cd contracts && npm install && npm run deploy

# 2. Lanzar el nodo local (en una terminal separada)
npx hardhat node

# 3. Lanzar el servidor en el puerto 5000 (en otra terminal)
#    CFP_MNEMONIC="..." CFP_FACTORY_ADDRESS="0x..." CFP_ADMIN_ADDRESS="0x..." \
#    <comando para iniciar el servidor>

# 4. Ejecutar los tests
CFP_MNEMONIC="..." CFP_FACTORY_ADDRESS="0x..." CFP_ADMIN_ADDRESS="0x..." \
  pytest test_apiserver.py
```

### Ejecución de todos los tests

```bash
pytest test_apiserver.py -v
```

**87 tests** que incorporan los 75 de entregas anteriores más 12 nuevos de Etapa 3.

### Ejecución de un test individual

```bash
pytest test_apiserver.py::test_verify_proposal_proofs_onchain
```

Los tests tienen dependencias de estado entre sí y están diseñados para ejecutarse en orden. La mayoría requiere que `test_register` y `test_create` hayan corrido antes para contar con cuentas autorizadas y llamados registrados en el sistema. Ejecutar un test aislado sin su estado previo puede producir fallas anticipadas (por ejemplo, `AssertionError` en `assert len(accounts) > 0`).

### Total de tests

**87 tests** que cubren:

* Registro y autorización de creadores (con firmas EIP-712)
* Creación y consulta de llamados
* Registro de propuestas con pruebas de Merkle
* Verificación de pruebas on-chain y off-chain
* Validaciones de firma, nonce y direcciones
* Casos borde: administrador no puede registrarse como creador
* **Nuevos en Etapa 3**: Entrega post-cierre con archivos físicos
  * Validación contra recibo original (pruebas de Merkle)
  * Rechazo por convocatoria no cerrada (`CALL_NOT_CLOSED`)
  * Rechazo por entrega duplicada (`ALREADY_DELIVERED`)
  * Consulta de información de entrega (`GET /deliveries`)
  * Descarga de archivos entregados (`GET /deliveries/.../files/...`)
  * Casos borde: recibo inválido, propuesta inexistente, hashes inválidos

Todas las firmas en los tests se generan con EIP-712 mediante `encode_typed_data` y se envían como parte del cuerpo de las solicitudes HTTP.

## Mensajes

| ID                    | Mensaje                                      |
|-----------------------|----------------------------------------------|
| INVALID_ADDRESS       | "Dirección inválida"                         |
| INVALID_SIGNATURE     | "Firma inválida"                             |
| INVALID_MIMETYPE      | "Tipo MIME inválido"                         |
| INVALID_CALLID        | "Identificador de llamado incorrecto"        |
| INVALID_PROPOSAL      | "Formato de propuesta incorrecto"            |
| MISSING_FIELD         | "Campo requerido ausente"                    |
| NAME_TOO_LONG         | "Nombre demasiado largo"                     |
| TITLE_TOO_LONG        | "Título demasiado largo"                     |
| DESCRIPTION_TOO_LONG  | "Descripción demasiado larga"                |
| TOO_MANY_FILES        | "Demasiados archivos"                        |
| PROOF_TOO_LONG        | "Prueba de Merkle demasiado larga"           |
| INVALID_NAME          | "Nombre inválido"                            |
| INVALID_TITLE         | "Título inválido"                            |
| ALREADY_IN_SYSTEM     | "Ya está registrado en el sistema"           |
| ALREADY_CREATED       | "El llamado ya existe"                       |
| ALREADY_REGISTERED    | "La propuesta ya ha sido registrada"         |
| CALLID_NOT_FOUND      | "El llamado no existe"                       |
| PROPOSAL_NOT_FOUND    | "La propuesta no existe"                     |
| UNAUTHORIZED          | "No autorizado"                              |
| NOT_REGISTERED        | "La dirección no está registrada"            |
| NONCE_OVERFLOW        | "Overflow de nonce"                          |
| ADMIN_CANNOT_REGISTER | "La cuenta administradora no puede registrarse como creador" |
| CALL_NOT_CLOSED       | "La convocatoria no ha cerrado"              |
| ALREADY_DELIVERED     | "La entrega ya fue registrada"               |
| NOT_DELIVERED         | "La entrega no ha sido registrada"           |
| NOT_FOUND             | "Recurso no encontrado"                      |
| INTERNAL_ERROR        | "Error interno"                              |
| OK                    | "OK"                                         |
