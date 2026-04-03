# Metodología

## Qué resume este documento
Este archivo funciona como resumen ejecutivo de la metodología vigente. No intenta reemplazar la documentación detallada del repositorio; su función es fijar en una sola página qué problema se resuelve, qué invariantes rigen el experimento y qué decisiones estructurales ya quedaron cerradas.

Para el detalle completo del flujo usar:
- `docs/METODOLOGIA_PIPELINE_COMPLETA.md`
- `docs/METODOLOGIA_HIBRIDO_ABLACION_Y_CIERRE.md`
- `docs/ARTEFACTOS_Y_CONTRATOS.md`
- `docs/SPANISH_PSYCH_PHENOTYPING_PY.md`

## Objetivo experimental vigente
El proyecto implementa un pipeline reproducible para clasificar notas clínicas psiquiátricas en español de Paraguay entre dos etiquetas:

- `ansiedad`
- `depresion`

La salida es probabilística. En esta fase no se modela una clase explícita de `comorbilidad`, no se ejecuta todavía la evaluación final en `test` y la fase completa de xAI sigue pendiente.

## Invariantes metodológicos
Estas decisiones se tratan como congeladas:

- `patient-level split`;
- universo canónico de comparación en `dataset_denoised`;
- capas clínicas `Concept_CO`, `Concept_Core`, `Concept_PY`;
- perfiles:
  - `co` = `Concept_CO`
  - `core` = `Concept_Core`
  - `py` = `Concept_Core` + `Concept_PY`
- `late fusion` restringida a síntomas:
  - `feat_X = max(rule_X, llm_X)`
- `rule_medication_*` como evidencia terapéutica separada.

## Secuencia metodológica
La lógica del experimento sigue esta cadena:

1. limpieza inicial del corpus;
2. split congelado por paciente;
3. denoising clínico para definir el universo modelado;
4. líneas base oficiales sobre ese mismo universo;
5. auditoría de brecha léxica y fijación de perfiles clínicos;
6. construcción de la matriz híbrida de features;
7. entrenamiento tabular y comparación `RF/XGB`;
8. comparación controlada de backbone del híbrido;
9. barrido, ablación y estabilidad multi-seed;
10. freeze léxico;
11. cierre formal del mejor modelo en `dev`;
12. análisis de errores del modelo congelado.

## Rol del LLM
El LLM se usa de manera acotada para:

1. normalización semántica de síntomas;
2. apoyo de auditoría léxica.

No se usa como clasificador clínico directo ni como generador libre de nuevas categorías diagnósticas.

## Separación clave: standalone vs backbone del híbrido
El proyecto separa dos decisiones que no deben mezclarse:

- `04c` decide el mejor transformer standalone en `dev`.
- `scripts/comparar_backbones_hibrido.py` decide qué backbone contextual conviene dentro del híbrido manteniendo fijo el resto.

En la corrida vigente:
- mejor transformer standalone: `ROBERTA_CLINICAL`
- mejor backbone del híbrido: `BETO`

Por eso `06` usa `BETO` por defecto para construir `ctx_<backbone>_*`. Si se quiere heredar explícitamente la selección de `04c`, debe indicarse `FE_TEXT_BACKBONE=auto`.

## Criterio de evaluación del híbrido
La familia híbrida no se cierra por una sola métrica. El cierre en `dev` combina:

- `macro_f1`;
- `balanced_accuracy`;
- F1 por clase;
- estabilidad entre seeds;
- parsimonia;
- auditabilidad clínica;
- penalización de riesgos metodológicos;
- consistencia entre backbone, barrido, freeze y análisis de errores.

## Estado actual de la fase
El repositorio está cerrado metodológicamente en `dev`:

- selección y comparación de líneas base;
- backbone del híbrido resuelto;
- barrido y ablación ejecutados;
- freeze léxico generado;
- modelo final congelado en `09b`.

Quedan pendientes:
- evaluación final en `test`;
- fase completa de xAI/explicabilidad.
