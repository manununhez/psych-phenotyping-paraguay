# Guía de Notebooks

Este directorio contiene solo notebooks activos para reproducibilidad.

## Flujo operativo
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

## Análisis (científico)
1. `analysis/05_brecha_lexica_co_core_py.ipynb`
2. `analysis/09_analisis_errores_hibrido.ipynb`

## Alcance de esta fase
- Este flujo llega hasta cierre en `dev`.
- No incluye todavía notebook final de `test`.
- No incluye todavía notebook final de xAI/explicabilidad.

## Apéndice (solo soporte)
1. `appendix/A00_configuracion_entorno.ipynb`
2. `appendix/A01_muestreo_validacion_psiquiatrica.ipynb`

## Convención obligatoria por notebook operativo
Cada notebook operativo declara al inicio:
- objetivo
- entradas
- salidas
- notebook anterior
- notebook siguiente

## Artefactos esperados por etapa
- 06: `data/processed/fe_<run_id>_{core,py}/features_{core,py}.parquet`.
- 07: `data/outputs/train_<run_id>/` con métricas, predicciones, figuras y modelos.
- 08: `data/outputs/results_<run_id>/` con tablas y figuras de comparación.
- 09b: `data/outputs/cierre_modelos_dev_<timestamp>/` con ranking, decisión y lista corta para `test`.
- 09 análisis: `data/outputs/error_analysis_<run_id>/` con resumen de errores y casos.

## Flags clave para ablación
- 06 (`pipeline/06_ingenieria_features_hibridas.ipynb`):
  - `FE_USE_LLM = auto | 1 | 0`
  - `FE_COMPUTE_SENTIMENT = 1 | 0`
  - `FE_COMPUTE_BETO = 1 | 0`
  - `FE_RUN_ID`, `FE_CACHE_KEY`
- 07 (`pipeline/07_entrenamiento_modelos_hibridos.ipynb`):
  - `TRAIN_MODELS`, `TRAIN_PROFILES`, `TRAIN_SEED`, `TRAIN_EVAL_ON`
  - `TRAIN_USE_LLM`, `TRAIN_USE_BETO`, `TRAIN_USE_TEMPLATE`
  - `TRAIN_USE_FEAT`, `TRAIN_USE_RULES`, `TRAIN_USE_MEDICATION`, `TRAIN_USE_SENTIMENT`
  - `TRAIN_DROP_COLUMNS`, `TRAIN_DROP_PREFIXES`, `TRAIN_KEEP_PREFIXES`
