"""RNF-05: oculta información no relevante (rostros) antes de guardar la evidencia."""
import cv2
import numpy as np

try:
    _ROSTROS = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
except Exception:
    _ROSTROS = None


def anonimizar(img: np.ndarray) -> np.ndarray:
    if _ROSTROS is None or _ROSTROS.empty():
        return img
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    for x, y, w, h in _ROSTROS.detectMultiScale(gris, 1.1, 5, minSize=(30, 30)):
        img[y:y + h, x:x + w] = cv2.GaussianBlur(img[y:y + h, x:x + w], (51, 51), 0)
    return img
