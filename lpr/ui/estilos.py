"""Formatos y fragmentos HTML reutilizables."""
from __future__ import annotations

import html
import json
from pathlib import Path

import pandas as pd
from bokeh.models.widgets.tables import NumberFormatter

from lpr import config

VERDE, ROJO, PRIMARIO = "#1b8a3a", "#c62828", "#0d3b66"
FORMATOS = {"conf_ocr": NumberFormatter(format="0%"), "latencia_ms": NumberFormatter(format="0")}


def formatear(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if not df.empty:
        df["resultado"] = df["resultado"].map(
            {"AUTORIZADO": "✔ AUTORIZADO", "NO AUTORIZADO": "✖ NO AUTORIZADO"}).fillna(df["resultado"])
        df["fecha"] = df["fecha"].str.replace("T", " ")
    return df


def colorear(fila):
    c = "#e8f5e9" if str(fila["resultado"]).startswith("✔") else "#ffebee"
    return [f"background-color:{c}"] * len(fila)


def tabla_html(filas) -> str:
    cuerpo = "".join(f"<tr><td style='padding:4px 12px 4px 0;color:#555'>{a}</td><td><b>{b}</b></td></tr>"
                     for a, b in filas)
    return f"<table style='font-size:14px'>{cuerpo}</table>"


def badge_verificacion(placa: str, resultado: str, propietario: str) -> str:
    c = VERDE if resultado == "AUTORIZADO" else ROJO
    return (f"<div style='border-left:8px solid {c};padding:6px 10px'><b>{placa}</b><br>"
            f"<span style='color:{c};font-weight:700'>{resultado}</span><br>"
            f"{html.escape(propietario or '')}</div>")


def tarjeta_html(l, umbral: float) -> str:
    if l is None:
        return "<div style='padding:40px;text-align:center;color:#777;font-size:18px'>Esperando vehículo…</div>"
    ok = l.resultado == "AUTORIZADO"
    color, icono = (VERDE, "✔") if ok else (ROJO, "✖")
    if l.corregido_por:
        nota = f"<div style='color:#555;margin-top:6px'>✎ Corregida por {html.escape(l.corregido_por)}</div>"
    elif l.conf_ocr < umbral:
        nota = ("<div style='background:#fff3cd;padding:6px 8px;border-radius:4px;margin-top:6px'>"
                "⚠ Confianza baja: compare con la imagen y corrija si es necesario</div>")
    else:
        nota = ""
    lat = f"{l.latencia_ms:.0f} ms " + ("✔" if l.latencia_ms <= config.META_LATENCIA_MS else "✖ excede 2 s")
    return f"""
    <div style="border-left:12px solid {color};padding:12px 16px;background:#fafafa;border-radius:8px">
      <div style="font-size:13px;color:#666">{l.fecha:%d/%m/%Y %H:%M:%S} · {html.escape(l.camara)} · #{l.id}</div>
      <div style="font:700 46px/1.15 monospace;letter-spacing:5px">{l.placa}</div>
      <div style="background:{color};color:#fff;font-size:26px;font-weight:700;padding:6px 14px;
                  border-radius:6px;display:inline-block;margin:6px 0">{icono} {l.resultado}</div>
      {tabla_html([("Propietario", html.escape(l.propietario or "—")),
                   ("Confianza OCR", f"{l.conf_ocr:.0%} <progress value='{l.conf_ocr:.2f}' max='1'></progress>"),
                   ("Confianza detección", f"{l.conf_det:.0%}"),
                   ("Ciclo completo", lat)])}
      {nota}
    </div>"""


def metricas_modelo_html(ruta_modelo: str) -> str:
    ruta = Path(ruta_modelo).parent / "resumen_metricas.json"
    if not ruta.exists():
        return "<i>No se encontró resumen_metricas.json junto al modelo.</i>"
    m = json.loads(ruta.read_text())
    filas = []
    for nombre, clave, meta in [("RF-01 Tasa de detección (IoU ≥ 0.75)", "tasa_deteccion_iou075", 0.95),
                                ("RF-02 IoU promedio", "iou_promedio_todas", 0.75),
                                ("mAP@0.5", "mAP50", None), ("mAP@0.5:0.95", "mAP50_95", None),
                                ("Precisión", "precision", None), ("Recall", "recall", None)]:
        v = m.get(clave)
        if v is None:
            continue
        estado = "" if meta is None else (f" (meta {meta}) " + ("✔" if v >= meta else "✖"))
        filas.append((nombre, f"{v:.3f}{estado}"))
    filas.append(("Imágenes de prueba", m.get("imagenes", "—")))
    return tabla_html(filas)
