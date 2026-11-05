"""
Punto de entrada.
    python app_lpr.py
    # o bien:
    panel serve app_lpr.py --basic-auth credenciales.json --cookie-secret <secreto>
"""
import panel as pn

from lpr import config
from lpr.ui.app import crear_app

if __name__ == "__main__":
    pn.serve(crear_app, port=config.PUERTO, show=False, title="LPR/ANPR",
             basic_auth=config.USUARIOS, cookie_secret=config.COOKIE_SECRET)
elif __name__.startswith("bokeh"):
    crear_app().servable()
