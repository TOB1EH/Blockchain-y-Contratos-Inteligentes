# Decisiones de Diseno

## 1. Contrato unico CFP con `guaranteeAmount`

**Decision**: Un solo contrato CFP donde `guaranteeAmount == 0` indica "sin garantia" (comportamiento identico al TP/10) y `guaranteeAmount > 0` indica "con garantia".

**Alternativa descartada**: Dos contratos separados (CFP + CFPGuaranteed).

**Justificacion**:
- Elimina duplicacion de codigo (logica de propuestas, deliveries, eventos)
- Cero riesgo de desincronizacion entre contratos
- La API distingue el tipo por el campo `guaranteeAmount`
- Menos superficie de testing
- Mas facil de mantener y explicar en el examen

## 2. Contratos ENS propios (basados en ejemplos del profesor)

**Decision**: Usar los contratos ENS proporcionados por el profesor en `ejemplos/ENS/`.

**Alternativa descartada**: `@ensdomains/ens-contracts` (libreria oficial).

**Justificacion**:
- Los contratos del profesor son exactamente lo que evaluara
- Son mucho mas simples (~50-120 lineas vs ~2000 lineas de los oficiales)
- Sin dependencia npm pesada adicional
- Implementan exactamente EIP-137 (addr), EIP-165 (supportsInterface), EIP-181 (name)
- Facil de explicar en el examen: cada contrato hace una cosa y la hace bien

## 3. OpenZeppelin v5.3.0 para ERC-20

**Decision**: Usar `@openzeppelin/contracts@5.3.0` con Solidity 0.8.28.

**Justificacion**:
- El profesor lo usa asi en `ejemplos/ERC20/`
- OpenZeppelin es la libreria estandar de contratos auditados
- v5.x cambia `Ownable` para recibir el owner en el constructor (`Ownable(msg.sender)`)
- ERC-20 con 18 decimales por default (estandar Ethereum)

## 4. Token con `buy()` y `redeem()` simetricos

**Decision**: `buy()` mints tokens a cambio de ETH, `redeem()` burns tokens y devuelve ETH. Ambos al mismo precio fijo (`TOKENS_PER_ETH`).

**Alternativa descartada**: Solo `buy()` con `withdraw()` del profesor (sin redemption).

**Justificacion**: La consigna exige explicitamente "compra y redencion de tokens contra ETH". El mecanismo debe ser simetrico.

## 5. Mecanismo pull para reembolso de garantias

**Decision**: `finalize()` desbloquea reembolsos. Cada proposer no aceptado llama `claimRefund()` con la lista de aceptados como prueba.

**Patron**: Checks-Effects-Interactions (previene reentrancia):
1. Verificar que la propuesta del caller no este en la lista de aceptadas
2. Verificar que el saldo de garantia del caller sea > 0
3. Marcar garantia como reembolsada (efecto primero)
4. Transferir tokens (interaccion despues)

**Justificacion**: La consigna lo pide explicitamente ("mecanismo de tipo pull"). Se pasa la lista de aceptados como parametro para no requerir almacenamiento on-chain de los ganadores.

## 6. ENS como prerrequisito para registro de creador

**Decision**: El usuario debe registrar su nombre ENS en `usuarios.cfp` ANTES de registrarse como creador (paso 1 on-chain en CFPFactory).

**Flujo**: `registrar(label, address)` -> `setResolver()` + `setAddr()` -> `reverseRegistrar.setName()` -> recien ahi `CFPFactory.register()`

**Justificacion**: La consigna lo especifica: "Cada usuario debe registrar su nombre en usuarios.cfp antes de registrarse como creador."

## 7. Propuesta con garantia via MetaMask directo (no API)

**Decision**: Para llamados con `guaranteeAmount > 0`, el usuario firma tx directamente desde MetaMask al CFP (no pasa por la API).

**Justificacion**:
- La API no tiene acceso a los tokens del usuario (no es custodio)
- `approve`/`transferFrom` requiere que el usuario firme con MetaMask
- El frontend computa el proposalId via la API (mismo algoritmo Merkle)
- La API devuelve `requiresCollateral: true` para que el frontend active el paso MetaMask

## 8. API como proxy ENS

**Decision**: La API expone endpoints `/ens/resolve` y `/ens/reverse` para consultas ENS. El frontend no tiene conexion directa al nodo Ethereum fuera de MetaMask.

**Alternativa descartada**: Resolucion ENS directa desde el frontend via ethers.js.

**Justificacion**: MetaMask solo expone `window.ethereum` para la cuenta conectada, no para consultas arbitrarias a contratos. La API tiene conexion directa al nodo y puede resolver nombres sin depender de MetaMask. Unifica el punto de acceso a datos on-chain.

## 9. Nombres de llamados gestionados por la API (owner)

**Decision**: `llamados.cfp` queda bajo control directo del deployer (cuenta del servidor API). Cuando la API detecta `CFPCreated` para un llamado con `ens_name`, crea el subnodo `<nombre>.llamados.cfp` usando su cuenta de servidor.

**Alternativa descartada**: FIFSRegistrar publico para `llamados.cfp`.

**Justificacion**: La consigna dice que el dueno del registry es el dueno de la factoria (el deployer). Como el servidor API usa esa misma cuenta, puede crear subnodos sin necesidad de que el creador pague gas por el registro ENS del llamado. Ademas evita que terceros registren nombres de llamados que no les pertenecen.

## 10. Actualizacion a Solidity 0.8.28

**Decision**: Migrar todos los contratos de 0.8.19 a 0.8.28.

**Justificacion**: Los ejemplos del profesor usan ^0.8.28. La version es compatible hacia atras (cambios menores no breaking). Nos alineamos con lo que el profesor espera ver.

## 11. Token con 18 decimales

**Decision**: 18 decimales (default de OpenZeppelin ERC-20).

**Justificacion**: Es el estandar de Ethereum. Coincide con ETH (tambien 18 decimales), simplificando los calculos de precio y la integracion con MetaMask/ethers. La consigna deja esta decision al alumno.

## 12. Dos FIFSRegistrars separados (usuarios / llamados)

**Decision**: Desplegar dos instancias de FIFSRegistrar: una con `rootNode = namehash("usuarios.cfp")` para autoregistro de usuarios, y `llamados.cfp` queda bajo control directo del deployer (sin registrar publico).

**Alternativa descartada**: Un solo FIFSRegistrar para `cfp` que gestione todo.

**Justificacion**: La consigna especifica dominios separados `usuarios.cfp` y `llamados.cfp` con propositos distintos. Usuarios se autoregistran (FIFS), llamados los controla el owner de la factoria. Separarlos evita colisiones de nombres y simplifica los permisos.

## 13. Verificacion forward+reverse contra imposturas

**Decision**: En toda resolucion inversa (direccion a nombre), se verifica tambien la resolucion directa (nombre a direccion). Si no coinciden, se sennala como impostura.

**Justificacion**: La consigna lo exige explicitamente: "Para cada consulta del reverso, debe verificarse tambien la resolucion directa para detectar y evitar imposturas."
