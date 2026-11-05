"""Estado de una sesión del navegador, compartido entre pestañas."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lpr.core.utils import normalizar, placa_valida
from lpr.datos.base_datos import BaseDatos
from lpr.vision.camara import Camara
from lpr.vision.procesador import Procesador


@dataclass
class Contexto:
    db: BaseDatos
    cam: Camara
    proc: Procesador
    usuario: str
    admin: bool
    notif: Any  # pn.state.notifications de la sesión

    def corregir_evento(self, id_ev: int | None, texto: str) -> bool:
        nueva = normalizar(texto)
        if id_ev is None or not placa_valida(nueva):
            self.notif.warning("Selecciona un evento y escribe una placa válida (5–8 caracteres).")
            return False
        res, prop = self.db.corregir(id_ev, nueva, self.usuario)
        self.proc.actualizar_ultima(id_ev, nueva, res, prop, self.usuario)
        self.notif.info(f"Evento #{id_ev} corregido → {nueva}: {res}")
        return True
