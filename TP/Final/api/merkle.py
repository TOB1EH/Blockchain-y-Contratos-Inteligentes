"""
Implementación del árbol de Merkle compatible con OpenZeppelin MerkleProof.

Convenciones:
- Las hojas se ordenan lexicográficamente antes de construir el árbol.
- Cada nodo interno es keccak256(min(a,b) ++ max(a,b)).
- Si el número de hojas es impar, la última hoja sube sin combinarse (promoción).
"""

from web3 import Web3

def _hash_pair(a: bytes, b: bytes) -> bytes:
    """Hash de dos nodos: siempre el menor primero para que sea conmutativo."""
    if a <= b:
        return bytes(Web3.keccak(a + b))
    return bytes(Web3.keccak(b + a))


def _build_tree(sorted_leaves: list[bytes]) -> list[bytes]:
    """
    Construye el árbol como un array plano.
    Índice 0 = raíz.
    Las hojas ocupan las últimas n posiciones en orden inverso al lexicográfico.
    """
    n = len(sorted_leaves)
    tree = [None] * (2 * n - 1)

    # Colocar las hojas al final del array en orden inverso
    for i in range(n):
        tree[2 * n - 2 - i] = sorted_leaves[i]

    # Calcular los nodos internos de atrás hacia adelante
    for i in range(n - 2, -1, -1):
        left  = tree[2 * i + 1]
        right = tree[2 * i + 2]
        tree[i] = _hash_pair(left, right)

    return tree


def build_merkle_tree(leaves: list[bytes]) -> tuple[bytes, dict[str, list[str]]]:
    """
    Dado una lista de hojas (bytes de 32 bytes cada una), construye el árbol
    de Merkle compatible con OpenZeppelin y devuelve:
      - la raíz como bytes
      - el diccionario proof: {"0x<hoja>": ["0x<hermano1>", ...], ...}

    Las hojas se ordenan lexicográficamente internamente.
    """
    if not leaves:
        raise ValueError("El árbol de Merkle requiere al menos una hoja")

    # Caso especial: árbol de una sola hoja
    if len(leaves) == 1:
        root = leaves[0]
        proof = {"0x" + leaves[0].hex(): []}
        return root, proof

    # Ordenar las hojas y construir el árbol
    sorted_leaves = sorted(leaves)
    tree = _build_tree(sorted_leaves)
    n = len(sorted_leaves)

    # Construir las pruebas para cada hoja original (no las ordenadas)
    proofs = {}
    for leaf in leaves:
        pos   = 2 * n - 2 - sorted_leaves.index(leaf)
        path  = []
        p     = pos
        while p > 0:
            # El hermano está a la derecha si soy impar, a la izquierda si soy par
            sibling = p + 1 if p % 2 == 1 else p - 1
            path.append("0x" + tree[sibling].hex())
            p = (p - 1) // 2
        proofs["0x" + leaf.hex()] = path

    return tree[0], proofs


def compute_proposal_id(
    call_id: str, title: str, description: str, file_hashes: list[str]
) -> str:
    """
    Calcula el identificador de propuesta (raíz del árbol de Merkle).

    Las hojas son:
      - call_id (ya es un hash de 32 bytes, se usa directamente)
      - keccak256(title en UTF-8)
      - keccak256(description en UTF-8)
      - cada elemento de file_hashes (ya son hashes de 32 bytes)

    Devuelve el proposalId como "0x..." en minúsculas.
    """

    # Convertir las entradas a bytes de 32 bytes cada una para construir el árbol
    call_leaf   = bytes.fromhex(call_id[2:])
    title_leaf  = bytes(Web3.keccak(text=title))
    desc_leaf   = bytes(Web3.keccak(text=description))
    file_leaves = [bytes.fromhex(h[2:]) for h in file_hashes]

    # Construir el árbol para obtener la raíz
    all_leaves = [call_leaf, title_leaf, desc_leaf] + file_leaves
    root, _ = build_merkle_tree(all_leaves)
    return "0x" + root.hex()


def compute_proposal_proofs(
    call_id: str, title: str, description: str, file_hashes: list[str]
) -> dict[str, list[str]]:
    """
    Construye el árbol y devuelve el diccionario completo de pruebas:
    {
      "0x<callId>":            [...],
      "0x<keccak(title)>":     [...],
      "0x<keccak(desc)>":      [...],
      "0x<fileHash1>":         [...],
      ...
    }
    Las claves son las hojas originales en minúsculas con prefijo 0x.
    """

    # Convertir las entradas a bytes de 32 bytes cada una para construir el árbol
    call_leaf   = bytes.fromhex(call_id[2:])
    title_leaf  = bytes(Web3.keccak(text=title))
    desc_leaf   = bytes(Web3.keccak(text=description))
    file_leaves = [bytes.fromhex(h[2:]) for h in file_hashes]

    # Construir el árbol para obtener las pruebas de cada hoja original (antes de ordenar)
    all_leaves = [call_leaf, title_leaf, desc_leaf] + file_leaves
    _, proofs = build_merkle_tree(all_leaves)
    return proofs


def verify_proof(proof: list[str], root: str, leaf_hex: str) -> bool:
    """
    Verifica que una hoja pertenece al árbol con la raíz dada.
    Compatible con MerkleProof.verify de OpenZeppelin.
    """

    # Recrear el hash de la hoja a partir del valor hexadecimal
    current = bytes.fromhex(leaf_hex[2:])
    for sibling in proof:
        current = _hash_pair(current, bytes.fromhex(sibling[2:]))
    return "0x" + current.hex() == root.lower()
