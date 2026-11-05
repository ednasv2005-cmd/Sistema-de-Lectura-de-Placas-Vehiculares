import re

import cv2
import numpy as np


def normalizar(texto: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (texto or "").upper())


def placa_valida(p: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{5,8}", p) and re.search(r"\d", p) and re.search(r"[A-Z]", p))


def ocultar_credenciales(fuente) -> str:
    return re.sub(r"//[^/@]+@", "//***@", str(fuente))


def a_jpg(img: np.ndarray, ancho: int | None = None, calidad: int = 75) -> bytes:
    if ancho and img.shape[1] > ancho:
        img = cv2.resize(img, (ancho, int(img.shape[0] * ancho / img.shape[1])))
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, calidad])[1].tobytes()
