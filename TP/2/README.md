# Trabajo Práctico 2

* En [este documento](https://cripto.iua.edu.ar/blockchain/doc/) se describen un conjunto de desafíos criptográficos. Resuelva los siguientes:
  * [Generador de números pseudoaleatorios de Java](https://cripto.iua.edu.ar/blockchain/doc/javarand.html)
  * [DSA con reutilización de `k`](https://cripto.iua.edu.ar/blockchain/doc/dsa.html)
* Suba el código utilizado a la carpeta `TP/2` de su repositorio personal, tal como se describe en el [README](../README.md) del repositorio de la materia.
* Describa la tarea realizada en el archivo `README.md` de la carpeta `TP/2` de su repositorio personal.

---

# Desafíos Criptográficos — Blockchain e Ingeniería en Informática

Soluciones a los desafíos criptográficos de la materia de Blockchain y Contratos Inteligentes.

---

## Desafío 1 — `javarand_attack.py`

Predice el próximo número producido por el generador pseudoaleatorio de Java (`java.util.Random`), que implementa un Generador Congruencial Lineal (LCG).

**Idea del ataque:**  
El estado interno del generador es de 48 bits, pero cada número devuelto expone solo los 32 bits más significativos. Conociendo dos números consecutivos, se pueden probar los 65.536 valores posibles para los 16 bits ocultos del primer número (fuerza bruta) hasta encontrar el estado interno completo. Con ese estado, el siguiente número es calculable de forma determinista.

**Uso:**
```bash
pip install requests
python3 javarand_attack.py
```

---

## Desafío 2 — `dsa_repeated_k_attack.py`

Recupera la clave privada de un servidor DSA que reutiliza el valor secreto `k` al firmar distintos mensajes.

**Idea del ataque:**  
En DSA, el valor `r` de una firma depende únicamente de `k`. Si dos firmas comparten el mismo `r`, el servidor usó el mismo `k` dos veces. Esto permite plantear un sistema de dos ecuaciones con dos incógnitas (`k` y `x`) y resolverlo mediante aritmética modular, obteniendo la clave privada `x`.

```
k = (H(m1) - H(m2)) * (s1 - s2)⁻¹  mod q
x = r⁻¹ * (k*s1 - H(m1))            mod q
```

**Uso:**
```bash
pip install requests
python3 dsa_repeated_k_attack.py
```

---

## Requisitos

- Python 3.8 o superior
- Librería `requests`: `pip install requests`
- Email registrado en el servidor de la cátedra