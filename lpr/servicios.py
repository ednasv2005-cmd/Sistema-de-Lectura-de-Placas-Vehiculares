"""Un único pipeline compartido por todas las sesiones del navegador."""
import threading

import panel as pn

from lpr import config
from lpr.datos.base_datos import BaseDatos
from lpr.vision.camara import Camara
from lpr.vision.procesador import Procesador

_lock = threading.Lock()


def servicios() -> tuple[BaseDatos, Camara, Procesador]:
    with _lock:
        if "lpr" not in pn.state.cache:
            config.DIR_IMG.mkdir(parents=True, exist_ok=True)
            db = BaseDatos(config.DB_PATH)
            cam = Camara(config.FUENTE)
            cam.start()
            proc = Procesador(db, cam)
            proc.start()
            pn.state.cache["lpr"] = (db, cam, proc)
        return pn.state.cache["lpr"]
