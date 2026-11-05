"""Configuración central. Todo se puede sobrescribir con variables de entorno."""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Rutas y fuentes
MODELO = os.getenv("LPR_MODELO", str(BASE / "modelo_placas" / "best.onnx"))
FUENTE = os.getenv("LPR_FUENTE", "0")  # 0 = webcam | rtsp://user:pass@ip/stream | video.mp4
DB_PATH = Path(os.getenv("LPR_DB", str(BASE / "lpr.db")))
DIR_IMG = Path(os.getenv("LPR_IMAGENES", str(BASE / "eventos")))

# Servidor y acceso (RNF-05)
PUERTO = int(os.getenv("LPR_PUERTO", "5006"))
USUARIOS: dict[str, str] = json.loads(
    os.getenv("LPR_USUARIOS", '{"admin": "admin123", "guardia": "guardia123"}'))
ADMINS = set(os.getenv("LPR_ADMINS", "admin").split(","))
COOKIE_SECRET = os.getenv("LPR_COOKIE_SECRET") or secrets.token_hex(32)

# Modelo y metas
IMG_SIZE = 640
META_LATENCIA_MS = 2000  # RF-05
ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# Valores iniciales (ajustables por el administrador desde la UI)
CONF_DET = 0.50
UMBRAL_OCR = 0.60
COOLDOWN_S = 15
