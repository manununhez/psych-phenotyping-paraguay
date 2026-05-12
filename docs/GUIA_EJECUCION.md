# Guía de ejecución (fase de desarrollo)

Esta guía cubre únicamente la regeneración hasta el cierre actual en `dev`.

No incluye:
- evaluación final en `test` (pendiente);
- notebook final de xAI/explicabilidad (pendiente; fuera del cierre técnico actual).

## Opción reproducible por contenedor

Si prefieres aislar dependencias del sistema host, puedes usar el contenedor del proyecto.

Scripts base:

```bash
bash scripts/docker_build.sh
bash scripts/docker_up.sh
CONTAINER_MODE=snapshot bash scripts/docker_up.sh
bash scripts/docker_smoke_test.sh
```

Si vas a usar Gemini desde el contenedor:

```bash
cp .env.docker.example .env.docker
```

Shell interactiva:

```bash
bash scripts/docker_shell.sh
```

Apagado:

```bash
bash scripts/docker_down.sh
```

Variables útiles:
- `CONTAINER_MODE=dev|snapshot`
- `CONTAINER_NAME=<nombre>`
- `IMAGE_NAME=<nombre>`
- `IMAGE_TAG=<tag>`

### Qué congela Docker y qué no

Docker congela:
- versión de Python de la imagen;
- dependencias Python declaradas;
- modelo spaCy base instalado en la imagen (`es_core_news_md`);
- utilidades del sistema necesarias para el pipeline.

Pero hay una diferencia operativa clave:
- `CONTAINER_MODE=dev` monta el repositorio local en `/workspace`, así que el código ejecutado es el de tu árbol actual;
- `CONTAINER_MODE=snapshot` usa el código copiado dentro de la imagen y solo monta `data/` si existe localmente.

Docker **no** congela por sí solo:
- datos clínicos reales;
- claves externas (`GEMINI_API_KEY`);
- artefactos locales de `data/outputs/` o `data/processed/`;
- caches remotas de Hugging Face descargadas después de construir la imagen.

### Inputs obligatorios

Para entender el contenedor correctamente:

1. **Siempre obligatorios**
   - código del repositorio;
   - submódulo `Spanish_Psych_Phenotyping_PY` inicializado.

2. **Obligatorios solo si se corre el pipeline desde 01**
   - `data/ips_raw.csv` disponible en el volumen local montado.

3. **Obligatorios solo si se ejecuta extracción LLM**
   - `.env.docker` con `GEMINI_API_KEY`, o variable equivalente pasada al contenedor.
   - Puedes partir de `.env.docker.example`.

4. **Obligatorios solo para reusar cierres previos**
   - artefactos locales ya generados en `data/processed/` y `data/outputs/`.

### Cuándo usar cada modo

- `CONTAINER_MODE=dev`
  - uso diario;
  - iteración local con código y notebooks vivos;
  - no congela el árbol fuente, solo el entorno.

- `CONTAINER_MODE=snapshot`
  - validación más cercana a un futuro repo público;
  - el código proviene de la imagen ya construida;
  - mantiene fuera de la imagen los datos clínicos y la caché de Hugging Face.

### Nota sobre BETO y otros modelos externos

El contenedor no empaqueta los pesos de `BETO`, `ROBERTA_CLINICAL` ni `ROBERTA_BIOMEDICAL`.

Eso significa:
- la lógica metodológica y los identificadores del backbone sí quedan congelados en código y notebooks;
- los pesos se descargarán desde Hugging Face cuando una corrida los necesite;
- la caché queda persistida localmente en `.docker_cache/huggingface/` para no descargar todo cada vez.

En otras palabras: Docker congela el **entorno de ejecución**, no los datos clínicos ni todos los artefactos pesados externos por defecto.

## Opción recomendada: script único

```bash
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
python scripts/audit/generar_auditoria_validacion_secundaria_dev.py
```

Wrapper bash opcional:

```bash
bash scripts/run_regeneracion_desarrollo.sh --dry-run
bash scripts/run_regeneracion_desarrollo.sh
```

## Ejecución parcial

```bash
python scripts/regenerar_pipeline_desarrollo.py --desde 06_ingenieria_features_hibridas --hasta 09b_cierre_modelos_dev
```

## Limpieza controlada de outputs

```bash
python scripts/regenerar_pipeline_desarrollo.py \
  --limpiar-outputs \
  --confirmar-limpieza \
  --dry-run
```

Para ejecutar limpieza real, quitar `--dry-run`.

## Salidas de la regeneración
Cada corrida deja:
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.md`
- `data/outputs/regeneracion_desarrollo_<timestamp>/resumen_regeneracion.json`
- logs por paso en `data/outputs/regeneracion_desarrollo_<timestamp>/logs/`.

## Orden operativo cubierto por la regeneración
1. `01_datos_eda_limpieza`
2. `02_patient_level_split`
3. `03_denoising_reglas_core`
4. `04a_linea_base_dummy`
5. `04b_linea_base_tfidf`
6. `04c_linea_base_transformers`
7. `05_brecha_lexica_co_core_py`
8. `06_ingenieria_features_hibridas`
9. `07_entrenamiento_modelos_hibridos`
10. `comparacion_backbones_hibrido` (si se activa `--incluir-comparacion-backbones`)
11. `08_resultados_hibrido_vs_lineas_base`
12. `barrido_hibrido_dev`
13. `freeze_lexico_preliminar`
14. `manifiesto_artefactos_backbone`
15. `09b_cierre_modelos_dev`
16. `09_analisis_errores_hibrido`

## Cierre dev vigente con ensamble 512
El cierre recomendado actual se formaliza en:

```bash
CIERRE_DEV_ENSAMBLE_RUN_ID=cierre_dev_ensamble_512_20260512_155606 \
jupyter nbconvert --to notebook --execute --inplace notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb

CIERRE_DEV_ENSAMBLE_RUN_ID=cierre_dev_ensamble_512_20260512_155606 \
jupyter nbconvert --to notebook --execute --inplace notebooks/analysis/09_analisis_errores_hibrido.ipynb
```

Artefactos principales:
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/manifest.json`
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/reporte_cierre_dev_ensamble.md`
- `data/outputs/cierre_dev_ensamble_512_20260512_155606/tabla_experimentos_dev_cierre.csv`

Este cierre usa `max_length=512`. Las corridas `max_length=256` quedan como sensibilidad no adoptada.

## Control secundario posterior
La auditoría secundaria pre-`test` se ejecuta después del cierre y del análisis de errores:

```bash
python scripts/audit/generar_auditoria_validacion_secundaria_dev.py
```

Este paso corresponde al notebook `notebooks/analysis/09c_auditoria_validacion_secundaria_dev.ipynb`. Consume artefactos congelados en `dev` y no reabre selección de modelo.

## Nota específica sobre backbone
- `04c` define y exporta la selección del baseline Transformer.
- `06` usa BETO por defecto para el híbrido, de acuerdo con la comparación controlada de backbone.
- Si se quiere probar una herencia explícita desde `04c`, debe indicarse `FE_TEXT_BACKBONE=auto`.
- `09b` utiliza la selección de `04c` y la comparación controlada de backbones (si existe artefacto válido) para fundamentar la decisión final en `dev`.

Cadena operativa recomendada:
`04c` -> `06` -> `07` -> `scripts/comparar_backbones_hibrido.py` -> `scripts/audit/registrar_artefactos_backbone.py` -> `09b`.

## Resolución automática en notebooks
- `07` resuelve por defecto la última corrida completa de features (`fe_*`) por mtime real y no por orden alfabético.
- `08` resuelve por defecto la última corrida base canónica `train_YYYYMMDD_HHMMSS`.
- `09b` busca un barrido compatible con la corrida base actual y, si no existe, puede preparar automáticamente:
  - `scripts/ejecutar_barrido_ablacion_hibrido.py`
  - `scripts/audit/generar_freeze_lexico.py`

Esto deja el flujo notebook-only alineado con la regeneración reproducible del proyecto.

## Nota metodológica
La regeneración está diseñada para reproducir el estado de desarrollo y su documentación de cierre en `dev`, sin mezclar decisiones de la fase final.
