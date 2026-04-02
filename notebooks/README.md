# Guía de Notebooks

Este directorio contiene solo notebooks activos para reproducibilidad.

## Flujo experimental principal
1. `pipeline/01_datos_eda_limpieza.ipynb`
2. `pipeline/02_patient_level_split.ipynb`
3. `pipeline/03_denoising_reglas_core.ipynb`
4. `pipeline/04a_linea_base_dummy.ipynb`
5. `pipeline/04b_linea_base_tfidf.ipynb`
6. `pipeline/04c_linea_base_transformers.ipynb`
7. `analysis/05_brecha_lexica_co_core_py.ipynb`
8. `pipeline/06_ingenieria_features_hibridas.ipynb`
9. `pipeline/07_entrenamiento_modelos_hibridos.ipynb`
10. `pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`
11. `pipeline/09b_cierre_modelos_dev.ipynb`
12. `analysis/09_analisis_errores_hibrido.ipynb`

## Fase clínica secundaria
1. `analysis/10_validacion_clinica_ips.ipynb`

Esta fase consume artefactos ya cerrados en `dev`; no redefine la shortlist ni la selección experimental.

## Análisis (científico)
1. `analysis/05_brecha_lexica_co_core_py.ipynb`
2. `analysis/09_analisis_errores_hibrido.ipynb`
3. `analysis/10_validacion_clinica_ips.ipynb`

## Alcance de esta fase
- Este flujo llega hasta cierre en `dev`.
- No incluye todavía notebook final de `test`.
- No incluye todavía notebook final de xAI/explicabilidad.

## Apéndice (solo soporte)
1. `appendix/A00_configuracion_entorno.ipynb`

## Convención obligatoria por notebook operativo
Cada notebook operativo declara al inicio:
- objetivo
- entradas
- salidas
- notebook anterior
- notebook siguiente
- técnicas, herramientas y librerías principales
- por qué esas herramientas son adecuadas en esta etapa y cuál sería la alternativa si no fueran la mejor opción

## Artefactos esperados por etapa
- 04c: `data/outputs/transformer_baseline_selection_<timestamp>.json` y `data/outputs/transformer_baseline_selection_latest.json`.
- 06: `data/processed/fe_<run_id>_{core,py}/features_{core,py}.parquet`.
- 07: `data/outputs/train_<run_id>/` con métricas, predicciones, figuras y modelos.
- 08: `data/outputs/results_<run_id>/` con tablas y figuras de comparación.
- 09b: `data/outputs/cierre_modelos_dev_<timestamp>/` con ranking, decisión y lista corta para `test`. Si no existe un barrido compatible con la corrida base actual, `09b` puede preparar automáticamente el barrido y regenerar el freeze léxico antes del cierre.
- 09 análisis: `data/outputs/error_analysis_<run_id>/` con resumen de errores y casos.
- 10 validación IPS: `data/outputs/material_validacion_ips_<timestamp>/` con preprocesamiento, balance, patrones por clase, comparación entre modelos, errores curados y preguntas para psiquiatras.
- Curación posterior al 10: `scripts/export/curar_dossier_ips.py` genera `data/outputs/dossier_ips_curado_<timestamp>/` como dossier reusable para revisión clínica externa y futura etapa de xAI.
- `analysis/10_validacion_clinica_ips.ipynb` funciona como capa legible y reutiliza scripts backend para generación reproducible de artefactos clínicos (`generar_material_validacion_ips.py`, `curar_dossier_ips.py`, `cerrar_fase_ips.py`).

## Flags clave para ablación
- 06 (`pipeline/06_ingenieria_features_hibridas.ipynb`):
  - `FE_USE_LLM = auto | 1 | 0`
  - `FE_COMPUTE_SENTIMENT = 1 | 0`
  - `FE_COMPUTE_CONTEXT = 1 | 0` (alias legacy: `FE_COMPUTE_BETO`)
  - `FE_TEXT_BACKBONE = auto | beto | roberta_clinical | roberta_biomedical`
  - `FE_RUN_ID`, `FE_CACHE_KEY`
- 07 (`pipeline/07_entrenamiento_modelos_hibridos.ipynb`):
  - `TRAIN_MODELS`, `TRAIN_PROFILES`, `TRAIN_SEED`, `TRAIN_EVAL_ON`
  - `TRAIN_FEATURE_RUN_BASE`, `TRAIN_FEATURE_RUN_ID_CORE`, `TRAIN_FEATURE_RUN_ID_PY`
  - `TRAIN_USE_LLM`, `TRAIN_USE_CONTEXT` (alias legacy: `TRAIN_USE_BETO`), `TRAIN_USE_TEMPLATE`
  - `TRAIN_USE_FEAT`, `TRAIN_USE_RULES`, `TRAIN_USE_MEDICATION`, `TRAIN_USE_SENTIMENT`
  - `TRAIN_DROP_COLUMNS`, `TRAIN_DROP_PREFIXES`, `TRAIN_KEEP_PREFIXES`

## Resolución por defecto de artefactos
- 07 resuelve la última corrida completa de features (`fe_*`) por mtime real, no por orden alfabético del nombre.
- 08 resuelve por defecto la última corrida base canónica `train_YYYYMMDD_HHMMSS`, evitando confundirse con corridas hijas del barrido.
- 09b busca un barrido compatible con la corrida base actual (`train_*` + `fe_*`) y, si no existe, puede generarlo automáticamente antes del cierre formal.

## Nota metodológica de backbone
- `04c` es la etapa explícita de selección del baseline Transformer en `dev`.
- `06` usa BETO por defecto para el híbrido, de acuerdo con la comparación controlada de backbone. Si se quiere heredar explícitamente la selección de `04c`, debe indicarse `FE_TEXT_BACKBONE=auto`.
- `04b` no interviene en esta decisión: `TF-IDF` es un baseline textual fuerte, pero no alimenta el bloque contextual `ctx_<backbone>_*`.

## Convención léxica canónica
- Capas:
  - `Concept_CO` = baseline histórico colombiano.
  - `Concept_Core` = núcleo clínico depurado.
  - `Concept_PY` = capa regional paraguaya.
- Perfiles:
  - `co` = `Concept_CO`
  - `core` = `Concept_Core`
  - `py` = `Concept_Core` + `Concept_PY`
