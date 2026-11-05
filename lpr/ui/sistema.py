"""Salud del sistema: RNF-01, RNF-04, RF-05 y métricas del modelo."""
import html
import time
from datetime import timedelta
from pathlib import Path

import numpy as np
import panel as pn
import psutil

from lpr import config
from lpr.core.utils import ocultar_credenciales
from lpr.ui.contexto import Contexto
from lpr.ui.estilos import ROJO, VERDE, metricas_modelo_html, tabla_html


class VistaSistema:
    titulo = "🖥 Sistema"

    def __init__(self, ctx: Contexto):
        self.ctx = ctx
        colores = [(0.7, VERDE), (0.85, "#f9a825"), (1, ROJO)]
        self.g_cpu = pn.indicators.Gauge(name="CPU (RNF-04 ≤ 70 %)", value=0, bounds=(0, 100),
                                         format="{value}%", colors=colores, height=280, width=300)
        self.g_ram = pn.indicators.Gauge(name="RAM proceso (≤ 4 GB)", value=0, bounds=(0, 4096),
                                         format="{value} MB", colors=colores, height=280, width=300)
        self.info = pn.pane.HTML()
        self.layout = pn.Column(
            pn.Row(self.g_cpu, self.g_ram, pn.Column("#### Estado del servicio", self.info)),
            pn.layout.Divider(), "#### Métricas del modelo de detección (conjunto de prueba)",
            pn.pane.HTML(metricas_modelo_html(ctx.proc.modelo_ruta)))

    def actualizar(self):
        cam, proc = self.ctx.cam, self.ctx.proc
        self.g_cpu.value = round(psutil.cpu_percent())
        self.g_ram.value = round(psutil.Process().memory_info().rss / 2**20)
        lat = list(proc.latencias)
        p95 = float(np.percentile(lat, 95)) if lat else 0.0
        self.info.object = tabla_html([
            ("Fuente", html.escape(ocultar_credenciales(cam.fuente))),
            ("Cámara", "🟢 En línea" if cam.ok else "🔴 Sin señal"),
            ("Reconexiones automáticas", cam.reconexiones),
            ("Tiempo activo", str(timedelta(seconds=int(time.time() - proc.inicio)))),
            ("Latencia p95 (RF-05 < 2 s)", f"{p95:.0f} ms " + ("✔" if p95 < config.META_LATENCIA_MS else "✖")),
            ("Modelo", html.escape(Path(proc.modelo_ruta).name)),
            ("OCR", proc.ocr.nombre if proc.ocr.disponible else "⚠ no disponible"),
            ("Procesamiento", "⏸ En pausa" if proc.pausado else "▶ Activo"),
        ])
