# Flujo de prueba de la DApp CFP

## Ideas fundamentales

La aplicacion implementa un sistema de **Convocatorias para Financiamiento de Proyectos (CFP)** sobre Ethereum. Hay tres roles bien diferenciados:

| Rol | Quien es | Que hace |
|-----|----------|----------|
| **Admin** | Cuenta #0 de MetaMask | Autoriza creadores |
| **Creador** | Cuentas #1..#9 de MetaMask | Crea llamados, finaliza, ve propuestas |
| **Proponente** | Cualquiera (sin MetaMask) | Presenta propuestas, entrega archivos |

La separacion clave: el Admin es el **owner del contrato CFPFactory**. Solo el puede autorizar/desautorizar creadores. Los creadores son los que interactuan con el sistema creando llamados y recibiendo propuestas.

---

## Flujo paso a paso

### Fase 0: Infraestructura (3 terminales + navegador)

```
Terminal 1: npx hardhat node &          → Blockchain local
Terminal 1: node scripts/deploy.js      → Despliega ENS + Token + CFPFactory
Terminal 2: python3 apiserver.py        → API REST (puerto 5000)
Terminal 3: npm run dev                 → Frontend Vue (puerto 5173)
MetaMask:  red = localhost:8545 (chain 31337)
           cuenta importada con frase MetaMask
```

### Fase 1: Registro de creador (por que tantos pasos)

El registro tiene 3 pasos porque cada uno prueba una capa distinta:

**Paso 1 — ENS (Pestana ENS)**
Registra un nombre como `tester.usuarios.cfp` en el sistema de nombres ENS. No tiene que ver con permisos: solo da una identidad legible al usuario. Requiere 4 transacciones MetaMask (register + setResolver + setAddr + setName).

**Paso 2 — On-chain (Pestana Creador: "Registrarse on-chain")**
Llama a `CFPFactory.register()` para registrar la direccion en el contrato. Esto deja constancia en la blockchain de que esta direccion quiere ser creador. Sin este paso, el contrato no sabe que existe.

**Paso 3 — Off-chain (Pestana Creador: "Registrarse off-chain")**
Firma un mensaje EIP-712 (sin gas, solo firma) que la API guarda en su base de datos local. La API necesita este registro off-chain para asociar nombre y nonce al usuario.

**Por que separar on-chain y off-chain?**
- On-chain: la verdad definitiva (quien esta autorizado).
- Off-chain: metadatos (nombre, nonce para anti-replay). Guardar strings en Ethereum sale caro, por eso van en DB.

**Paso 4 — Admin autoriza (Pestana Admin)**
El admin firma un mensaje EIP-712 que la API usa para llamar `CFPFactory.authorize()`. Sin autorizacion, el creador no puede crear llamados. Es el paso que realmente da permiso.

### Fase 2: Crear un llamado (Pestana Creador)

El creador llena titulo, descripcion y fecha de cierre.

- **La fecha de cierre debe ser FUTURA** (en Unix timestamp). Si la fecha ya paso, el constructor del contrato CFP revierte con "El cierre de la convocatoria no puede estar en el pasado".
- Si se fija guaranteeAmount > 0, los proponentes deberan depositar tokens como garantia.
- Si se fija guaranteeAmount = 0, cualquiera puede proponer sin costo.
- La API guarda el llamado como "pending" primero. Cuando el event listener de la API detecta el evento `CFPCreated` en la blockchain, cambia el estado a "created".

**Dos firmas**: EIP-712 (sin gas) para avisar a la API, luego transaccion real `CFPFactory.create()` via MetaMask.

### Fase 3: Presentar propuesta (Pestana Inicio)

**Sin garantia (recommended para pruebas)**: el proponente sube titulo, descripcion y archivos. La API calcula el arbol de Merkle, guarda los archivos, y devuelve un recibo JSON. La API paga el gas de la transaccion `registerProposal()`.

**Con garantia**: el proponente debe tener tokens CFPGovernanceToken. Los compra en la pestana Token, luego firma `approve()` + `registerProposalWithCollateral()` en MetaMask.

El recibo JSON es la **prueba de presentacion** — contiene los hashes y las pruebas de Merkle. Sin el recibo, no se puede hacer la entrega post-cierre.

### Fase 4: Entrega post-cierre (Pestana Inicio)

Una vez que pasa la fecha de cierre del llamado, el proponente puede entregar los archivos definitivos:

1. Sube el recibo JSON original + los archivos exactos
2. La API verifica que los hashes de los archivos coincidan con las pruebas de Merkle del recibo
3. Si todo coincide, la API llama `CFP.registerDelivery()` (paga el gas)
4. Los archivos quedan visibles publicamente en "Ver Entregas"

Esto demuestra que el proponente presento los archivos correctos sin necesidad de que el creador los valide manualmente.

### Fase 5: Finalizar y reembolso (Pestana Garantia - solo si guarantee > 0)

**Finalizar**: el creador firma `CFP.finalize()` que marca el llamado como finalizado. A partir de ahi, los proponentes no aceptados pueden recuperar su garantia.

**Reclamar reembolso**: el proponente no aceptado firma `CFP.claimRefund()` con su proposal ID y la lista de propuestas aceptadas. Si su propuesta no esta en la lista aceptada, recupera los tokens.

---

## Resumen de quien paga el gas

| Operacion | Paga gas | Comentario |
|-----------|----------|------------|
| Registrar nombre ENS | Usuario (MetaMask) | 4 transacciones |
| Registrarse on-chain | Usuario (MetaMask) | 1 transaccion |
| Crear llamado | Usuario (MetaMask) | 1 transaccion |
| Autorizar creador | API (server_account) | Usuario solo firma EIP-712 |
| Presentar propuesta (sin garantia) | API (server_account) | Solo si guaranteeAmount = 0 |
| Presentar propuesta (con garantia) | Usuario (MetaMask) | approve + registerProposalWithCollateral |
| Entrega post-cierre | API (server_account) | Usuario solo sube archivos |
| Finalizar | Usuario (MetaMask) | 1 transaccion |
| Reclamar reembolso | Usuario (MetaMask) | 1 transaccion |

Las operaciones que paga la API son las que no requieren autenticacion fuerte (anonimas). Las que requieren identidad del usuario van por MetaMask.

---

## Por que el admin no puede registrar nombres ENS ni crear llamados

El admin es el owner del contrato CFPFactory. Su unica funcion es autorizar/desautorizar creadores. No deberia participar como creador ni como proponente para mantener la separacion de roles. El frontend bloquea al admin en:
- Registro ENS (Pestana ENS)
- Registro on-chain/off-chain (Pestana Creador)
- Creacion de llamados (Pestana Creador)

Cualquier cuenta de MetaMask, excepto la del admin, puede seguir el flujo completo de creador.
