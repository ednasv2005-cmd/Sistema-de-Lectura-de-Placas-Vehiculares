"""Pestaña principal (RF-07): video, última lectura, KPIs y últimos eventos."""
from pathlib import Path

import numpy as np
import pandas as pd
import panel as pn

from lpr import config
from lpr.ui.contexto import Contexto
from lpr.ui.estilos import FORMATOS, ROJO, VERDE, colorear, formatear, tarjeta_html


class VistaMonitoreo:
    titulo = "🎥 Monitoreo"

    def __init__(self, ctx: Contexto):
        self.ctx = ctx
        self._ver = self._id = self._jpg = None

        kw = dict(font_size="26pt", title_size="10pt")
        self.k_total = pn.indicators.Number(name="Eventos hoy", value=0, **kw)
        self.k_aut = pn.indicators.Number(name="Autorizados", value=0, default_color=VERDE, **kw)
        self.k_no = pn.indicators.Number(name="No autorizados", value=0, default_color=ROJO, **kw)
        self.k_lat = pn.indicators.Number(name="Latencia media", value=0, format="{value:.0f} ms",
                                          colors=[(config.META_LATENCIA_MS, VERDE), (1e12, ROJO)], **kw)
        self.k_fps = pn.indicators.Number(name="FPS proceso", value=0, format="{value:.1f}", **kw)

        self.video = pn.pane.JPG(None, sizing_mode="stretch_width", min_height=360)
        self.sin_senal = pn.pane.Alert("📷 Cámara sin señal — reconectando automáticamente…",
                                       alert_type="danger", visible=False)
        self.tarjeta = pn.pane.HTML(tarjeta_html(None, ctx.proc.umbral_ocr), sizing_mode="stretch_width")
        self.recorte = pn.pane.JPG(None, height=110)
        self.correccion = pn.widgets.TextInput(placeholder="Placa correcta", width=170)
        self.b_corregir = pn.widgets.Button(name="Corregir y re-verificar", button_type="warning")
        self.b_corregir.on_click(self._corregir)

        self.recientes = pn.widgets.Tabulator(
            pd.DataFrame(), disabled=True, show_index=False, height=320, sizing_mode="stretch_width",
            formatters=FORMATOS, hidden_columns=["id", "propietario", "camara", "corregido_por", "imagen"])
        self.recientes.style.apply(colorear, axis=1)

        self.layout = pn.Column(
            pn.Row(self.k_total, self.k_aut, self.k_no, self.k_lat, self.k_fps),
            pn.Row(pn.Column(self.sin_senal, self.video, sizing_mode="stretch_width"),
                   pn.Column("#### Última lectura", self.tarjeta, self.recorte,
                             pn.Row(self.correccion, self.b_corregir), width=440)),
            "#### Últimos eventos", self.recientes, sizing_mode="stretch_width")

    def _corregir(self, _):
        ult = self.ctx.proc.ultima
        if self.ctx.corregir_evento(ult.id if ult else None, self.correccion.value):
            self.correccion.value = ""

    def actualizar_rapido(self):  # ~200 ms
        proc = self.ctx.proc
        if proc.jpg is not self._jpg:
            self._jpg = self.video.object = proc.jpg
        self.sin_senal.visible = not self.ctx.cam.ok

    def actualizar(self):  # ~1 s
        db, proc, notif = self.ctx.db, self.ctx.proc, self.ctx.notif
        if proc.version != self._ver:
            l = proc.ultima
            nuevo = self._ver is not None and l is not None and l.id != self._id
            self._ver, self._id = proc.version, (l.id if l else None)
            self.tarjeta.object = tarjeta_html(l, proc.umbral_ocr)
            self.recorte.object = l.recorte if l and Path(l.recorte).exists() else None
            self.recientes.value = formatear(db.eventos(limite=12))
            if nuevo:
                if l.resultado != "AUTORIZADO":
                    notif.error(f"✖ {l.placa}: NO AUTORIZADO", duration=8000)
                if l.conf_ocr < proc.umbral_ocr:
                    notif.warning(f"⚠ {l.placa}: confianza OCR {l.conf_ocr:.0%}, revisar imagen", duration=8000)
        self.k_total.value, self.k_aut.value, self.k_no.value = db.resumen_hoy()
        self.k_lat.value = float(np.mean(proc.latencias)) if proc.latencias else 0.0
        self.k_fps.value = round(proc.fps, 1)
