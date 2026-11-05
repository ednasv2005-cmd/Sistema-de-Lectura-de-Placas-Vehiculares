"""Historial (RF-06): consultas por placa, fecha o resultado, evidencia y corrección."""
import io
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import panel as pn

from lpr.ui.contexto import Contexto
from lpr.ui.estilos import FORMATOS, colorear, formatear


class VistaHistorial:
    titulo = "📋 Historial"

    def __init__(self, ctx: Contexto):
        self.ctx = ctx
        self._sel: int | None = None

        self.f_placa = pn.widgets.TextInput(name="Placa", placeholder="Ej. ABC123D")
        self.f_fechas = pn.widgets.DateRangePicker(name="Rango de fechas",
                                                   value=(date.today() - timedelta(days=7), date.today()))
        self.f_res = pn.widgets.Select(name="Resultado", options=["Todos", "AUTORIZADO", "NO AUTORIZADO"])
        b_buscar = pn.widgets.Button(name="🔍 Buscar", button_type="primary", align="end")
        descarga = pn.widgets.FileDownload(callback=self._exportar, filename="historial_lpr.csv",
                                           label="⬇ Exportar CSV", button_type="success", align="end")

        self.tabla = pn.widgets.Tabulator(pd.DataFrame(), pagination="remote", page_size=15, disabled=True,
                                          selectable=1, show_index=False, sizing_mode="stretch_width",
                                          hidden_columns=["imagen"], formatters=FORMATOS)
        self.tabla.style.apply(colorear, axis=1)

        self.det_info = pn.pane.Markdown("Selecciona un evento para ver la evidencia.")
        self.det_img = pn.pane.JPG(None, sizing_mode="stretch_width")
        self.det_corr = pn.widgets.TextInput(placeholder="Placa correcta", width=170)
        det_b = pn.widgets.Button(name="Corregir", button_type="warning")

        b_buscar.on_click(self.buscar)
        self.f_placa.param.watch(self.buscar, "value")
        self.tabla.param.watch(self._seleccionar, "selection")
        det_b.on_click(self._corregir)

        self.layout = pn.Column(
            pn.Row(self.f_placa, self.f_fechas, self.f_res, b_buscar, descarga),
            pn.Row(self.tabla, pn.Column(self.det_info, self.det_img,
                                         pn.Row(self.det_corr, det_b), width=440)),
            sizing_mode="stretch_width")
        self.buscar()

    def buscar(self, _=None):
        desde, hasta = self.f_fechas.value or (None, None)
        self.tabla.value = formatear(self.ctx.db.eventos(self.f_placa.value, desde, hasta, self.f_res.value))
        self.tabla.selection = []

    def _seleccionar(self, e):
        if not e.new:
            return
        fila = self.tabla.value.iloc[e.new[0]]
        self._sel = int(fila["id"])
        ruta = fila["imagen"]
        self.det_img.object = ruta if ruta and Path(ruta).exists() else None
        self.det_info.object = (f"**#{fila['id']}** · {fila['fecha']} · **{fila['placa']}** · "
                                f"{fila['resultado']} · OCR {(fila['conf_ocr'] or 0):.0%} · {fila['camara']}")

    def _corregir(self, _):
        if self.ctx.corregir_evento(self._sel, self.det_corr.value):
            self.det_corr.value = ""
            self.buscar()

    def _exportar(self):
        df = self.tabla.value.drop(columns=["imagen"], errors="ignore")
        return io.BytesIO(df.to_csv(index=False).encode("utf-8-sig"))
