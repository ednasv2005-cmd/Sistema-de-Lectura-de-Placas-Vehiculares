"""Persistencia local: padrón (RF-04) y eventos (RF-06)."""
from __future__ import annotations

import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from lpr.core.utils import normalizar

ESQUEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS padron(
    placa TEXT PRIMARY KEY, propietario TEXT, vehiculo TEXT,
    vigente INTEGER NOT NULL DEFAULT 1, notas TEXT);
CREATE TABLE IF NOT EXISTS eventos(
    id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, placa TEXT NOT NULL,
    resultado TEXT NOT NULL, propietario TEXT, conf_ocr REAL, conf_det REAL,
    latencia_ms REAL, camara TEXT, imagen TEXT, recorte TEXT, corregido_por TEXT);
CREATE INDEX IF NOT EXISTS ix_eventos_placa ON eventos(placa);
CREATE INDEX IF NOT EXISTS ix_eventos_fecha ON eventos(fecha);
"""


class BaseDatos:
    CAMPOS_PADRON = {"propietario", "vehiculo", "vigente", "notas"}

    def __init__(self, ruta: Path):
        self.con = sqlite3.connect(ruta, check_same_thread=False)
        self.lock = threading.Lock()
        self.con.executescript(ESQUEMA)

    # ── internos ──
    def _ejecutar(self, sql, params=()):
        with self.lock:
            cur = self.con.execute(sql, params)
            self.con.commit()
            return cur

    def _df(self, sql, params=()) -> pd.DataFrame:
        with self.lock:
            return pd.read_sql_query(sql, self.con, params=params)

    # ── verificación (RF-04) ──
    def verificar(self, placa: str) -> tuple[str, str]:
        """En producción esta llamada va contra la API REST de verificación."""
        with self.lock:
            fila = self.con.execute(
                "SELECT propietario FROM padron WHERE placa=? AND vigente=1", (placa,)).fetchone()
        return ("AUTORIZADO", fila[0] or "") if fila else ("NO AUTORIZADO", "")

    # ── eventos (RF-06) ──
    def registrar(self, **ev) -> int:
        cols, marcas = ", ".join(ev), ", ".join("?" * len(ev))
        return self._ejecutar(f"INSERT INTO eventos({cols}) VALUES({marcas})", tuple(ev.values())).lastrowid

    def corregir(self, id_evento: int, placa: str, usuario: str) -> tuple[str, str]:
        resultado, prop = self.verificar(placa)
        self._ejecutar("UPDATE eventos SET placa=?, resultado=?, propietario=?, corregido_por=? WHERE id=?",
                       (placa, resultado, prop, usuario, id_evento))
        return resultado, prop

    def eventos(self, placa="", desde=None, hasta=None, resultado="Todos", limite=5000) -> pd.DataFrame:
        sql = ("SELECT id, fecha, placa, resultado, propietario, conf_ocr, latencia_ms, camara, "
               "corregido_por, imagen FROM eventos WHERE 1=1")
        p: list = []
        if placa:
            sql += " AND placa LIKE ?"; p.append(f"%{normalizar(placa)}%")
        if desde:
            sql += " AND fecha >= ?"; p.append(desde.isoformat())
        if hasta:
            sql += " AND fecha < ?"; p.append((hasta + timedelta(days=1)).isoformat())
        if resultado != "Todos":
            sql += " AND resultado = ?"; p.append(resultado)
        return self._df(sql + " ORDER BY id DESC LIMIT ?", p + [limite])

    def resumen_hoy(self) -> tuple[int, int, int]:
        with self.lock:
            return self.con.execute(
                "SELECT COUNT(*), COALESCE(SUM(resultado='AUTORIZADO'),0), "
                "COALESCE(SUM(resultado='NO AUTORIZADO'),0) FROM eventos WHERE fecha >= ?",
                (date.today().isoformat(),)).fetchone()

    # ── padrón ──
    def padron(self) -> pd.DataFrame:
        df = self._df("SELECT placa, propietario, vehiculo, vigente, notas FROM padron ORDER BY placa")
        df["vigente"] = df["vigente"].astype(bool)
        return df

    def guardar_vehiculo(self, placa, propietario="", vehiculo="", vigente=True, notas=""):
        self._ejecutar(
            "INSERT INTO padron VALUES(?,?,?,?,?) ON CONFLICT(placa) DO UPDATE SET "
            "propietario=excluded.propietario, vehiculo=excluded.vehiculo, "
            "vigente=excluded.vigente, notas=excluded.notas",
            (normalizar(placa), propietario, vehiculo, int(vigente), notas))

    def editar_vehiculo(self, placa, campo, valor):
        if campo in self.CAMPOS_PADRON:  # lista blanca: evita inyección por nombre de columna
            self._ejecutar(f"UPDATE padron SET {campo}=? WHERE placa=?",
                           (int(bool(valor)) if campo == "vigente" else valor, placa))

    def borrar_vehiculos(self, placas: list[str]):
        with self.lock:
            self.con.executemany("DELETE FROM padron WHERE placa=?", [(p,) for p in placas])
            self.con.commit()
