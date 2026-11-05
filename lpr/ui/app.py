"""Ensambla la aplicación por sesión. Para agregar una pestaña basta con añadirla a PESTANAS."""
import html

import panel as pn

from lpr import config
from lpr.servicios import servicios
from lpr.ui.contexto import Contexto
from lpr.ui.estilos import PRIMARIO
from lpr.ui.historial import VistaHistorial
from lpr.ui.monitoreo import VistaMonitoreo
from lpr.ui.padron import VistaPadron
from lpr.ui.sidebar import construir_sidebar
from lpr.ui.sistema import VistaSistema

pn.extension("tabulator", "echarts", notifications=True)

# Cada vista expone: titulo, layout y, opcionalmente, actualizar() (1 s) y actualizar_rapido() (200 ms)
PESTANAS = [VistaMonitoreo, VistaHistorial, VistaPadron, VistaSistema]


def crear_app():
    db, cam, proc = servicios()
    usuario = pn.state.user or "local"
    ctx = Contexto(db, cam, proc, usuario, usuario in config.ADMINS, pn.state.notifications)

    vistas = [V(ctx) for V in PESTANAS]
    lentas = [v.actualizar for v in vistas if hasattr(v, "actualizar")]
    rapidas = [v.actualizar_rapido for v in vistas if hasattr(v, "actualizar_rapido")]

    def tick_lento():
        for f in lentas:
            f()

    def tick_rapido():
        for f in rapidas:
            f()

    tick_lento()
    pn.state.add_periodic_callback(tick_rapido, period=200)
    pn.state.add_periodic_callback(tick_lento, period=1000)

    rol = "administrador" if ctx.admin else "vigilancia"
    return pn.template.FastListTemplate(
        title="Sistema LPR/ANPR · Control de acceso vehicular",
        sidebar=construir_sidebar(ctx),
        main=[pn.Tabs(*[(v.titulo, v.layout) for v in vistas])],
        header=[pn.pane.HTML(f"<div style='color:white;padding-top:12px'>👤 {html.escape(usuario)} ({rol}) · "
                             f"<a href='/logout' style='color:white'>Cerrar sesión</a></div>")],
        accent=PRIMARIO, header_background=PRIMARIO, sidebar_width=330)
