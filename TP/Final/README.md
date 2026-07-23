# TP Final - Blockchain y Contratos Inteligentes

Sistema de gestion de llamados a presentacion de propuestas (CFP) con soporte
para ENS (Ethereum Name Service), token ERC-20 con garantia de oferta y
devolucion mediante mecanismo pull.

## Estructura del proyecto

```
TP/Final/
├── contracts/        # Smart contracts (Hardhat + Solidity 0.8.28)
├── api/              # API REST (Flask + Web3.py)
├── web/              # Interfaz web (Vue 3 + ethers.js v6)
└── docs/             # Documentacion de diseno
```

## Componentes

### contracts/

9 contratos Solidity: ENSRegistry, FIFSRegistrar, PublicResolver,
ReverseRegistrar, CFPGovernanceToken, CFPFactory, CFP, y utilidades.

Despliegue completo via `npm run deploy`. Ver `contracts/README.md`.

### api/

Servidor Flask con endpoints para registro de creadores, creacion de llamados,
presentacion de propuestas, resolucion ENS, consulta de tokens y gestion de
garantias. Ver `api/README.md`.

### web/

Frontend Vue 3 con paneles para cada rol: publico (ver llamados), creador
(registro, crear llamado, finalizar), proponente (presentar propuesta, reclamar
reembolso), admin (autorizar creadores), ENS, y Token. Ver `web/README.md`.

## Arquitectura

```
MetaMask                Hardhat node (localhost:8545)
   |                           |
   |  ethers.js                |  Web3.py
   |                           |
   v                           v
  Web (Vue 3:5173)  --->  API (Flask:5000)  --->  Contratos (Solidity)
   |                           |
   |  POST /api/*              |  Event listener
   v                           v
  Navegador                 SQLite (cfp.db)
```

## Arbol ENS

```
cfp                     ← deployer (owner del CFPFactory)
├── usuarios.cfp        ← FIFSRegistrar (autoregistro de usuarios)
│   └── <nombre>.usuarios.cfp  ← registrado por el usuario via MetaMask
├── llamados.cfp        ← deployer (la API registra nombres de llamados)
│   └── <nombre>.llamados.cfp  ← registrado por la API al crear el llamado
└── addr.reverse        ← ReverseRegistrar
    └── <addr>.addr.reverse    ← configurado por el usuario via setName()
```

## Puesta en marcha (Quickstart)

### 1. Nodo blockchain

```bash
cd TP/Final/contracts
npx hardhat node
```

### 2. Desplegar contratos (otra terminal)

```bash
cd TP/Final/contracts
npm run deploy
```

Al finalizar imprime las variables de entorno necesarias. **Copialas** para el paso siguiente.

### 3. API (otra terminal)

```bash
cd TP/Final/api
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export CFP_MNEMONIC="la frase que imprime el deploy"
export CFP_FACTORY_ADDRESS="0x..."
export CFP_ADMIN_ADDRESS="0x..."
export CFP_ENS_REGISTRY="0x..."
export CFP_ERC20_TOKEN="0x..."

python3 apiserver.py
```

### 4. Frontend (otra terminal)

```bash
cd TP/Final/web
npm install
npm run dev
```

Abrir `http://localhost:5173`.

### 5. MetaMask

1. Agregar red: `http://127.0.0.1:8545` (chainId `31337`)
2. Importar cuenta con la mnemonic que imprime el deploy (o usar una de las cuentas prefinanciadas)
3. Conectar la wallet en la web

## Ejecutar tests

```bash
# Contratos
cd TP/Final/contracts && npm test

# API (entorno separado)
cd TP/Final/api
python3 -m venv venv-test
source venv-test/bin/activate
pip install -r pytest-requirements.txt
pytest test_apiserver.py -v

# Web
cd TP/Final/web && npx vitest run
```

## Requisitos del sistema

- Python 3
- Node.js >= 18
- npm
- MetaMask (navegador)

## Resumen de funcionalidades

| Funcionalidad | Estado |
|---------------|--------|
| ENS: registro, resolucion directa e inversa | Implementado |
| ENS: unicidad en usuarios.cfp y llamados.cfp | Implementado |
| Token ERC-20: compra y redencion contra ETH | Implementado |
| Garantia de oferta: deposito via approve/transferFrom | Implementado |
| Finalizacion y reembolso pull | Implementado |
| UI con nombres ENS en lugar de direcciones | Parcial |
| Tests automatizados para nuevas funcionalidades | Pendiente |

## Puesta en marcha

Ver `docs/FLUJO_DE_PRUEBA.md` para instrucciones paso a paso.

## Documentacion de diseno

| Documento | Descripcion |
|-----------|-------------|
| `docs/ANALISIS_CONSIGNA.md` | Desglose de requisitos |
| `docs/DECISIONES_DISENO.md` | 13 decisiones con justificacion |
| `docs/PATRONES_EJEMPLOS.md` | Patrones de ejemplos del profesor |
| `docs/FLUJO_DE_PRUEBA.md` | Flujo de prueba completo |
