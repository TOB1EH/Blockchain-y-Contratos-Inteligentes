# Documentacion del TP Final

Indice de documentacion del Trabajo Practico Final de Blockchain y Contratos Inteligentes.

## Documentos

| Documento | Descripcion |
|-----------|-------------|
| [`ANALISIS_CONSIGNA.md`](ANALISIS_CONSIGNA.md) | Analisis detallado de la consigna del TP Final, requisitos y desglose de cada componente |
| [`PATRONES_EJEMPLOS.md`](PATRONES_EJEMPLOS.md) | Patrones extraidos de los ejemplos del profesor (ENS, ERC-20, Bank, BuggyBank, ERC-721) |
| [`DECISIONES_DISENO.md`](DECISIONES_DISENO.md) | Decisiones de diseño con justificacion tecnica para cada una |

## Estructura del proyecto

```
TP/Final/
  contracts/    # Smart contracts (Hardhat + Solidity 0.8.28)
  api/          # API REST (Flask + Web3.py)
  web/          # Interfaz web (Vue 3 + ethers.js v6)
```

## Stack tecnologico

| Componente | Tecnologia | Version |
|------------|-----------|---------|
| Contratos | Solidity + Hardhat | ^0.8.28 / ^3.0.0 |
| API | Flask + Web3.py | 3.1.3 / 7.x |
| Frontend | Vue 3 + Vite + ethers.js | 3.5 / 8.x / 6.x |
| Testing | Hardhat Mocha + Chai + Pytest | Hardhat v3 / Pytest 9.x |
| OpenZeppelin | Contratos ERC-20 y Ownable | ^5.3.0 |
| Base de datos | SQLite | - |
