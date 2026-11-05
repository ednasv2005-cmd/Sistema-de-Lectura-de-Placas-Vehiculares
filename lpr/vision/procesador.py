"""Pipeline: detección (YOLO) → OCR → verificación (RF-04) → registro (RF-06)."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, replace
from datetime import datetime

import cv2
import numpy as np

from lpr import config
from lpr.core.privacidad import anonimizar
from lpr.core.utils import a_jpg, ocultar_credenciales, placa_valida
from lpr.datos.base_datos import BaseDatos
from lpr.vision.camara import Camara
from lpr.vision.ocr import OCREasy

BGR_AUTORIZADO, BGR_DENEGADO, BGR_SIN_LECTURA = (0, 170, 0), (0, 0, 220), (0, 200, 255)


@dataclass
class Lectura:
    id: int
    fecha: datetime
    placa: str
    resultado: str
    propietario: str
    conf_ocr: float
    conf_det: float
    latencia_ms: float
    camara: str
    imagen: str
    recorte: str
    corregido_por: str = ""


class Procesador(threading.Thread):
    def __init__(self, db: BaseDatos, cam: Camara, ocr=None, modelo: str = config.MODELO):
        super().__init__(daemon=True)
        from ultralytics import YOLO
        self.db, self.cam = db, cam
        self.modelo_ruta = modelo
        self.modelo = YOLO(modelo, task="detect")
        self.ocr = ocr or OCREasy()
        self.lock_modelo = threading.Lock()
        self.conf_det, self.umbral_ocr = config.CONF_DET, config.UMBRAL_OCR
        self.cooldown, self.pausado = config.COOLDOWN_S, False
        self.jpg: bytes | None = None
        self.ultima: Lectura | None = None
        self.version, self.fps, self.inicio = 0, 0.0, time.time()
        self.latencias: deque[float] = deque(maxlen=300)
        self._vistas: dict[str, tuple[float, str]] = {}

    # ── bucle principal ──
    def run(self):
        ultimo = -1
        while True:
            try:
                fid, frame = self.cam.leer()
                if frame is None or fid == ultimo:
                    time.sleep(0.02)
                    continue
                ultimo, t = fid, time.perf_counter()
                vis = frame if self.pausado else self.procesar(frame, ocultar_credenciales(self.cam.fuente))[0]
                self.jpg = a_jpg(vis, 960)
                self.fps = 0.8 * self.fps + 0.2 / max(time.perf_counter() - t, 1e-3)
            except Exception as exc:  # el hilo nunca muere (RNF-01)
                print("[procesador]", exc)
                time.sleep(1)

    # ── un frame ──
    def procesar(self, frame: np.ndarray, camara: str, deduplicar: bool = True):
        t0 = time.perf_counter()
        with self.lock_modelo:
            r = self.modelo.predict(frame, imgsz=config.IMG_SIZE, conf=self.conf_det, verbose=False)[0]
        vis, (h, w) = frame.copy(), frame.shape[:2]
        lecturas = []
        for (x1, y1, x2, y2), cdet in zip(r.boxes.xyxy.cpu().numpy().astype(int), r.boxes.conf.cpu().numpy()):
            mx, my = int((x2 - x1) * 0.05), int((y2 - y1) * 0.10)
            roi = frame[max(0, y1 - my):min(h, y2 + my), max(0, x1 - mx):min(w, x2 + mx)]
            placa, cocr = self.ocr.leer(roi)
            color, texto = BGR_SIN_LECTURA, f"? {cdet:.2f}"
            if placa_valida(placa):
                ahora = time.time()
                visto, res = self._vistas.get(placa, (0.0, None))
                if res is None or not deduplicar or ahora - visto > self.cooldown:
                    lect = self._registrar(frame, roi, placa, cocr, float(cdet), t0, camara)
                    res = lect.resultado
                    lecturas.append(lect)
                self._vistas[placa] = (ahora, res)  # vehículo detenido = un solo evento
                color = BGR_AUTORIZADO if res == "AUTORIZADO" else BGR_DENEGADO
                texto = f"{placa} {cocr:.0%}"
            cv2.rectangle(vis, (x1, y1), (x2, y2), color, 3)
            cv2.putText(vis, texto, (x1, max(25, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
        self._podar_vistas()
        return vis, lecturas

    def _podar_vistas(self):
        if len(self._vistas) > 500:
            lim = time.time() - self.cooldown
            self._vistas = {k: v for k, v in self._vistas.items() if v[0] > lim}

    def _registrar(self, frame, roi, placa, cocr, cdet, t0, camara) -> Lectura:
        resultado, prop = self.db.verificar(placa)
        lat = (time.perf_counter() - t0) * 1000  # ciclo detección → OCR → verificación (RF-05)
        ahora = datetime.now()
        carpeta = config.DIR_IMG / f"{ahora:%Y-%m-%d}"
        carpeta.mkdir(parents=True, exist_ok=True)
        base = carpeta / f"{ahora:%H%M%S_%f}_{placa}"
        img, rec = f"{base}.jpg", f"{base}_placa.jpg"
        cv2.imwrite(img, anonimizar(frame.copy()))
        cv2.imwrite(rec, roi)
        id_ev = self.db.registrar(fecha=ahora.isoformat(timespec="seconds"), placa=placa, resultado=resultado,
                                  propietario=prop, conf_ocr=cocr, conf_det=cdet, latencia_ms=lat,
                                  camara=camara, imagen=img, recorte=rec)
        self.latencias.append(lat)
        self.ultima = Lectura(id_ev, ahora, placa, resultado, prop, cocr, cdet, lat, camara, img, rec)
        self.version += 1
        return self.ultima

    def actualizar_ultima(self, id_evento, placa, resultado, prop, usuario):
        if self.ultima and self.ultima.id == id_evento:
            self.ultima = replace(self.ultima, placa=placa, resultado=resultado,
                                  propietario=prop, corregido_por=usuario)
        self.version += 1
