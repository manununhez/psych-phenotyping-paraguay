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

La salida es probabilística. En esta fase no se modela una clase explícita de `comorbilidad`, no se ejecuta todavía la evaluación final en `test` y la explicabilidad final queda fuera del cierre técnico actual.

## Cierre dev vigente
El cierre técnico vigente en `dev` es un ensamble por ramas con `max_length=512`:

- rama contextual: `ROBERTA_CLINICAL` standalone, `hidden_size=768`, salida probabilística por clase;
- rama simbólica regionalizada: `Concept_Core + Concept_PY` con `RandomForest`;
- rama simbólica core con late fusion LLM: `RandomForest`;
- combinación: weighted soft voting con pesos `0.80 / 0.10 / 0.10`.

Resultado principal en `dev`:

| Modelo | Macro F1 | Balanced accuracy | Weighted F1 | F1 ansiedad | F1 depresión |
|---|---:|---:|---:|---:|---:|
| Ensamble weighted soft 512 | `0.749250` | `0.770062` | `0.784909` | `0.663717` | `0.834783` |
| `ROBERTA_CLINICAL` 512 | `0.741078` | `0.763889` | `0.776955` | `0.655022` | `0.827133` |
| Híbrido tabular 512 `py XGB` | `0.723387` | `0.717099` | `0.774828` | `0.600000` | `0.846774` |

El cierre híbrido tabular previo se conserva como referencia histórica/comparativa. La configuración `max_length=256` queda documentada como sensibilidad no adoptada.

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
11. cierre formal del ensamble por ramas en `dev`;
12. análisis de errores del modelo recomendado;
13. auditoría secundaria pre-`test` en `dev` cuando corresponda (`09c`).

## Rol del LLM
El LLM se usa de manera acotada para:

1. normalización semántica de síntomas;
2. apoyo de auditoría léxica.

No se usa como clasificador clínico directo ni como generador libre de nuevas categorías diagnósticas.

## Señal clínica útil, `keep_entity` y negación
El denoising no se define por una lista ad hoc de notas "buenas" y "malas". Se apoya en una política explícita de aseveración clínica implementada en `utils_shared.keep_entity`.

La regla práctica es esta:

- una mención se conserva como señal clínica útil si no está en contexto histórico, hipotético ni familiar;
- una mención afirmada se conserva como evidencia válida;
- una mención negada solo se conserva si la negación es atribuible al paciente;
- la negación de plantilla, del médico o de una fórmula administrativa se descarta como señal diagnóstica útil.

De esa política salen dos piezas centrales del pipeline:

- `has_clinical_signal = 1`: la nota conserva al menos una entidad válida para la tarea diferencial;
- `niega_*`: la negación del paciente se preserva como señal clínica específica y no como simple ausencia de fenómeno.

Esto debe leerse correctamente: no es una decisión diagnóstica final, sino una política de limpieza y normalización del EHR para evitar que el modelo aprenda ruido documental como si fuera evidencia clínica.

## Separación clave: standalone vs backbone del híbrido
El proyecto separa dos decisiones que no deben mezclarse:

- `04c` decide el mejor transformer standalone en `dev`.
- `scripts/comparar_backbones_hibrido.py` decide qué backbone contextual conviene dentro del híbrido manteniendo fijo el resto.

En la corrida vigente:
- mejor transformer standalone: `ROBERTA_CLINICAL`
- mejor backbone del híbrido: `BETO`

Por eso `06` usa `BETO` por defecto para construir `ctx_<backbone>_*` en el híbrido tabular. El ensamble vigente, en cambio, usa `ROBERTA_CLINICAL` como rama contextual porque combina predicciones probabilísticas de ramas independientes. Si se quiere heredar explícitamente la selección de `04c` dentro de `06`, debe indicarse `FE_TEXT_BACKBONE=auto`.

## Criterio de evaluación del cierre dev
El cierre en `dev` no se decide por una sola métrica. La decisión combina:

- `macro_f1`;
- `balanced_accuracy`;
- F1 por clase;
- estabilidad entre seeds;
- parsimonia;
- auditabilidad clínica;
- penalización de riesgos metodológicos;
- consistencia entre backbone, barrido, freeze y análisis de errores.

## Estado actual de la fase
El repositorio está cerrado metodológicamente en `dev` con ensamble por ramas:

- selección y comparación de líneas base;
- backbone del híbrido resuelto;
- híbrido tabular reejecutado como comparativo 512;
- ensamble por ramas formalizado;
- freeze léxico generado;
- análisis de errores del ensamble ejecutado;
- `test` sigue virgen.

Quedan pendientes:
- evaluación final en `test`;
- integración final de xAI/explicabilidad y repetición de análisis secundarios cuando se abra `test`, si la dirección metodológica lo aprueba.

## Validación secundaria en `dev`
La lectura principal del proyecto sigue siendo el cierre metodológico en `dev`, pero la auditoría secundaria añade controles necesarios antes de abrir `test`:

| Modelo | Macro F1 note-level | Macro F1 patient-weighted | Macro F1 patient-aggregated | AP ansiedad |
|---|---:|---:|---:|---:|
| `TF-IDF` | `0.740564` | `0.751384` | `0.887500` | `0.725725` |
| `ROBERTA_CLINICAL` | `0.741078` | `0.768400` | `0.828571` | `0.655111` |
| híbrido final `py|XGB` | `0.728894` | `0.692788` | `0.750000` | `0.589144` |

Estos controles no reabren la selección del modelo. Su función es reforzar la interpretación: TF-IDF y ROBERTA_CLINICAL son referencias predictivas muy fuertes, mientras que el híbrido retenido se conserva por trazabilidad clínica, parsimonia y valor metodológico dentro de una shortlist heterogénea.

También se ejecutó una sensibilidad con `sample_weight = 1 / n_notas_paciente_train`. El efecto fue negativo en `dev`, por lo que no se adopta como nuevo cierre ni como reemplazo del modelo congelado.
