# Trabajo Práctico 10

Este trabajo implica una modificación y extensión de los trabajos prácticos 7, 8 y 9.
El proyecto debe incluir tres componentes principales:

* Un conjunto de *smart contracts*, ubicados en el subdirectorio `contracts`. Dicho subdirectorio debe tener la estructura de un proyecto `hardhat` y debe ser posible desplegar todos los contratos relevantes ejecutando `npm run deploy` o `npm run deploy:localhost`. Los contratos deben satisfacer como mínimo las especificaciones del Práctico 9, incorporar las extensiones requeridas en este práctico y pasar todos los casos de prueba. El directorio `contracts` debe incluir además un `README.md` que describa la nueva estructura de contratos, explique las decisiones de diseño adoptadas y enumere los casos de prueba agregados para verificar las nuevas funcionalidades.
* API REST, que satisfaga las especificaciones del práctico 9, y situada en el directorio `api`.
Deben proveerse las instrucciones necesarias para desplegar y ejecutar el servidor que provee la API. El directorio `api` debe incluir un `README.md` que describa la estructura final de endpoints, explique las decisiones tomadas y enumere los casos de prueba agregados para verificar las nuevas funcionalidades.

* Interface web, en el directorio `web`. Deben proveerse las instrucciones para desplegar y ejecutar el servidor que provee esta interface. El directorio `web` debe incluir un `README.md` que describa el *stack* utilizado, la forma de lanzar el servidor y la forma de utilizar la aplicación.

Puede usarse una estructura de directorios diferente si las herramientas utilizadas así lo requieren. En este caso se deberá indicar claramente en qué directorio se encuentra cada uno de los tres componentes.

## Descripción general

Debe proveerse un sistema de gestión de llamados a presentación de propuestas, con los criterios utilizados en los prácticos 7, 8 y 9.
Este práctico requiere modificaciones tanto en los contratos como en la API, además del desarrollo de una interfaz web completa. Si se agregan nuevos métodos o *endpoints* se deberá proveer lo siguiente:

* Documentación que especifique funcionalidad, argumentos, valores devueltos y condiciones de error, ya sea como comentarios en el código o en el `README.md` correspondiente.
* Documentación del esquema de base de datos *off-chain* utilizado (tablas/colecciones, campos, claves, restricciones y relaciones).
* Casos de prueba

## Requisitos adicionales de contratos, API y despliegue

Además de las funcionalidades descriptas más abajo, deberán cumplirse los siguientes requisitos mínimos.

### Contratos

Los contratos deberán ser extendidos respecto del práctico anterior. Como mínimo deberán incorporarse:

* Eventos adicionales para todos los nuevos hechos significativos que este práctico introduce.
* Al menos un método público adicional, debidamente documentado y cubierto por pruebas, que permita registrar en cadena la entrega final posterior al cierre del llamado.

La especificación concreta de nombres, argumentos y restricciones de estos métodos puede variar, pero debe quedar documentada en el `README.md` del directorio `contracts`.

### API

La API podrá extender la estructura de endpoints del práctico 9 para soportar los nuevos flujos de la interfaz web y la recepción final de archivos. En particular, es esperable la incorporación de endpoints adicionales para:

* identificar la cuenta administradora utilizada por la interfaz;
* registrar o confirmar la entrega final posterior al cierre;
* consultar la información pública derivada de esa entrega final.

Además, cambiaremos el esquema de firma. En el práctico 9 utilizamos la firma EIP-191, en este utilizaremos la firma EIP-712. Esto implica cambiar la implementación de todos los endpoints que reciben y procesan una firma, y cambiar los casos de prueba conforme a la nueva implementación.

#### Principio de fuente de verdad *on-chain*

Toda consulta que haga referencia a información cuya fuente de verdad es el contrato (estado de autorización de un creador, existencia o estado de un llamado, etc.) debe resolverse **consultando directamente a la cadena** en el momento de la solicitud. La API no debe cachear ni responder con datos almacenados localmente cuando la información canónica proviene del contrato.

#### Dominio EIP-712

Todas las firmas comparten el mismo dominio:

```json
{
  "name": "CFP API",
  "version": "1",
  "chainId": <id de la cadena>,
  "verifyingContract": "<dirección del contrato CFPFactory>"
}
```

#### Tipos de mensaje

Cada endpoint que requiere firma define su propio tipo estructurado. El campo `operation` identifica la operación dentro del tipo y previene el reuso de firmas entre operaciones distintas.

**`CreateRequest`** — registro de llamado (`POST /create`):

| Campo       | Tipo      | Valor                               |
|-------------|-----------|-------------------------------------|
| `operation` | `string`  | `"create"`                          |
| `contract`  | `address` | Dirección del contrato `CFPFactory` |
| `callId`    | `bytes32` | Hash que identifica al llamado      |

La API recupera la dirección firmante y verifica que esté autorizada en el contrato.

**`RegisterRequest`** — registro de creador (`POST /register`) y actualización de perfil (`PATCH /registrations/:address`):

| Campo       | Tipo      | Registro                                                         | Actualización de perfil             |
|-------------|-----------|------------------------------------------------------------------|-------------------------------------|
| `operation` | `string`  | `"register"`                                                     | `"update"`                          |
| `contract`  | `address` | Dirección del contrato `CFPFactory`                              | Dirección del contrato `CFPFactory` |
| `nonce`     | `uint256` | Nonce actual (obtenido de la API; `0` para primera registración) | Nonce actual (obtenido de la API)   |
| `name`      | `string`  | Nombre del solicitante                                           | Nuevo nombre                        |

La API recupera la dirección firmante y verifica que coincida con la dirección del solicitante. Tras una actualización exitosa el nonce se incrementa.

**`AdminActionRequest`** — autorización (`POST /authorize/:address`) y desautorización (`POST /unauthorize/:address`):

| Campo       | Tipo      | Autorizar                           | Desautorizar                        |
|-------------|-----------|-------------------------------------|-------------------------------------|
| `operation` | `string`  | `"authorize"`                       | `"unauthorize"`                     |
| `contract`  | `address` | Dirección del contrato `CFPFactory` | Dirección del contrato `CFPFactory` |
| `nonce`     | `uint256` | Nonce actual (obtenido de la API)   | Nonce actual (obtenido de la API)   |
| `target`    | `address` | Dirección a autorizar               | Dirección a desautorizar            |

La API recupera la dirección firmante y verifica que coincida con `CFP_ADMIN_ADDRESS`. Tras cada operación exitosa el nonce del administrador se incrementa.

Toda ampliación deberá quedar documentada en el `README.md` del directorio `api`, junto con sus casos de prueba. Esa documentación debe incluir además los *schemas* de la base de datos *off-chain* utilizada por la API.

### Despliegue

#### Cuenta owner del contrato (`CFP_MNEMONIC`)

El mecanismo de despliegue de contratos debe incluir, en el mismo script o en otro script correctamente documentado, la generación de una frase mnemónica distinta de la utilizada por Hardhat por defecto. La primera cuenta derivada de esa frase mnemónica es la cuenta que despliega el contrato `CFPFactory` y, por lo tanto, su dueña (*owner*). Es la única cuenta con privilegios de *owner* sobre ese contrato y la única que puede ejecutar las operaciones que lo requieran (por ejemplo, autorizar o desautorizar creadores directamente desde el contrato).

La API utiliza internamente esa misma cuenta para todas las transacciones *on-chain* que requieren privilegios de *owner*. **Nadie externo a los scripts de despliegue y a la API tiene acceso a esta frase mnemónica**; no es una cuenta de usuario ni debe aparecer en Metamask. La frase se provee a la API mediante la variable de entorno `CFP_MNEMONIC`.

#### Cuenta administradora (`CFP_ADMIN_ADDRESS`)

La cuenta administradora es una cuenta completamente distinta de la anterior. No se deriva de `CFP_MNEMONIC` ni está relacionada con ella. Es una cuenta ordinaria de Metamask, controlada por un usuario humano, que opera desde la interfaz web firmando mensajes EIP-712 con su *wallet*. **La cuenta administradora no tiene ningún privilegio directo sobre el contrato**: no es el *owner* ni puede ejecutar funciones restringidas. Su privilegio es exclusivamente a nivel de la API: ésta reconoce su dirección y acepta sus órdenes administrativas (autorizar/desautorizar creadores) siempre que vengan acompañadas de una firma EIP-712 válida.

La dirección de la cuenta administradora se provee a la API mediante la variable de entorno `CFP_ADMIN_ADDRESS`. **La cuenta administradora no puede registrarse como creador ni operar como tal.**

#### Financiamiento de cuentas de Metamask

Las firmas EIP-712 utilizadas para interactuar con la API no consumen gas, pero las transacciones *on-chain* (registro, creación de llamados, etc.) sí lo hacen. Por ello debe existir un script, correctamente documentado, que reciba como argumento la frase mnemónica de Metamask y transfiera 1000 `ether` a cada una de las primeras 10 cuentas generadas por esa frase. Este script se ejecuta una vez durante la preparación del entorno de desarrollo, antes de que los usuarios comiencen a operar con Metamask.

#### Variables de entorno requeridas

El proceso de despliegue y preparación de cuentas debe emitir en forma explícita la información necesaria para configurar el entorno de ejecución. Como mínimo debe informar:

* `CFP_FACTORY_ADDRESS`
* `CFP_MNEMONIC`

La salida del script debe ser suficiente para que un usuario pueda lanzar la API con las variables de entorno correctas.

El servidor de API requiere además la variable `CFP_ADMIN_ADDRESS` al momento de ejecución.
La responsabilidad de proveer `CFP_FACTORY_ADDRESS`, `CFP_MNEMONIC` y `CFP_ADMIN_ADDRESS` recae en quien invoca el servidor.
Esas mismas variables deben ser provistas también al ejecutar los casos de prueba de la API.

### Especificación funcional de la interfaz web

La interfaz web de `TP/10/web` debe funcionar como cliente de la API y de los contratos, integrando:

* Contratos desplegados (factoría y llamados), con firma de transacciones mediante Metamask cuando corresponda.
* API REST, extendida según sea necesario para soportar los nuevos flujos, la persistencia *off-chain* y la verificación de pruebas.

La aplicación debe separar claramente operaciones:

* ***On-chain* con Metamask**: acciones que requieren identidad del usuario y firma/transacción desde su *wallet*.
* ***Off-chain* vía API**: acciones de consulta, persistencia de metadatos, generación y validación de pruebas/recibos, y carga/descarga de archivos.

Metamask debe utilizar una frase mnemónica distinta que Hardhat. Dado que las firmas EIP-712 no consumen gas pero las transacciones *on-chain* sí, debe proveerse un script que reciba la frase mnemónica de Metamask y transfiera 1000 `ether` a cada una de las primeras 10 cuentas generadas por esa frase, de modo que todas ellas puedan operar en la red de desarrollo. Este script debe ejecutarse como parte del proceso de preparación del entorno antes de usar la interfaz web.

### Comportamiento según el rol activo

La interfaz debe adaptarse al contexto del usuario conectado o no conectado. En particular:

* Si el usuario no tiene Metamask instalado, no conectó ninguna cuenta, o no autorizó el acceso, el sitio debe seguir siendo plenamente funcional para todas las operaciones públicas y anónimas.
* En ese caso, la interfaz debe mostrar únicamente las acciones que pueden realizarse sin *wallet*: exploración pública, consulta de llamados y verificación de recibos.
* Si el usuario se conecta como administrador, la interfaz debe mostrar todas las acciones disponibles para administración, además de todas las acciones públicas.
* Si el usuario se conecta como creador, la interfaz debe mostrar todas las acciones públicas y las acciones propias del rol creador, incluyendo registro, consulta de estado, actualización de perfil y creación de llamados cuando corresponda.
* Si el usuario posee una cuenta pero no pertenece a un rol habilitado para alguna operación, la interfaz no debe ocultar las funciones públicas ni impedir su navegación; únicamente debe deshabilitar o explicar las acciones restringidas.

Para implementar este comportamiento, la API debe exponer un endpoint de solo lectura que devuelva la cuenta administrativa, de modo que la interfaz pueda determinar si la cuenta conectada corresponde al administrador. Por ejemplo, la API puede exponer un endpoint como `GET /admin/address` o equivalente, además de los endpoints de estado ya definidos para creadores y administradores.

## Roles y permisos

La interfaz debe admitir los siguientes roles funcionales.

### 1. Administrador

Corresponde a la cuenta administradora definida por la API mediante `CFP_ADMIN_ADDRESS`. Es una cuenta de Metamask controlada por un usuario humano, completamente distinta del *owner on-chain* (`CFP_MNEMONIC`). Opera desde la interfaz web firmando mensajes EIP-712 con su *wallet*; no tiene privilegios directos sobre el contrato y no puede enviar transacciones en nombre del *owner*.

Debe poder:

* Ver listado de solicitudes de registro de creadores.
* Autorizar creadores.
* Desautorizar creadores.

Requisitos de interacción:

* La UI debe mostrar el `nonce` actual del administrador (obtenido desde API) o manejarlo internamente para firma correcta.
* Las operaciones de autorizar/desautorizar deben requerir confirmación explícita del usuario administrador.
* El resultado de cada operación debe reflejarse correctamente tanto en el estado que devuelve la API como en el estado del contrato.

Restricciones del rol administrador:

* La cuenta administradora no puede registrarse como creador ni presentar propuestas en ningún llamado.

### 2. Creador de propuestas

Usuario que se registra con su dirección y datos en el sistema.

Debe poder:

* Registrarse como creador con Metamask.
* Consultar estado de registración (`pending`, `registered`, `authorized`).
* Si está autorizado, crear llamados.
* En cualquier estado (registrado o autorizado), actualizar su información de perfil a través de la API (operación que requiere firma EIP-712):
  * nombre
  * descripción

#### Doble interacción: cadena y API

Las operaciones de los creadores requieren interacción con dos sistemas independientes:

1. ***On-chain***: el creador ejecuta funciones del contrato (`register()`, `create()`, etc.) desde Metamask. Estas transacciones consumen gas y quedan registradas en la cadena.
2. ***Off-chain***: el creador también debe interactuar con la API para persistir los datos que no se almacenan en el contrato (por ejemplo, su nombre, descripción u otros metadatos).

Ambas interacciones son necesarias para que la operación se considere completa. La API **escucha los eventos emitidos por el contrato** para saber que la operación *on-chain* fue efectivamente ejecutada, y solo entonces actualiza el estado correspondiente en la base de datos *off-chain*. El orden en que el usuario realiza las dos interacciones puede variar, por lo que deben manejarse adecuadamente los estados intermedios que resulten de las distintas combinaciones posibles.

Toda consulta de información que tenga origen *on-chain* (estado de autorización, existencia de un llamado, etc.) debe realizarse consultando directamente a la cadena. La API no debe responder con datos almacenados localmente cuando la fuente de verdad es el contrato.

#### Estados de registración

| Acciones previas                               | En contrato | En API | Estado       | Observación                                                                                                      |
|------------------------------------------------|-------------|--------|--------------|------------------------------------------------------------------------------------------------------------------|
| Ninguna                                        | no          | no     | `pending`    | Estado inicial.                                                                                                  |
| Registrado en el contrato solamente            | sí          | no     | `pending`    | Interacción *on-chain* completada; la API aún no recibió los datos.                       |
| Registrado en la API solamente                 | no          | sí     | `pending`    | Interacción con la API completada; la transacción *on-chain* aún no fue minada, fracasó, o aún no fue detectada. |
| Registrado en ambos, pendiente de autorización | sí          | sí     | `registered` | El creador completó ambas interacciones y espera que el administrador lo autorice.                               |
| Autorizado por el administrador                | sí          | sí     | `authorized` | El administrador ejecutó la autorización *on-chain*; el creador puede crear llamados.                            |
| Desautorizado por el administrador             | no          | sí     | `pending`    | El administrador ejecutó la desautorización *on-chain*. Los datos en la API se preservan para evitar *replay*.   |

Tras una desautorización la cuenta vuelve a `pending`: se elimina del contrato pero sus datos en la API se preservan (en particular el `nonce`), lo que impide ataques de *replay* con firmas anteriores. El creador puede volver a registrarse en el contrato para solicitar una nueva autorización.

#### Notas

* Si el usuario ya se registró y aún no fue autorizado, la UI debe priorizar mostrar el estado de su solicitud y no bloquear la edición de su información.
* La actualización de información debe requerir firma (cuando la API así lo exija) y manejar nonces de forma robusta.

### 3. Público general

Sin autenticación obligatoria, cualquier usuario debe poder consultar:

* Listado de creadores de propuestas.
* Listado de llamados de un creador específico.
* Listado global de llamados abiertos, independientemente del creador.

Estas vistas deben funcionar sin *wallet* conectada.

### 4. Oferente (presentación de propuesta)

Cualquier usuario (con o sin Metamask) debe poder presentar una propuesta para un llamado:

* Completar datos de propuesta.
* Adjuntar archivos.
* Permitir que el sistema calcule hashes de archivos y genere el identificador/compromiso criptográfico correspondiente.

Como respuesta, el sistema debe devolver un **recibo verificable** que incluya como mínimo:

* `callId`
* `proposalId` (raíz/identificador criptográfico)
* pruebas necesarias para verificar pertenencia (por ejemplo pruebas de Merkle)
* hash(es) de archivos y de campos relevantes
* referencia de transacción/evento *on-chain* asociado
* *timestamp*

Privacidad:

* El contenido completo presentado (datos y archivos) no es público en esta etapa.
* Solo quien posee los datos originales y el recibo puede revalidar su integridad.

Verificación por recibo:

* Debe existir una pantalla para subir el recibo y verificar en cualquier momento que:
  * los datos coinciden con los hashes comprometidos
  * el compromiso existe en la cadena
  * las pruebas incluidas son válidas

### 5. Oferente (entrega post-cierre)

Una vez cerrado un llamado:

* El oferente debe subir:
  * recibo original de presentación
  * todos los archivos comprometidos
* El servidor verifica integridad contra las pruebas del recibo.
* Si todo coincide, el servidor registra en cadena la **recepción de archivos**.
* El servidor devuelve un **recibo de recepción** con evidencia *on-chain* de la recepción.

Persistencia y consulta:

* Los archivos entregados se almacenan en el servidor.
* Esos archivos pasan a ser consultables públicamente por cualquiera.

## Flujos obligatorios de UI

La interfaz debe incluir, como mínimo, los siguientes módulos/pantallas:

* Inicio/Exploración pública:
  * listado de creadores
  * listado de llamados abiertos
  * filtro por creador
* Acceso *wallet* (Metamask):
  * conectar/desconectar cuenta
  * detectar red incorrecta y guiar cambio de red
* Panel de creador:
  * registro y estado
  * actualización de perfil
  * creación de llamado (solo autorizado)
* Panel de administración:
  * solicitudes pendientes
  * autorizar/desautorizar
* Presentación de propuesta:
  * carga de datos y archivos
  * generación y descarga de recibo
* Verificación de propuesta:
  * carga de recibo
  * validación criptográfica y *on-chain*
* Entrega post-cierre:
  * carga de recibo + archivos completos
  * emisión y descarga de recibo de recepción
  * consulta pública de archivos recibidos

## Integración entre web, API y contratos

La solución debe documentar explícitamente en el `README.md` de `web`:

* Qué operaciones se resuelven por API y cuáles por transacción Metamask.
* Qué endpoints del TP 9 y qué endpoints adicionales consume cada pantalla.
* Qué métodos/eventos de contrato utiliza cada flujo.
* Manejo de errores esperables (firma inválida, nonce inválido, no autorizado, llamado inexistente, etc.).

Además, la UI debe contemplar estados transitorios típicos de *blockchain*:

* transacción pendiente
* transacción confirmada
* transacción fallida/revertida

## Recibos y verificabilidad

El formato exacto del recibo puede definirse libremente (por ejemplo JSON firmado por servidor), pero debe cumplir:

* Ser portable (descargable y reutilizable luego).
* Permitir verificación independiente del lado cliente.
* Incluir referencias suficientes para reconsultar evidencia en cadena (*tx hash*, bloque, evento, contrato).
* Versionado de formato para compatibilidad futura.

## Eventos *on-chain* obligatorios

Todos los hechos significativos registrados en cadena deben emitir eventos adecuados, al menos para:

* registro de creador
* autorización de creador
* desautorización de creador
* creación de llamado
* registro de propuesta/compromiso
* recepción de archivos post-cierre

Cada evento debe incluir los identificadores necesarios para trazabilidad entre:

* entidad *on-chain* (direcciones, ids, hashes)
* entidad *off-chain* (registros de API y recibos)

## Entregas parciales (3 etapas)

Para hacer viable el trabajo en más de una semana, dividiremos la implementación en tres entregas incrementales. Cada etapa debe incluir código funcionando, documentación y casos de prueba de lo incorporado.

### Etapa 1: Base operativa (consulta pública + registro de creadores + administración)

Objetivo: disponer de una web navegable, conectada a la API, con soporte de *wallet*, flujo inicial de creadores y administración básica de autorizaciones.

Alcance mínimo:

* Estructura del proyecto `web`, instrucciones de instalación y ejecución.
* Conexión a API y manejo de errores básicos.
* Conexión con Metamask (conectar/desconectar cuenta, validación de red).
* Vistas públicas:
  * listado de creadores
* Flujo de creador:
  * registro con *wallet*
  * consulta de estado de registración
  * actualización de perfil
* Panel de administración:
  * listado de solicitudes
  * autorizar creadores
  * desautorizar creadores

Entregables de la etapa:

* Código de *frontend* funcionando para los flujos anteriores.
* Documento breve de arquitectura (qué consume de API y cómo usa Metamask).
* Pruebas (al menos integración/UI o pruebas de componentes para los módulos implementados).

### Etapa 2: Gestión de llamados

Objetivo: permitir que creadores autorizados publiquen llamados y que el sistema exponga sus listados públicos.

Alcance mínimo:

* Panel de creador autorizado:
  * creación de llamados
  * *feedback* de estado de transacción (pendiente, confirmada, fallida)
* Vistas públicas de llamados:
  * listado de llamados por creador
  * listado global de llamados abiertos
* Integración explícita web/API/contratos documentada por pantalla.
* Eventos *on-chain* implementados y consumibles para:
  * creación de llamado

Entregables de la etapa:

* Funcionalidad completa para creación y listado de llamados.
* Casos de prueba para llamadas públicas y creador autorizado.
* Actualización del README de `web` con mapeo endpoint/método por flujo.

### Etapa 3: Propuestas, recibos y entrega post-cierre

Objetivo: completar el ciclo de vida de propuestas con verificabilidad criptográfica y publicación posterior de archivos.

Alcance mínimo:

* Presentación de propuesta para cualquier usuario:
  * carga de datos
  * carga de archivos
  * cálculo de hashes
  * registro del compromiso *on-chain* a través de la API (la API firma y envía la transacción con su propia cuenta, sin requerir intervención del oferente)
* Emisión de recibo de presentación con evidencia verificable.
* Pantalla de verificación por recibo (subida de recibo y validación completa).
* Flujo post-cierre:
  * subida de recibo + archivos completos
  * validación de pruebas
  * registro *on-chain* de recepción
  * emisión de recibo de recepción
* Publicación y consulta pública de archivos una vez recibidos.
* Eventos *on-chain* para:
  * registro de propuesta/compromiso
  * recepción de archivos post-cierre

Entregables de la etapa:

* Funcionalidad completa del ciclo de propuestas.
* Especificación del formato de recibos (campos, versión, validación).
* Pruebas end-to-end del flujo completo: presentar -> verificar -> entregar post-cierre -> consultar archivos.

## Criterios de aceptación

Se considera cumplida la especificación cuando:

* La aplicación web permite operar correctamente todos los roles y flujos definidos arriba.
* Las operaciones que requieren identidad del usuario se resuelven con Metamask.
* La presentación de propuestas es anónima y se realiza íntegramente a través de la API.
* Las operaciones de persistencia/verificación *off-chain* usan la API.
* Los recibos permiten verificar de manera consistente lo registrado en cadena.
* La recepción post-cierre deja evidencia *on-chain*, almacena los archivos y los hace accesibles públicamente.
* Existen eventos para todos los hechos significativos.

## Tags de entrega

Dado que el práctico se entrega en varias etapas dentro de un mismo repositorio, cada hito debe quedar marcado con un tag de git para facilitar la corrección y la recuperación de una versión estable de cada entrega parcial.

Usaremos la siguiente convención:

* `tp10-etapa1` para la primera entrega, correspondiente a la base operativa, registro de creadores y administración básica.
* `tp10-etapa2` para la segunda entrega, correspondiente a gestión de llamados.
* `tp10-etapa3` para la tercera entrega, correspondiente a propuestas, recibos y entrega post-cierre.

### Cómo usar los tags

Una vez terminado cada hito, debe crearse el tag apuntando al commit que deja el repositorio en un estado consistente y verificable.

Ejemplos:

```bash
git tag tp10-etapa1
git tag tp10-etapa2
git tag tp10-etapa3
```

Si el tag ya fue creado localmente y se desea publicarlo en el remoto:

```bash
git push origin tp10-etapa1
git push origin tp10-etapa2
git push origin tp10-etapa3
```

Para listar las versiones etiquetadas disponibles:

```bash
git tag --list 'tp10-etapa*'
```

Para inspeccionar o verificar una entrega puntual, se puede hacer checkout del tag correspondiente:

```bash
git checkout tp10-etapa2
```

Luego, para volver a la rama principal de trabajo:

```bash
git checkout master
```

Cada tag debe referir a una versión completa de la etapa: con código, documentación y pruebas coherentes con el alcance indicado para esa entrega.

## Metamask

Metamask es una *wallet* para navegador que permite administrar cuentas de Ethereum y firmar mensajes o transacciones sin exponer la clave privada a la aplicación web. En este práctico debe utilizarse como el mecanismo de identidad del usuario para todas las operaciones que requieran intervención directa sobre la cadena.

La interfaz web debe contemplar, como mínimo, los siguientes aspectos de uso:

* Permitir que el usuario conecte y desconecte su cuenta desde el navegador.
* Detectar la red activa y advertir cuando no coincida con la red donde están desplegados los contratos.
* Solicitar firma de transacciones *on-chain* para registrar acciones sobre el contrato que dependen de la identidad del usuario, por ejemplo el registro o la creación de llamados.
* Solicitar firma de mensajes cuando la API lo requiera para validar operaciones *off-chain* asociadas a una dirección determinada.

La aplicación debe tratar a Metamask como una dependencia explícita de la interfaz. Si la extensión no está instalada, si el usuario no autorizó la cuenta, o si la red es incorrecta, la UI debe informar la situación de manera clara y permitir que el usuario continúe, cuando corresponda, con las funcionalidades públicas del sistema.

Puede encontrarse un ejemplo del uso de Metamask en la carpeta [`ejemplos/metamask`](../../ejemplos/metamask/) del repositorio.