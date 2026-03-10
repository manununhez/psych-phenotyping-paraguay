# Guía de Notebooks

Este directorio contiene solo notebooks activos para reproducibilidad.

## Flujo operativo
1. `pipeline/01_datos_eda_limpieza.ipynb`
2. `pipeline/02_patient_level_split.ipynb`
3. `pipeline/03_denoising_reglas_core.ipynb`
4. `pipeline/04a_linea_base_dummy.ipynb`
5. `pipeline/04b_linea_base_tfidf.ipynb`
6. `pipeline/04c_linea_base_transformers.ipynb`
7. `pipeline/06_ingenieria_features_hibridas.ipynb`
8. `pipeline/07_entrenamiento_modelos_hibridos.ipynb`
9. `pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`

## Análisis (científico)
1. `analysis/05_brecha_lexica_co_core_py.ipynb`
2. `analysis/09_analisis_errores_hibrido.ipynb`

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
- 07: `data/processed/fe_<run_id>_{core,py}/features_{core,py}.parquet`.
- 08: `data/outputs/train_<run_id>/` con métricas, predicciones, figuras y modelos.
- 09: `data/outputs/results_<run_id>/` con tablas y figuras de comparación.
- 10: `data/outputs/error_analysis_<run_id>/` con resumen de errores y casos.