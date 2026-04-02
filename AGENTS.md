# AGENTS.md

## Propósito
Este repositorio implementa un pipeline reproducible de fenotipado psiquiátrico sobre notas clínicas en español de Paraguay. El objetivo experimental vigente es la clasificación probabilística binaria entre `ansiedad` y `depresion`.

## Dependencia clínica
`Spanish_Psych_Phenotyping_PY/` es un submódulo versionado y debe tratarse como dependencia reproducible del proyecto, no como contenido accidental del árbol.

## Invariantes metodológicos
No modificar sin una decisión metodológica explícita:

- `Concept_CO` como baseline histórico;
- `Concept_Core` como núcleo clínico depurado;
- `Concept_PY` como adaptación regional paraguaya;
- perfiles:
  - `co` = `Concept_CO`
  - `core` = `Concept_Core`
  - `py` = `Concept_Core` + `Concept_PY`
- `patient-level split`;
- `late fusion` restringido a síntomas:
  - `feat_X = max(rule_X, llm_X)`
- `rule_medication_*` como evidencia terapéutica separada;
- target actual:
  - `ansiedad`
  - `depresion`

## Rol del LLM
Uso permitido:

1. normalización semántica de síntomas;
2. apoyo de auditoría léxica.

No usar el LLM como clasificador clínico directo ni como fuente para expandir libremente el espacio de features diagnósticas.

## Flujo principal
Orden oficial del experimento:

1. `notebooks/pipeline/01_datos_eda_limpieza.ipynb`
2. `notebooks/pipeline/02_patient_level_split.ipynb`
3. `notebooks/pipeline/03_denoising_reglas_core.ipynb`
4. `notebooks/pipeline/04a_linea_base_dummy.ipynb`
5. `notebooks/pipeline/04b_linea_base_tfidf.ipynb`
6. `notebooks/pipeline/04c_linea_base_transformers.ipynb`
7. `notebooks/analysis/05_brecha_lexica_co_core_py.ipynb`
8. `notebooks/pipeline/06_ingenieria_features_hibridas.ipynb`
9. `notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb`
10. `scripts/comparar_backbones_hibrido.py`
11. `notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`
12. `notebooks/pipeline/09b_cierre_modelos_dev.ipynb`
13. `notebooks/analysis/09_analisis_errores_hibrido.ipynb`

Fase secundaria opcional:

14. `notebooks/analysis/10_validacion_clinica_ips.ipynb`

## Contrato entre etapas
- `03` define el universo final modelado y produce `data/input_for_gemini.json`.
- `04c` selecciona el mejor transformer standalone en `dev`.
- `06` construye `feat_*`, `feat_niega_*`, `rule_medication_*`, `sent_*` y `ctx_<backbone>_*`.
- `07` consume únicamente la salida final de `06`.
- `08` consolida líneas base y modelos híbridos.
- `09b` congela la decisión formal en `dev`.
- `09` analiza errores del modelo final congelado.
- `scripts/comparar_backbones_hibrido.py` resuelve la comparación controlada de backbone del híbrido.

## Backbone contextual
- `04c` decide el mejor transformer standalone.
- `06` usa `BETO` por defecto para el híbrido porque la comparación controlada de backbone vigente retuvo `BETO`.
- Si se quiere heredar explícitamente la selección de `04c`, usar `FE_TEXT_BACKBONE=auto`.
- `04b` no interviene en esta decisión.

## Documentación pública mínima
Mantener como frente público principal:

- `README.md`
- `AGENTS.md`
- `notebooks/README.md`
- `scripts/README.md`
- `docs/README.md`
- `docs/GUIA_EJECUCION.md`
- `docs/METODOLOGIA.md`
- `docs/LIMITACIONES.md`
- `docs/ESTRATEGIA_VALIDACION.md`
- `docs/DECISIONES_METODOLOGICAS_CLAVE.md`
- `docs/REVALIDACION_RESULTADOS_REFERENCIA.md`

El material interno, histórico o circunstancial debe quedar fuera del frente público o archivado localmente.

## Estilo y edición
- Escribir en español, salvo términos técnicos razonables en inglés.
- No duplicar documentación.
- No mezclar outputs locales con código fuente ni documentación pública.
- Si una modificación cambia resultados o selección metodológica, dejar trazabilidad explícita en código o documentación pública.

## Verificaciones antes de aceptar cambios
1. no romper el orden del pipeline;
2. no cambiar la ontología congelada;
3. mantener reproducibilidad;
4. dejar clara la relación entre líneas base, backbone y cierre final;
5. no reintroducir documentación interna en la capa pública.
