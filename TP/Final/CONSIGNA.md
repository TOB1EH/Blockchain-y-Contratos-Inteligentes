# Trabajo Práctico Final

Este trabajo implica una modificación y extensión del trabajo práctico 10. El examen final consistirá en la presentación del trabajo, explicación del código y de las decisiones de diseño.

El proyecto debe incluir tres componentes principales, tal como se especifica en el práctico 10:

* Un conjunto de *smart contracts*, ubicados en el subdirectorio `contracts`. Dicho subdirectorio debe tener la estructura de un proyecto `hardhat` y debe ser posible desplegar todos los contratos relevantes ejecutando `npm run deploy` o `npm run deploy:localhost`. Los contratos deben satisfacer como mínimo las especificaciones del Práctico 10, incorporar las extensiones requeridas en este trabajo final y pasar todos los casos de prueba. El directorio `contracts` debe incluir además un `README.md` que describa la nueva estructura de contratos, explique las decisiones de diseño adoptadas y enumere los casos de prueba agregados para verificar las nuevas funcionalidades.

* API REST, situada en el directorio `api`.
Deben proveerse las instrucciones necesarias para desplegar y ejecutar el servidor que provee la API. El directorio `api` debe incluir un `README.md` que describa la estructura final de endpoints, explique las decisiones tomadas y enumere los casos de prueba agregados para verificar las nuevas funcionalidades.

* Interfaz web, en el directorio `web`. Deben proveerse las instrucciones para desplegar y ejecutar el servidor que provee esta interfaz. El directorio `web` debe incluir un `README.md` que describa el *stack* utilizado, la forma de lanzar el servidor y la forma de utilizar la aplicación.

Todo el trabajo final debe ubicarse bajo el directorio `TP/Final`, de modo que los tres componentes se encuentren en `TP/Final/contracts`, `TP/Final/api` y `TP/Final/web` respectivamente. Puede usarse una estructura de directorios diferente dentro de `TP/Final` si las herramientas utilizadas así lo requieren; en ese caso se deberá indicar claramente en qué directorio se encuentra cada uno de los tres componentes.

## Descripción general

Debe proveerse un sistema de gestión de llamados a presentación de propuestas, con los criterios utilizados en el práctico 10.
Pueden modificarse tanto los contratos como la API para proveer las funcionalidades requeridas. Si se agregan nuevos métodos o *endpoints* se deberá proveer lo siguiente:

* Documentación que especifique funcionalidad, argumentos, valores devueltos y condiciones de error, ya sea como comentarios en el código o en el `README.md` correspondiente.

* Casos de prueba

### Funcionalidades adicionales requeridas

#### ENS

A nivel de interfaz, deben reemplazarse todas las direcciones, tanto de contratos como de usuarios, por nombres registrados en un ENS.

Por lo tanto, el conjunto de *smart contracts* debe contener los contratos necesarios para implementar estas funcionalidades. Esto implica, como mínimo:

* Un registro (*registry*).
* Uno o más registradores (*registrars*).
* Uno o más resolutores (*resolvers*).

Estos contratos deben ajustarse a las especificaciones de la [documentación](https://docs.ens.domains/). En particular, para los [*resolvers*](https://docs.ens.domains/contract-api-reference/publicresolver) deben tenerse en cuenta las siguientes *interfaces*:

* [EIP 137](https://eips.ethereum.org/EIPS/eip-137) Direcciones (`addr()`).
* [EIP 165](https://eips.ethereum.org/EIPS/eip-165) Detección de *interface* (`supportsInterface()`).
* [EIP 181](https://eips.ethereum.org/EIPS/eip-181) Resolución reversa (`name()`).

Se usará como dominio de primer nivel el nombre `cfp`. Los dominios a utilizar serán:

* `llamados.cfp`: Dominio donde están los nombres de los llamados. Cada llamado debe estar identificado por un nombre único.
* `usuarios.cfp`: Dominio donde están los nombres de los usuarios, tanto creadores de los llamados como de presentadores de propuestas.
* `addr.reverse`: Dominio para la resolución reversa.

El dueño del registro (*registry*) es el dueño del contrato factoría. Como mínimo, el dominio de primer nivel `cfp` y los subdominios `usuarios.cfp` y `llamados.cfp` quedan bajo su control.

**Registro de usuarios.** El dominio `usuarios.cfp` debe contar con un *registrar* de tipo FIFS (*first-in, first-served*) que permita a cualquier cuenta registrar, por sí misma y desde Metamask, un subnodo `<nombre>.usuarios.cfp` que aún no esté tomado. La cuenta que registra el nombre queda como dueña de su propio subnodo, de modo que pueda configurar tanto la resolución directa (`addr()`) como la reversa (`name()` en `addr.reverse`).

Cada usuario debe registrar su nombre en `usuarios.cfp` **antes** de registrarse como creador. El registro del nombre es un paso previo e independiente del registro como creador (*on-chain* en la factoría y *off-chain* en la API).

**Registro de llamados.** Los llamados creados deben registrarse con un nombre del dominio `llamados.cfp`. El nombre a asociar con el llamado se solicita en el proceso de creación del llamado.

**Manejo de colisiones.** Si el nombre elegido ya está tomado, la registración falla y el registrante debe elegir otro nombre antes de continuar. Esto aplica tanto a los nombres de usuarios como a los de llamados.

La interfaz web debe presentar al menos las siguientes funcionalidades adicionales:

* Permitir que un usuario con Metamask registre, en forma previa al registro como creador, un nombre asociado con su cuenta en el dominio `usuarios.cfp`, configurando tanto la resolución directa como la reversa.
* En el proceso de creación de un llamado se debe pedir el nombre a asociar con el llamado y registrarlo.
* En todos los casos en los que se haga referencia a un contrato o a un usuario, debe figurar su nombre y no su dirección. Para cada consulta del reverso, debe verificarse también la resolución directa para detectar y evitar imposturas.

#### Uso de *tokens* ERC-20

En este sistema existen dos tipos de llamados: aquellos que requieren la presentación de una *garantía de oferta* y aquellos que no la requieren. Es decisión del creador, en el momento de creación del llamado, si la garantía es requerida y, en su caso, cuál es el monto en *tokens* exigido. Este monto es el mismo para todos los oferentes del llamado.

La implementación de ambos tipos de llamado puede resolverse mediante dos contratos distintos o mediante un único contrato en el que la garantía de oferta esté especificada con un monto igual a cero (sin garantía) o mayor que cero (con garantía). La elección y su justificación quedan a criterio del estudiante.

**Llamados sin garantía.** La presentación de propuestas es anónima y se realiza íntegramente a través de la API, exactamente como en el práctico 10. Ese circuito sigue funcionando sin cambios.

**Llamados con garantía.** La presentación deja de ser anónima. Solo está habilitada para usuarios con Metamask y requiere el registro previo del nombre del oferente en ENS (ver sección ENS). Presentar una propuesta implica depositar el monto de garantía en *tokens* en el contrato `CFP` del llamado, mediante el patrón `approve`/`transferFrom`: el oferente autoriza (`approve`) al contrato `CFP` a retirar el monto de garantía y la presentación ejecuta el `transferFrom` correspondiente.

**Finalización y devolución de garantías.** Por simplicidad, el sistema no resuelve quién es el ganador de la licitación. El creador del llamado debe poder dar por finalizado el proceso y determinar a quiénes corresponde la devolución de la garantía de oferta. Esto permite modelar tanto el caso en que el llamado se declara desierto (no se adjudica a nadie y se devuelve la garantía a todos los oferentes) como el caso en que hay uno o más ganadores. El monto a devolver a cada oferente es siempre el monto de garantía especificado en la creación del llamado, igual para todos.

La devolución utiliza un mecanismo de tipo *pull*: el contrato autoriza a cada oferente con derecho a devolución a transferir sus *tokens*, y es el propio oferente quien ejecuta el retiro.

**Token ERC-20.** El *token* tiene un precio fijo en `ETH`, establecido en la creación del contrato ERC-20. El contrato debe permitir la compra y la redención de *tokens* contra `ETH` a ese precio fijo. La cantidad de decimales del *token* queda a criterio del estudiante.

Para implementar esta funcionalidad se debe:

* Desarrollar y desplegar un contrato que cumpla con el estándar ERC-20 y que permita la compra y redención de *tokens* con `ETH` a un precio fijo establecido en su creación.

* Modificar los contratos existentes para que existan llamados que requieren la presentación de una garantía de oferta por un monto en *tokens* especificado por el creador, y permitan su devolución posterior mediante un mecanismo *pull*.

* Modificar la API si se considera necesario.

* Modificar la interfaz web para que:

  * Los creadores de llamados puedan especificar, al crear un llamado, si se requiere una garantía de oferta y, en su caso, el monto exigido.
  * En el caso de llamados con garantía de oferta, se requiera el uso de Metamask y el registro previo en ENS, y la presentación de una oferta implique la transferencia de *tokens* del oferente al contrato `CFP` mediante `approve`/`transferFrom`. Debe existir además una forma en la cual el creador del `CFP` pueda dar por finalizado el procedimiento y habilitar la devolución de la garantía a los oferentes que determine, quienes la retiran mediante el mecanismo *pull*.
  * Los potenciales oferentes puedan comprar y redimir *tokens*.

## Despliegue y puesta en marcha

La entrega debe documentar de forma completa y reproducible todos los pasos necesarios para poner en funcionamiento el sistema desde cero, incluyendo:

* El despliegue de **todos** los contratos relevantes: el contrato `CFPFactory` y los contratos de llamado, los contratos de ENS (*registry*, *registrars* y *resolvers*) y el contrato del *token* ERC-20. Debe ser posible desplegarlos mediante `npm run deploy` o `npm run deploy:localhost` desde el directorio `contracts`, manteniendo los requisitos de despliegue del práctico 10 (en particular, la generación de la frase mnemónica del *owner* y el financiamiento de las cuentas de Metamask).
* El lanzamiento del servidor de la API.
* El lanzamiento del servidor de la interfaz web.

El proceso de despliegue debe emitir en forma explícita toda la información necesaria para configurar el entorno de ejecución de la API y de la interfaz web. Además de las variables ya requeridas por el práctico 10 (como mínimo `CFP_FACTORY_ADDRESS`, `CFP_MNEMONIC` y `CFP_ADMIN_ADDRESS`), deben informarse las direcciones de los nuevos contratos necesarias para que la API y la web puedan operar con ENS y con el *token* ERC-20 (por ejemplo, la dirección del *registry* de ENS y la dirección del contrato del *token*).

La documentación de despliegue debe ser suficiente para que, a partir de un entorno limpio, se puedan desplegar los contratos y lanzar la API y la interfaz web siguiendo los pasos indicados, sin conocimiento previo del proyecto.

## Entrega

La entrega es única y comprende los tres componentes (contratos, API e interfaz web) con su código, documentación y casos de prueba. Debe realizarse a más tardar 7 días antes de la fecha del examen final.
