"""
Genera un padrón SINTÉTICO de vehículos (nombres y placas ficticios) para pruebas y demos.

Uso (desde la raíz del proyecto, con el venv activo):
    python scripts/generar_padron.py                         # 50 registros -> data/padron_sintetico.csv
    python scripts/generar_padron.py -n 200 --db             # además los inserta en la BD
    python scripts/generar_padron.py --incluir ABC123D XYZ987A --db   # agrega tus placas reales de prueba
    python scripts/generar_padron.py --semilla 7             # otro conjunto reproducible
"""
from __future__ import annotations

import argparse
import csv
import random
import string
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))  # permite importar el paquete lpr

from lpr import config                       # noqa: E402
from lpr.core.utils import normalizar, placa_valida  # noqa: E402

NOMBRES = [
    "José", "María", "Juan", "Guadalupe", "Luis", "Ana", "Carlos", "Fernanda", "Jorge", "Sofía",
    "Miguel", "Daniela", "Ricardo", "Valeria", "Alejandro", "Mariana", "Fernando", "Gabriela",
    "Eduardo", "Paola", "Roberto", "Andrea", "Arturo", "Claudia", "Héctor", "Patricia", "Raúl",
    "Verónica", "Sergio", "Ximena", "Diego", "Alejandra", "Óscar", "Lucía", "Iván", "Regina",
]
APELLIDOS = [
    "Hernández", "García", "Martínez", "López", "González", "Pérez", "Rodríguez", "Sánchez",
    "Ramírez", "Cruz", "Flores", "Gómez", "Morales", "Vázquez", "Reyes", "Jiménez", "Torres",
    "Díaz", "Gutiérrez", "Ruiz", "Mendoza", "Aguilar", "Ortiz", "Moreno", "Castillo", "Romero",
    "Álvarez", "Méndez", "Chávez", "Rivera", "Juárez", "Ramos", "Domínguez", "Herrera", "Medina",
]
VEHICULOS = {
    "Nissan": ["Versa", "Sentra", "March", "Kicks", "NP300"],
    "Volkswagen": ["Jetta", "Vento", "Virtus", "Taos", "Tiguan"],
    "Chevrolet": ["Aveo", "Onix", "Beat", "Tracker", "S10"],
    "Toyota": ["Corolla", "Yaris", "RAV4", "Hilux", "Camry"],
    "Honda": ["Civic", "City", "CR-V", "HR-V"],
    "Mazda": ["Mazda 2", "Mazda 3", "CX-3", "CX-5"],
    "Kia": ["Rio", "Forte", "Seltos", "Sportage"],
    "Hyundai": ["Grand i10", "Accent", "Creta", "Tucson"],
    "Ford": ["Figo", "Escape", "Ranger", "Territory"],
    "MG": ["MG5", "ZS", "HS"],
}
COLORES = ["Blanco", "Gris", "Plata", "Negro", "Rojo", "Azul", "Arena", "Vino"]
NOTAS = ["Residente", "Empleado", "Proveedor", "Visitante frecuente", "Directivo", "Mantenimiento"]

# Formatos frecuentes de placas particulares en México (sin guiones, como las normaliza el sistema)
# L = letra, D = dígito.  Ej.: ABC123D, 123ABC, ABC1234, AB1234C
FORMATOS = ["LLLDDDL", "DDDLLL", "LLLDDDD", "LLDDDDL"]
LETRAS = "ABCDEFGHJKLMNPRSTUVWXYZ"  # sin I, O, Q para evitar confusión con 1 y 0


def generar_placa(rng: random.Random) -> str:
    fmt = rng.choice(FORMATOS)
    return "".join(rng.choice(LETRAS) if c == "L" else rng.choice(string.digits) for c in fmt)


def generar_nombre(rng: random.Random) -> str:
    nombre = rng.choice(NOMBRES)
    if rng.random() < 0.3:  # 30 % con segundo nombre
        nombre += " " + rng.choice([n for n in NOMBRES if n != nombre])
    return f"{nombre} {rng.choice(APELLIDOS)} {rng.choice(APELLIDOS)}"


def generar_vehiculo(rng: random.Random) -> str:
    marca = rng.choice(list(VEHICULOS))
    return f"{marca} {rng.choice(VEHICULOS[marca])} {rng.randint(2012, 2026)} {rng.choice(COLORES)}"


def generar_registros(n: int, semilla: int, incluir: list[str], pct_vencidos: float) -> list[dict]:
    rng = random.Random(semilla)
    placas: set[str] = set()
    registros = []

    # 1) Placas reales de prueba (las que usarás en la demo): siempre vigentes
    for p in incluir:
        p = normalizar(p)
        if not placa_valida(p):
            print(f"[aviso] placa ignorada por formato inválido: {p}")
            continue
        placas.add(p)
        registros.append({"placa": p, "propietario": generar_nombre(rng), "vehiculo": generar_vehiculo(rng),
                          "vigente": 1, "notas": "SINTÉTICO · placa de demo"})

    # 2) Placas aleatorias únicas
    while len(registros) < n + len(incluir):
        p = generar_placa(rng)
        if p in placas or not placa_valida(p):
            continue
        placas.add(p)
        vigente = 0 if rng.random() < pct_vencidos else 1
        registros.append({"placa": p, "propietario": generar_nombre(rng), "vehiculo": generar_vehiculo(rng),
                          "vigente": vigente, "notas": f"SINTÉTICO · {rng.choice(NOTAS)}"})
    return registros


def guardar_csv(registros: list[dict], ruta: Path):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: acentos bien en Excel
        w = csv.DictWriter(f, fieldnames=["placa", "propietario", "vehiculo", "vigente", "notas"])
        w.writeheader()
        w.writerows(registros)


def guardar_db(registros: list[dict]):
    from lpr.datos.base_datos import BaseDatos  # misma lógica que usa la interfaz
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = BaseDatos(config.DB_PATH)
    for r in registros:
        db.guardar_vehiculo(r["placa"], r["propietario"], r["vehiculo"], bool(r["vigente"]), r["notas"])


def main():
    ap = argparse.ArgumentParser(description="Genera un padrón sintético para el sistema LPR.")
    ap.add_argument("-n", type=int, default=50, help="número de registros aleatorios (default 50)")
    ap.add_argument("--semilla", type=int, default=42, help="semilla para resultados reproducibles")
    ap.add_argument("--incluir", nargs="*", default=[], help="placas reales de prueba a incluir como vigentes")
    ap.add_argument("--vencidos", type=float, default=0.15, help="proporción de registros no vigentes (0-1)")
    ap.add_argument("--csv", type=Path, default=RAIZ / "data" / "padron_sintetico.csv", help="ruta del CSV")
    ap.add_argument("--db", action="store_true", help="insertar también en la base de datos del sistema")
    args = ap.parse_args()

    registros = generar_registros(args.n, args.semilla, args.incluir, args.vencidos)
    guardar_csv(registros, args.csv)
    print(f"✔ CSV: {args.csv}  ({len(registros)} registros)")

    if args.db:
        guardar_db(registros)
        print(f"✔ Insertados en la BD: {config.DB_PATH}")

    vig = sum(r["vigente"] for r in registros)
    print(f"  Vigentes: {vig}   No vigentes: {len(registros) - vig}")


if __name__ == "__main__":
    main()
