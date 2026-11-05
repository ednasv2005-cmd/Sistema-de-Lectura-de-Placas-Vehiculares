"""Captura de video con reconexión automática (RNF-01)."""
import threading
import time
from pathlib import Path

import cv2


class Camara(threading.Thread):
    """Conserva sólo el último frame (sin retraso acumulado en RTSP) y se reconecta sola."""

    def __init__(self, fuente: str):
        super().__init__(daemon=True)
        self.fuente, self.ok, self.reconexiones = fuente, False, 0
        self._frame, self._id = None, 0
        self._lock, self._cambio = threading.Lock(), threading.Event()

    def cambiar(self, fuente: str):
        self.fuente = fuente
        self._cambio.set()

    def leer(self):
        with self._lock:
            return self._id, self._frame

    def run(self):
        while True:
            self._cambio.clear()
            src = int(self.fuente) if str(self.fuente).isdigit() else self.fuente
            es_archivo = isinstance(src, str) and Path(src).is_file()
            cap = cv2.VideoCapture(src)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            espera = 1.0 / (cap.get(cv2.CAP_PROP_FPS) or 15) if es_archivo else 0.0
            while cap.isOpened() and not self._cambio.is_set():
                ok, frame = cap.read()
                if not ok:
                    if es_archivo and cap.get(cv2.CAP_PROP_POS_FRAMES) > 0:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # video de prueba en bucle
                        continue
                    break
                with self._lock:
                    self._frame, self._id = frame, self._id + 1
                self.ok = True
                if espera:
                    time.sleep(espera)
            cap.release()
            with self._lock:
                self._frame = None
            self.ok = False
            if not self._cambio.is_set():
                self.reconexiones += 1
                self._cambio.wait(3)  # reintento automático cada 3 s
