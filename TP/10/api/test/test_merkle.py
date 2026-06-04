"""Verifica que nuestra implementación coincide exactamente con la del test."""

from web3 import Web3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from merkle import compute_proposal_id, compute_proposal_proofs, verify_proof
from os import urandom

# Copiar exactamente las funciones del test para comparar
def _hash_pair_test(a, b):
    if a <= b:
        return bytes(Web3.keccak(a + b))
    return bytes(Web3.keccak(b + a))

def compute_proposal_id_test(call_id, title, description, file_hashes):
    """
    Computa el ID de una propuesta usando el mismo algoritmo que el test.
    """
    call_leaf   = bytes.fromhex(call_id[2:])
    title_leaf  = bytes(Web3.keccak(text=title))
    desc_leaf   = bytes(Web3.keccak(text=description))
    file_leaves = [bytes.fromhex(h[2:]) for h in file_hashes]
    leaves = sorted([call_leaf, title_leaf, desc_leaf] + file_leaves)
    def root(lvs):
        if len(lvs) == 1:
            return lvs[0]
        tree = [None] * (2 * len(lvs) - 1)
        n = len(lvs)
        for i in range(n):
            tree[2 * n - 2 - i] = lvs[i]
        for i in range(n - 2, -1, -1):
            tree[i] = _hash_pair_test(tree[2*i+1], tree[2*i+2])
        return tree[0]
    return "0x" + root(leaves).hex()


call_id = "0x" + urandom(32).hex()
title = "Título de prueba"
description = "Descripción de prueba"
files = ["0x" + urandom(32).hex(), "0x" + urandom(32).hex()]

# Comparar raíces
mi_root    = compute_proposal_id(call_id, title, description, files)
test_root  = compute_proposal_id_test(call_id, title, description, files)

print(f"Mi raíz:   {mi_root}")
print(f"Test raíz: {test_root}")
assert mi_root == test_root, "¡Las raíces no coinciden!"
print("✓ Las raíces coinciden")

# Verificar pruebas
proofs = compute_proposal_proofs(call_id, title, description, files)
for leaf_hex, siblings in proofs.items():
    assert verify_proof(siblings, mi_root, leaf_hex), f"Prueba inválida para {leaf_hex}"
print(f"✓ Todas las pruebas son válidas ({len(proofs)} hojas)")

# Prueba vacía (solo 3 hojas: callId, title, desc)
call_id2 = "0x" + urandom(32).hex()
root2 = compute_proposal_id(call_id2, "t", "d", [])
proofs2 = compute_proposal_proofs(call_id2, "t", "d", [])
assert len(proofs2) == 3, f"Esperaba 3 hojas, obtuve {len(proofs2)}"
for leaf_hex, siblings in proofs2.items():
    assert verify_proof(siblings, root2, leaf_hex)
print("✓ Árbol de 3 hojas (sin archivos) correcto")

# Prueba con 1 archivo (4 hojas)
root4 = compute_proposal_id(call_id, title, description, [files[0]])
proofs4 = compute_proposal_proofs(call_id, title, description, [files[0]])
assert len(proofs4) == 4
for leaf_hex, siblings in proofs4.items():
    assert verify_proof(siblings, root4, leaf_hex)
print("✓ Árbol de 4 hojas correcto")

print("\n✓ Todas las verificaciones pasaron")
