# AGENTS.md

## Directivas operativas

**Idioma**: Todas las respuestas al usuario deben ser en espanol. El razonamiento interno puede quedar en ingles.

**Formato**: No usar emojis. Texto limpio.

---

## Estructura del repositorio

Materia "Blockchain y Contratos Inteligentes". El directorio `TP/` contiene los trabajos practicos. `ejemplos/` contiene ejemplos del profesor.

## TP Final (rama tp-final)

El TP Final esta en `TP/Final/` con tres componentes:

```
TP/Final/
  contracts/    # Hardhat + Solidity 0.8.28
  api/          # Flask + Web3.py
  web/          # Vue 3 + ethers.js v6
docs/           # Documentacion de decisiones de diseno
```

### Setup contratos

```bash
cd TP/Final/contracts
npm install
npm run deploy  # Despliega: ENS + Token + CFPFactory
npm test        # Hardhat test (Mocha + Chai)
```

### Setup API

```bash
cd TP/Final/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Terminal 1: servidor
export CFP_MNEMONIC="..."
export CFP_FACTORY_ADDRESS="0x..."
export CFP_ADMIN_ADDRESS="0x..."
export CFP_ENS_REGISTRY="0x..."
export CFP_ERC20_TOKEN="0x..."
python3 apiserver.py

# Terminal 2: tests (entorno separado)
python3 -m venv venv-test
source venv-test/bin/activate
pip install -r pytest-requirements.txt
pytest test_apiserver.py -v
```

### Setup web

```bash
cd TP/Final/web
npm install
npm run dev
```

### Nuevos contratos (vs TP/10)

| Contrato | Proposito |
|----------|-----------|
| `ENSRegistry.sol` | Registro central ENS (EIP-137) |
| `FIFSRegistrar.sol` | Registro de nombres bajo `usuarios.cfp` |
| `PublicResolver.sol` | Resolutor addr() + name() (EIP-137, EIP-165, EIP-181) |
| `ReverseRegistrar.sol` | Resolucion inversa (addr.reverse) |
| `CFPGovernanceToken.sol` | Token ERC-20 con compra/redencion |

### Modificaciones a contratos existentes

| Contrato | Cambios |
|----------|---------|
| `CFP.sol` | Agregar `guaranteeAmount`, `registerProposalWithCollateral()`, `finalize()`, `claimRefund()` |
| `CFPFactory.sol` | Agregar `token` (immutable), `create()` con `guaranteeAmount` |

### Documentos de diseno

En `docs/`:
- `ANALISIS_CONSIGNA.md` - Desglose completo de requisitos
- `PATRONES_EJEMPLOS.md` - Patrones de los ejemplos del profesor
- `DECISIONES_DISENO.md` - Decisiones de diseno con justificacion

### Variables de entorno (adicionales a TP/10)

| Variable | Descripcion |
|----------|-------------|
| `CFP_ENS_REGISTRY` | Direccion del ENSRegistry desplegado |
| `CFP_ERC20_TOKEN` | Direccion del token ERC-20 desplegado |

### Orden de despliegue

1. ENSRegistry
2. PublicResolver (toma direccion del registry)
3. FIFSRegistrar para `usuarios.cfp`
4. ReverseRegistrar
5. Configurar arbol de nodos ENS (cfp, usuarios.cfp, llamados.cfp, addr.reverse)
6. CFPGovernanceToken
7. CFPFactory (toma direccion del token)

### Documentacion

Cada decision de diseno debe estar documentada en `docs/` con justificacion.
Cada componente debe tener su propio `README.md`.

## TPs anteriores (TP/1 a TP/10)

Ver rama `practicos` para los trabajos practicos previos.

## Restricciones importantes

1. No versionar: `node_modules/`, `venv/`, `venv-test/`, `__pycache__/`, `.pytest_cache/`, `artifacts/`, `cache/`, `dist/`, `*.db`, `uploads/`
2. Cada TP es autocontenido (sin imports entre directorios)
3. Asumir Python 3, node/npm, hardhat instalados
