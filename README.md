# Prototipo de Detección y Recorte de Placas Vehiculares (LPR/ANPR)

**Proyecto:** Sistema de Lectura de Placas — Formulación y Evaluación de Proyectos Informáticos 2026
**Paquete de trabajo (WBS):** 2.2 — Detección YOLO y ROI de Matrícula
**Dataset:** Chinese City Parking Dataset (CCPD) — +300,000 imágenes

Notebook: [`prototipo_deteccion_placas_CCPD.ipynb`](./prototipo_deteccion_placas_CCPD.ipynb)

---

## 1. ¿Qué hace este notebook?

Implementa un primer prototipo del pipeline de detección de placas descrito en la Memoria
Técnica del proyecto:

```
Imágenes CCPD  →  Modelo YOLO (detección de placa)  →  Placa recortada (ROI)  →  Métricas  →  Visualización
```

Concretamente:

1. Lee imágenes del dataset CCPD (directo desde el `.tar.xz` o desde una carpeta ya descomprimida).
2. Parsea las anotaciones (bbox, número de placa, etc.), que en CCPD van embebidas en el
   nombre de cada archivo, no en un archivo de anotación aparte.
3. Convierte una muestra al formato que espera Ultralytics YOLO (`images/`, `labels/`, `data.yaml`).
4. Entrena un detector YOLOv8n de una sola clase (`placa`).
5. Evalúa el modelo: mAP@0.5, mAP@0.5:0.95, precisión, recall, **IoU promedio** y
   **tasa de detección**, comparándolas contra los requisitos del proyecto:

   | Requisito | Descripción | Meta |
   |---|---|---|
   | RF-01 | Tasa de detección de vehículos/placa | ≥ 95 % |
   | RF-02 | Localización del ROI de matrícula (IoU) | ≥ 0.75 |

6. Recorta la placa detectada (ROI) de cada imagen de prueba.
7. Genera visualizaciones (imagen + caja predicha vs. real + placa recortada).

### Alcance y limitación importante

CCPD contiene **placas chinas**. Este notebook se limita a la tarea **geométrica** de
localizar la placa como objeto (transferible entre países) y **no incluye OCR** (lectura
de caracteres): eso corresponde al paquete 2.3 del proyecto (RF-03), que requiere un
dataset de placas mexicanas y queda fuera de este prototipo. La sección final del
notebook ("Conclusiones y siguientes pasos") detalla esto.

---

## 2. Requisitos

- Python ≥ 3.9
- GPU recomendada para el entrenamiento (funciona en CPU, pero mucho más lento). Entornos
  sugeridos: Google Colab (con GPU activada) o Kaggle Notebooks.
- Dependencias (se instalan en la primera celda del notebook):

  ```bash
  pip install ultralytics opencv-python-headless matplotlib pandas tqdm scikit-learn
  ```

---

## 3. Obtener el dataset CCPD

Descarga oficial desde el repositorio [`detectRecog/CCPD`](https://github.com/detectRecog/CCPD)
(enlaces a Google Drive / BaiduYun, archivo `CCPD2019.tar.xz`, ~12 GB).

El notebook admite **dos formas de leerlo**, controladas por el parámetro `DATASET_SOURCE`:

| Modo | Cuándo usarlo | Qué hace |
|---|---|---|
| `"tar"` (por defecto) | Tienes el `.tar.xz` descargado y quieres evitar ocupar ~12 GB extra al descomprimir | Lee el archivo **una sola vez, en streaming**, y aplica *reservoir sampling* para tomar una muestra aleatoria de tamaño exacto sin extraer las imágenes no elegidas |
| `"folder"` | Ya tienes el dataset descomprimido (p. ej. un "Input Dataset" de Kaggle) | Lee directamente de la carpeta con `ccpd_base/`, `ccpd_blur/`, etc. |

Estructura interna esperada del `.tar` / carpeta:

```
CCPD2019/
├── ccpd_base/       (imágenes "normales")
├── ccpd_blur/
├── ccpd_challenge/
├── ccpd_db/
├── ccpd_fn/
├── ccpd_rotate/
├── ccpd_tilt/
└── splits/
```

---

## 4. Cómo ejecutarlo

1. Abre el notebook en Colab, Kaggle o Jupyter local.
2. Ejecuta la celda de instalación de dependencias.
3. En la sección **"2. Parámetros generales"**, ajusta según tu caso:

   | Parámetro | Descripción |
   |---|---|
   | `DATASET_SOURCE` | `"tar"` o `"folder"` |
   | `DATASET_TAR_PATH` | Ruta al `.tar.xz` (si `DATASET_SOURCE = "tar"`) |
   | `DATASET_DIR` | Carpeta descomprimida (si `DATASET_SOURCE = "folder"`) |
   | `CCPD_SUBSETS` | Subcarpetas de CCPD a usar (por defecto: base, blur, tilt) |
   | `SAMPLE_SIZE` | Nº de imágenes de la muestra (por defecto 3,000; súbelo para un modelo más robusto) |
   | `EPOCHS`, `IMG_SIZE`, `BATCH_SIZE` | Hiperparámetros de entrenamiento |
   | `YOLO_BASE_MODEL` | Pesos base preentrenados (por defecto `yolov8n.pt`) |

4. Ejecuta el resto de celdas en orden. El notebook se detiene con un error explícito si
   la ruta configurada no existe.

---

## 5. Salidas generadas

Todo se guarda dentro de `WORK_DIR` (por defecto `/content/ccpd_yolo_proto`):

```
WORK_DIR/
├── images/{train,val,test}/       # imágenes de la muestra, ya en formato YOLO
├── labels/{train,val,test}/       # etiquetas YOLO (una .txt por imagen)
├── data.yaml                      # configuración del dataset para Ultralytics
├── manifest.csv                   # metadatos de cada imagen de la muestra (bbox, placa, etc.)
├── runs/ccpd_plate_detector/      # checkpoints y logs del entrenamiento (best.pt, results.png, ...)
├── placas_recortadas/             # ROIs recortados por el modelo entrenado
├── ejemplos_resultados.png        # panel de ejemplos visuales (predicción vs. ground truth)
└── resumen_metricas.json          # métricas finales, listas para citar en el reporte
```

---

## 6. Interpretación de resultados

El notebook compara automáticamente dos métricas contra las metas del proyecto:

- **Tasa de detección** (a IoU ≥ 0.75): debe acercarse a **RF-01 (≥ 95 %)**.
- **IoU promedio** en el conjunto de prueba: debe acercarse a **RF-02 (≥ 0.75)**.

Con `SAMPLE_SIZE = 3000` y pocas épocas, es normal que un primer prototipo no alcance
todavía ambas metas — el objetivo de esta etapa es validar el pipeline completo, no
entregar el modelo final del paquete 2.2. Para acercarse a las metas:

- Aumentar `SAMPLE_SIZE` (usar más imágenes de CCPD).
- Aumentar `EPOCHS`.
- Usar un modelo base más grande (`yolov8s.pt`, `yolov8m.pt`) si hay GPU disponible.

---

## 7. Siguientes pasos (fuera de este notebook)

1. Recolectar un **dataset local de placas mexicanas** en condiciones reales (cámaras IP,
   ángulos, clima) para cumplir RNF-02 y RF-03.
2. Hacer *fine-tuning* del detector con ese dataset local antes de considerarlo "validado"
   (entregable del paquete 2.2).
3. Construir el **módulo OCR** (paquete 2.3, RF-03), tomando como entrada las placas
   recortadas (`placas_recortadas/`) que genera este notebook.
4. Medir el tiempo de inferencia por frame en el dispositivo edge real (RF-05: ≤ 1.5 s/frame).

---

## 8. Referencias

- Xu, Z. et al. (2018). *Towards End-to-End License Plate Detection and Recognition: A
  Large Dataset and Baseline*. ECCV 2018.
- Repositorio oficial del dataset y formato de anotaciones:
  [github.com/detectRecog/CCPD](https://github.com/detectRecog/CCPD)
- [Ultralytics YOLO — Documentación](https://docs.ultralytics.com/)
