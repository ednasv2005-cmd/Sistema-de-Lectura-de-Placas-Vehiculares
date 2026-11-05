"""RF-03 (pendiente en el proyecto). Cualquier clase con `leer(roi) -> (texto, confianza)`
y atributo `disponible` puede sustituir a OCREasy al construir el Procesador."""
import cv2
import numpy as np

from lpr.config import ALNUM
from lpr.core.utils import normalizar


class OCREasy:
    nombre = "EasyOCR (provisional)"

    def __init__(self):
        try:
            import easyocr
            self.lector = easyocr.Reader(["en"], gpu=False, verbose=False)
        except Exception as exc:
            print(f"[OCR] no disponible ({exc}); sólo se mostrarán detecciones.")
            self.lector = None

    @property
    def disponible(self) -> bool:
        return self.lector is not None

    def leer(self, roi: np.ndarray) -> tuple[str, float]:
        if self.lector is None or roi.size == 0 or roi.shape[1] < 40:
            return "", 0.0
        gris = cv2.resize(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), None, fx=2, fy=2,
                          interpolation=cv2.INTER_CUBIC)
        res = self.lector.readtext(gris, allowlist=ALNUM)
        if not res:
            return "", 0.0
        altos = [abs(c[2][1] - c[0][1]) for c, _, _ in res]
        hmax = max(altos)
        # Placas MX: descarta textos pequeños (estado, leyendas) y ordena de izquierda a derecha
        partes = sorted((r for r, a in zip(res, altos) if a >= 0.6 * hmax), key=lambda r: r[0][0][0])
        return normalizar("".join(t for _, t, _ in partes)), float(np.mean([c for _, _, c in partes]))
