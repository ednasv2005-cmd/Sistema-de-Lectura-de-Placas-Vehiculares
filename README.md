# Sistema de Lectura de Placas Vehiculares (LPR) — v0.2

Sistema de reconocimiento automático de placas vehiculares (ALPR/LPR) para el control de acceso.
Detecta la placa en video en tiempo real con **YOLOv8n**, lee los caracteres con **OCR**,
consulta un **padrón** de vehículos autorizados y registra cada evento en una bitácora auditable.
Todo se maneja desde una interfaz web hecha en Python con **Panel (HoloViz)**.

> **Estado:** prototipo funcional v0.2 (segundo parcial). La versión del primer parcial era una
> prueba de concepto (PoC) con el dataset CCPD.

---

## Tabla de contenido
1. [Características](#características)
2. [Arquitectura](#arquitectura)
3. [Estructura del repositorio](#estructura-del-repositorio)
4. [Requisitos](#requisitos)
5. [Instalación y ejecución local](#instalación-y-ejecución-local)
6. [Configuración (variables de entorno)](#configuración-variables-de-entorno)
7. [Padrón sintético de prueba](#padrón-sintético-de-prueba)
8. [Métricas del modelo](#métricas-del-modelo)
9. [Cambios respecto a la versión del primer parcial](#cambios-respecto-a-la-versión-del-primer-parcial)
10. [Limitaciones y trabajo futuro](#limitaciones-y-trabajo-futuro)

---

## Características
- Detección de placas en tiempo real desde una webcam, una cámara IP (RTSP/HTTP) o un celular usado como cámara.
- Lectura de caracteres con OCR (EasyOCR, provisional).
- Verificación contra el padrón: **AUTORIZADO**, **NO VIGENTE** o **NO AUTORIZADO**.
- Bitácora de eventos en SQLite con evidencia (fotograma y recorte de la placa), confianza y latencia.
- Corrección manual de lecturas (queda registrado quién corrigió).
- Gestión del padrón: alta, edición, baja e importación desde CSV.
- Autenticación con usuarios y roles (operador / administrador).
- Privacidad: los rostros se difuminan en la evidencia guardada.
- Reconexión automática de la cámara y supresión de lecturas duplicadas (cooldown por placa).

---

## Arquitectura

### Vista de componentes

```
┌──────────────────────────── Interfaz web (Panel) ─────────────────────────────┐
│  Monitoreo  │  Historial  │  Padrón  │  Sistema           (lpr/ui/*)           │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ Contexto / servicios() (singleton compartido)
        ┌───────────────────────┼─────────────────────────────┐
        ▼                       ▼                             ▼
┌───────────────┐      ┌──────────────────┐          ┌──────────────────┐
│   Camara      │─────▶│   Procesador     │─────────▶│    BaseDatos     │
│ (hilo, último │frame │ YOLOv8 → OCR →   │ evento   │ SQLite (WAL)     │
│  fotograma,   │      │ normalizar →     │          │ padron / eventos │
│  reconexión)  │      │ verificar →      │◀─────────│                  │
└───────────────┘      │ anonimizar       │ verificar└──────────────────┘
                       └──────────────────┘
                                │ imágenes de evidencia
                                ▼
                         data/eventos/*.jpg
```

| Capa | Módulo | Responsabilidad |
|------|--------|-----------------|
| Configuración | `lpr/config.py` | Variables de entorno y constantes (umbrales, tamaño de entrada, cooldown). |
| Servicios | `lpr/servicios.py` | Crea una sola vez `(db, cam, proc)` y los comparte entre sesiones. |
| Núcleo | `lpr/core/utils.py`, `lpr/core/privacidad.py` | Normalización y validación de placas, ocultar credenciales en URLs, difuminado de rostros. |
| Datos | `lpr/datos/base_datos.py` | Padrón, eventos, correcciones, resúmenes y consultas filtradas. |
| Visión | `lpr/vision/camara.py`, `ocr.py`, `procesador.py` | Captura, detección (YOLO ONNX/OpenVINO/PT), OCR y registro del evento. |
| Interfaz | `lpr/ui/*.py` | Pestañas de la aplicación, barra lateral y estilos. |
| Entrada | `app_lpr.py` | Inicia el pipeline y levanta el servidor Panel con autenticación. |

### Flujo de una lectura
1. `Camara` captura de forma continua y guarda solo el último fotograma.
2. `Procesador` ejecuta YOLOv8n a 640 px y descarta las detecciones con confianza menor a 0.5.
3. La región de la placa pasa por el OCR. El texto se normaliza (A–Z, 0–9) y se valida el formato.
4. Si la lectura supera el umbral de OCR (0.6) y no está en cooldown, se consulta el padrón.
5. Se difuminan los rostros y se guarda la evidencia junto con el evento (resultado, confianzas y latencia).
6. La interfaz consulta cada 200 ms (video) y cada 1 s (tablas e indicadores).

### Vista de despliegue

```
 Webcam USB / cámara IP / celular ──USB/RTSP/HTTP──▶ ┌──────────────────────────────┐
                                                     │ Equipo local (Linux)         │
 Navegador del operador ◀──────HTTP :5006──────────▶ │  venv + python app_lpr.py    │
                                                     │  ├─ modelo_placas/           │
                                                     │  └─ data/ (lpr.db, eventos)  │
                                                     └──────────────────────────────┘
```

---

## Estructura del repositorio

```
.
├── app_lpr.py                 # Punto de entrada
├── requirements.txt
├── lpr/
│   ├── config.py
│   ├── servicios.py
│   ├── core/       (utils.py, privacidad.py)
│   ├── datos/      (base_datos.py)
│   ├── vision/     (camara.py, ocr.py, procesador.py)
│   └── ui/         (app.py, contexto.py, estilos.py, sidebar.py,
│                    monitoreo.py, historial.py, padron.py, sistema.py)
├── scripts/
│   └── generar_padron.py      # Padrón sintético para pruebas
├── modelo_placas/             # best.pt / best.onnx / best_openvino_model (no versionado)
└── data/                      # BD y evidencias (no versionado)
```

> `venv/`, `credenciales.json`, `data/`, `*.db` y los pesos del modelo están en `.gitignore`.

---

## Requisitos
- Python 3.10–3.12 con `venv`
- Linux, Windows o macOS (probado en Fedora 44)
- 4 GB de RAM como mínimo. No se necesita GPU: la inferencia corre en CPU con ONNX Runtime u OpenVINO.
- Una cámara: webcam, cámara IP o un celular con una app de cámara IP (por ejemplo *IP Webcam* o *DroidCam*).
- Los pesos del modelo en `modelo_placas/`. Se obtienen descomprimiendo `modelo_placas.zip`.

---

## Instalación y ejecución local

```bash
git clone https://github.com/ednasv2005-cmd/Sistema-de-Lectura-de-Placas-Vehiculares.git
cd Sistema-de-Lectura-de-Placas-Vehiculares

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# Modelo
unzip modelo_placas.zip -d modelo_placas   # si no existe la carpeta

# Configuración
export LPR_FUENTE=0                       # 0 = webcam; o URL de la cámara/celular
export LPR_USUARIOS="admin:ClaveSegura1"
export LPR_ADMINS=admin


# (Opcional) padrón de prueba
python scripts/generar_padron.py -n 50 --db

# Ejecutar
python app_lpr.py
```

Abre **http://localhost:5006** e inicia sesión con un usuario definido en `LPR_USUARIOS`.


## Configuración (variables de entorno)

| Variable | Ejemplo | Descripción |
|----------|---------|-------------|
| `LPR_FUENTE` | `0` · `rtsp://usuario:clave@192.168.1.50:554/stream` · `http://192.168.1.70:8080/video` | Índice de la webcam o URL de la cámara o celular. |
| `LPR_MODELO` | `modelo_placas/best.onnx` | Ruta del modelo (`.pt`, `.onnx` o carpeta OpenVINO). |
| `LPR_DB` | `data/lpr.db` | Base de datos SQLite. |
| `LPR_IMAGENES` | `data/eventos` | Carpeta de evidencias. |
| `LPR_USUARIOS` | `admin:ClaveSegura1,operador:OtraClave2` | Usuarios con su contraseña. |
| `LPR_USUARIOS_ARCHIVO` | `credenciales.json` | Alternativa a `LPR_USUARIOS`: un archivo JSON. |
| `LPR_ADMINS` | `admin` | Usuarios con rol de administrador. |
| `LPR_COOKIE_SECRET` | `[cadena aleatoria]` | Genérala con `python -c "import secrets;print(secrets.token_hex(32))"`. |
| `LPR_DIRECCION` / `LPR_PUERTO` | `0.0.0.0` / `5006` | Dirección y puerto del servidor. |
| `LPR_ORIGEN` | `localhost:5006,192.168.1.10:5006` | Orígenes permitidos para el websocket. |

---

## Padrón sintético de prueba
`scripts/generar_padron.py` genera propietarios ficticios, placas con formato mexicano y vehículos.
Todos los registros llevan la marca **SINTÉTICO** en `notas`.

```bash
python scripts/generar_padron.py -n 50 --incluir ABC123D --db   # inserta en la BD
python scripts/generar_padron.py -n 50                          # solo CSV → data/padron_sintetico.csv
```

El CSV se puede importar desde la pestaña **Padrón → Importar CSV**. Sus columnas son
`placa, propietario, vehiculo, vigente, notas`.

---

## Métricas del modelo
YOLOv8n con una clase (`LicensePlate`) a 640 px. Evaluado en el split de prueba: 9 imágenes con 11 placas.

| Métrica | Valor |
|---------|-------|
| mAP@50 | 0.995 |
| mAP@50-95 | 0.683 |
| Precisión | 0.915 |
| Recall | 1.000 |
| Tasa de detección (IoU ≥ 0.75) | 90.9 % |
| IoU promedio | 0.858 |

> El conjunto de prueba es pequeño. El intervalo de confianza de Wilson al 95 % para la tasa de
> detección es de [62 %, 98 %], así que hacen falta más datos para confirmar RF-01.

---

## Cambios respecto a la versión del primer parcial

| Aspecto | Primer parcial (PoC) | v0.2 (actual) |
|---------|----------------------|---------------|
| Objetivo | Demostrar la detección de placas | Sistema de control de acceso funcional de principio a fin |
| Dataset | CCPD (placas chinas) | Placas mexicanas (Roboflow: *License Plates Mexico*, *Placas*) `[COMPLETAR: tamaño/licencia]` |
| Modelo | Prueba inicial con YOLO | YOLOv8n reentrenado, exportado a ONNX y OpenVINO para CPU |
| Lectura de caracteres | No incluida | OCR con EasyOCR, normalización y validación del formato |
| Interfaz | Mockup estático (`index.html`) | App web en Python (Panel) con monitoreo en vivo |
| Persistencia | Ninguna | SQLite (WAL): padrón y bitácora de eventos con evidencia |
| Padrón | No existía | Alta, edición, baja, importación CSV y generador sintético |
| Seguridad | Ninguna | Login, roles (operador/admin) y credenciales fuera del repositorio |
| Privacidad | No contemplada | Difuminado de rostros en las evidencias |
| Robustez | Ejecución puntual en notebook | Hilos de captura y procesamiento, reconexión de cámara y cooldown de duplicados |
| Código | Notebook monolítico | Paquete modular `lpr/` (core, datos, vision, ui) |
| Despliegue | Google Colab | Ejecución local con entorno virtual (`venv`) y configuración por variables de entorno |
| Repositorio | Archivos subidos sin control | `.gitignore` y separación de configuración y secretos |

---

## Limitaciones y trabajo futuro
- **RF-03:** el OCR es provisional (EasyOCR). Falta entrenar o ajustar un OCR específico para placas mexicanas.
- **RF-04:** falta la API REST para integrarse con sistemas externos.
- **RNF-05:** la base de datos SQLite no está cifrada. Se planea SQLCipher o PostgreSQL con TLS.
- El conjunto de prueba es pequeño, y faltan pruebas nocturnas, con ángulos extremos y con placas sucias.
- Falta integrar el medidor de uso y el estado de cuenta en la interfaz.
- Contenerizar el sistema (Docker) para facilitar el despliegue en otros equipos.

---

## Autores
- [Edna Andrea Serrano Vela, David Torres, Gómez] — [COMPLETAR: Formulación y Evaluación de Proyectos Informáticos / Unidad Profesional Interdisciplinaria de Ingeniería Campus Tlaxcala (UPIIT) / Periodo 2027-1]
