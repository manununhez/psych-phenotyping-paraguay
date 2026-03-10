# Fenotipado Psiquiátrico Paraguay

Repositorio de tesis para fenotipado psiquiátrico en notas clínicas IPS (Paraguay).

## Alcance científico congelado
- Sistema de reglas y lexicones congelados: `Concept_CO`, `Concept_PY`, `Concept_PY_Lexicon`.
- Arquitectura híbrida congelada: reglas + LLM semántico + `embeddings` BETO + sentimiento + `RandomForest` / `XGBoost`.
- Clases objetivo congeladas: `ansiedad`, `depresión`, `comorbilidad`.
- Split obligatorio: `patient-level split`.
- `late fusion` congelada: `feat_X = max(rule_X, llm_X)`.

## Estructura activa mínima
```text
.
├── notebooks/
│   ├── pipeline/
│   ├── analysis/
│   ├── appendix/
│   ├── README.md
│   └── utils_shared.py
├── scripts/
│   └── README.md
├── docs/
│   ├── GUIA_EJECUCION.md
│   ├── METODOLOGIA.md
│   ├── ESTRATEGIA_VALIDACION.md
│   └── LIMITACIONES.md
└── archivo/
    ├── documentacion_historica/
    ├── notebooks_legado/
    ├── notebooks_apendice/
    └── interno/
```

## Flujo operativo de notebooks
1. `notebooks/pipeline/01_datos_eda_limpieza.ipynb`
2. `notebooks/pipeline/02_patient_level_split.ipynb`
3. `notebooks/pipeline/03_denoising_reglas_core.ipynb`
4. `notebooks/pipeline/04a_linea_base_dummy.ipynb`
5. `notebooks/pipeline/04b_linea_base_tfidf.ipynb`
6. `notebooks/pipeline/04c_linea_base_transformers.ipynb`
7. `notebooks/analysis/05_brecha_lexica_co_core_py.ipynb`
8. `notebooks/pipeline/06_ingenieria_features_hibridas.ipynb`
9. `notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb`
10. `notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`
11. `notebooks/analysis/09_analisis_errores_hibrido.ipynb`

## Artefactos exportados clave
- Características híbridas: `data/processed/fe_<run_id>_{core,py}/features_{core,py}.parquet`.
- Entrenamiento: `data/outputs/train_<run_id>/comparacion_modelos_<split>.csv`, predicciones, figuras y modelos.
- Resultados consolidados: `data/outputs/results_<run_id>/tabla_comparativa_modelos.csv` y figuras.
- Análisis de errores: `data/outputs/error_analysis_<run_id>/`.

## Documentación activa
- Guía de ejecución: `docs/GUIA_EJECUCION.md`.
- Metodología: `docs/METODOLOGIA.md`.
- Validación clínica: `docs/ESTRATEGIA_VALIDACION.md`.
- Limitaciones: `docs/LIMITACIONES.md`.