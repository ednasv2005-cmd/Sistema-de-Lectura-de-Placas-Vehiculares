"""Barra lateral: consulta rápida, prueba con imagen y configuración (admin)."""
import cv2
import numpy as np
import panel as pn

from lpr.core.utils import a_jpg, normalizar
from lpr.ui.contexto import Contexto
from lpr.ui.estilos import badge_verificacion


def construir_sidebar(ctx: Contexto) -> list:
    db, cam, proc, notif = ctx.db, ctx.cam, ctx.proc, ctx.notif

    # Consulta rápida contra el padrón
    v_placa = pn.widgets.TextInput(name="Consultar placa en padrón", placeholder="ABC123D")
    v_res = pn.pane.HTML()

    def consultar(_=None):
        p = normalizar(v_placa.value)
        v_res.object = badge_verificacion(p, *db.verificar(p)) if p else ""

    v_placa.param.watch(consultar, "value")

    # Prueba con imagen
    subir = pn.widgets.FileInput(accept=".jpg,.jpeg,.png,.bmp")
    prueba_img = pn.pane.JPG(None, sizing_mode="stretch_width")

    def probar(e):
        if not e.new:
            return
        frame = cv2.imdecode(np.frombuffer(e.new, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            notif.error("Archivo de imagen no válido.")
            return
        vis, lecturas = proc.procesar(frame, "carga manual", deduplicar=False)
        prueba_img.object = a_jpg(vis, 600)
        if not lecturas:
            notif.warning("No se encontró una placa legible en la imagen.")

    subir.param.watch(probar, "value")

    items = ["### 🔎 Consulta rápida", v_placa, v_res, pn.layout.Divider(),
             "### 🧪 Probar con imagen", subir, prueba_img]

    if ctx.admin:
        s_fuente = pn.widgets.TextInput(name="Fuente de video", value=str(cam.fuente))
        b_fuente = pn.widgets.Button(name="Conectar", button_type="primary")
        s_det = pn.widgets.FloatSlider(name="Confianza mínima de detección", start=0.1, end=0.95,
                                       step=0.05, value=proc.conf_det)
        s_ocr = pn.widgets.FloatSlider(name="Umbral de confianza OCR (aviso)", start=0.1, end=0.99,
                                       step=0.05, value=proc.umbral_ocr)
        s_cool = pn.widgets.IntSlider(name="Ventana anti-duplicados (s)", start=3, end=120, value=proc.cooldown)
        t_pausa = pn.widgets.Toggle(name="⏸ Pausar procesamiento", value=proc.pausado)

        b_fuente.on_click(lambda _: cam.cambiar(s_fuente.value.strip()))
        s_det.param.watch(lambda e: setattr(proc, "conf_det", e.new), "value")
        s_ocr.param.watch(lambda e: setattr(proc, "umbral_ocr", e.new), "value")
        s_cool.param.watch(lambda e: setattr(proc, "cooldown", e.new), "value")
        t_pausa.param.watch(lambda e: setattr(proc, "pausado", e.new), "value")

        items += [pn.layout.Divider(), "### ⚙ Configuración", s_fuente, b_fuente, s_det, s_ocr, s_cool, t_pausa]
    return items
