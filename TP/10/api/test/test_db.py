"""
Este script es para probar la funcionalidad de la base de datos. Se puede ejecutar
después de haber editado el archivo database.py para verificar que las funciones
de inserción, actualización y consulta funcionan correctamente.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database

database.init_db()
print("DB creada correctamente")

database.upsert_registration("0xABC123", "Test User", "pending")
reg = database.get_registration("0xABC123")
print(f"Registro: {dict(reg)}")

nonce = database.get_admin_nonce()
print(f"Nonce admin: {nonce}")
new_nonce = database.increment_admin_nonce()
print(f"Nonce después de incrementar: {new_nonce}")
