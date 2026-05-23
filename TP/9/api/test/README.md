# test/ — Artefactos de prueba

Este directorio contiene artefactos auxiliares usados exclusivamente por `test_apiserver.py`. **No forman parte del sistema desplegado en la cadena.**

## Contenido

| Archivo               | Descripción                                                    |
|-----------------------|----------------------------------------------------------------|
| `MerkleVerifier.sol`  | Fuente del contrato auxiliar de prueba                         |
| `MerkleVerifier.json` | ABI y bytecode precompilados, leídos directamente por el test  |

## Por qué existe este directorio

`test_apiserver.py` incluye un test (`test_verify_proposal_proofs_onchain`) que verifica on-chain las pruebas de Merkle devueltas por la API. Para eso despliega `MerkleVerifier`, un contrato mínimo que expone `MerkleProof.verify` de OpenZeppelin.

El contrato vive aquí — y no en `contracts/contracts/` — para dejar en claro que es un auxiliar de test, no un contrato de producción. El test lee el ABI y el bytecode de `MerkleVerifier.json` en lugar de depender del artefacto generado por Hardhat, lo que elimina la dependencia del ciclo de compilación de `contracts/`.

## Integridad del artefacto

`test_apiserver.py` verifica al momento de ejecutarse que el SHA-256 de `MerkleVerifier.sol` coincida con el valor esperado. Si no coincide, el test falla con un mensaje explícito antes de intentar desplegar nada.

### Si necesita modificar `MerkleVerifier.sol`

El contrato importa de `@openzeppelin/contracts`, por lo que la compilación
debe hacerse desde el directorio `contracts/`, donde se encuentran esas
dependencias. Los pasos son:

1. Edite `api/test/MerkleVerifier.sol`.
2. Copie el `.sol` al directorio de contratos, compile y traiga el artefacto
   de vuelta (desde la raíz de este práctico):

   ```bash
   cp api/test/MerkleVerifier.sol TP/9/contracts/contracts/
   cd contracts && npx hardhat compile
   cd ..
   python3 - <<'EOF'
   import json
   src = "contracts/artifacts/contracts/MerkleVerifier.sol/MerkleVerifier.json"
   dst = "api/test/MerkleVerifier.json"
   d = json.load(open(src))
   json.dump({"abi": d["abi"], "bytecode": d["bytecode"]}, open(dst, "w"), indent=2)
   print("Artefacto actualizado.")
   EOF
   rm contracts/contracts/MerkleVerifier.sol
   ```

3. Recalcule el SHA-256 del `.sol`:

   ```bash
   python3 -c "import hashlib; print(hashlib.sha256(open('TP/9/api/test/MerkleVerifier.sol','rb').read()).hexdigest())"
   ```

4. Actualice la constante `MERKLE_VERIFIER_SHA256` en `test_apiserver.py`.
