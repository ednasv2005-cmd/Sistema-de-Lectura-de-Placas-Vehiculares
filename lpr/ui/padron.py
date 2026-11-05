"""Padrón de vehículos (RF-04). Edición sólo para administradores."""
import io

import pandas as pd
import panel as pn

from lpr.core.utils import normalizar, placa_valida
from lpr.ui.contexto import Contexto


class VistaPadron:
    titulo = "🚗 Padrón"

    def __init__(self, ctx: Contexto):
        self.ctx = ctx
        self.tabla = pn.widgets.Tabulator(
            ctx.db.padron(), show_index=False, sizing_mode="stretch_width", header_filters=True,
            pagination="local", page_size=20, disabled=not ctx.admin,
            selectable="checkbox" if ctx.admin else False, editors={"placa": None})
        self.tabla.on_edit(self._editar)
        self.layout = self._layout_admin() if ctx.admin else pn.Column(
            pn.pane.Alert("Vista de sólo lectura (perfil vigilancia).", alert_type="info"),
            self.tabla, sizing_mode="stretch_width")

    def _layout_admin(self):
        self.n_placa = pn.widgets.TextInput(name="Placa")
        self.n_prop = pn.widgets.TextInput(name="Propietario")
        self.n_veh = pn.widgets.TextInput(name="Vehículo (marca / modelo / color)")
        self.n_notas = pn.widgets.TextInput(name="Notas")
        b_agregar = pn.widgets.Button(name="➕ Agregar / actualizar", button_type="primary")
        b_borrar = pn.widgets.Button(name="🗑 Eliminar seleccionados", button_type="danger")
        csv = pn.widgets.FileInput(accept=".csv")

        b_agregar.on_click(self._agregar)
        b_borrar.on_click(self._borrar)
        csv.param.watch(self._importar, "value")

        return pn.Row(
            pn.Column("#### Alta de vehículo", self.n_placa, self.n_prop, self.n_veh, self.n_notas, b_agregar,
                      pn.layout.Divider(), "#### Importar CSV", csv,
                      pn.layout.Divider(), b_borrar, width=320),
            self.tabla, sizing_mode="stretch_width")

    def recargar(self):
        self.tabla.value = self.ctx.db.padron()

    def _editar(self, e):
        placa = self.tabla.value.iloc[e.row]["placa"]
        self.ctx.db.editar_vehiculo(placa, e.column, e.value)
        self.ctx.notif.success(f"{placa}: «{e.column}» actualizado")

    def _agregar(self, _):
        p = normalizar(self.n_placa.value)
        if not placa_valida(p):
            self.ctx.notif.warning("Placa no válida (5–8 caracteres alfanuméricos).")
            return
        self.ctx.db.guardar_vehiculo(p, self.n_prop.value, self.n_veh.value, True, self.n_notas.value)
        for w in (self.n_placa, self.n_prop, self.n_veh, self.n_notas):
            w.value = ""
        self.recargar()
        self.ctx.notif.success(f"{p} guardada en el padrón")

    def _borrar(self, _):
        placas = self.tabla.value.iloc[self.tabla.selection]["placa"].tolist()
        if placas:
            self.ctx.db.borrar_vehiculos(placas)
            self.recargar()
            self.ctx.notif.success(f"{len(placas)} vehículo(s) eliminados")

    def _importar(self, e):
        if not e.new:
            return
        df = pd.read_csv(io.BytesIO(e.new), dtype=str).fillna("")
        if "placa" not in df.columns:
            self.ctx.notif.error("El CSV debe tener columnas: placa, propietario, vehiculo, vigente, notas")
            return
        n = 0
        for f in df.to_dict("records"):
            p = normalizar(f["placa"])
            if placa_valida(p):
                vig = str(f.get("vigente", "1")).strip().lower() not in {"0", "false", "no"}
                self.ctx.db.guardar_vehiculo(p, f.get("propietario", ""), f.get("vehiculo", ""),
                                             vig, f.get("notas", ""))
                n += 1
        self.recargar()
        self.ctx.notif.success(f"{n} vehículos importados")
