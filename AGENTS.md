# AGENTS.md

## Propósito del proyecto
Este repositorio implementa un pipeline reproducible para fenotipado psiquiátrico en notas clínicas en español de Paraguay. El objetivo final es clasificar tres clases diagnósticas: ansiedad, depresión y comorbilidad.

## Principios que no deben modificarse
Los siguientes elementos se consideran congelados y no deben alterarse sin una decisión metodológica explícita:

- `Concept_CO` como baseline histórico.
- `Concept_PY (Core)` como núcleo clínico depurado.
- `Concept_PY_Lexicon` como adaptación paraguaya.
- uso de `late fusion` solo para síntomas:
  - `feat_X = max(rule_X, llm_X)`
- conservación de `rule_medication_*` como evidencia terapéutica separada.
- target final: diagnóstico (`ansiedad`, `depresión`, `comorbilidad`).

## Idioma y estilo
Todo comentario, encabezado, título, documento y nombre de archivo debe estar en español, salvo términos técnicos o métodos que sea razonable mantener en inglés, por ejemplo:

- TF-IDF
- RandomForest
- XGBoost
- embeddings
- late fusion
- patient-level split
- BETO

No agregar documentación redundante. Si un documento no aporta a reproducibilidad, comprensión o redacción de tesis, debe eliminarse o archivarse.

## Flujo activo del proyecto
Orden oficial de ejecución:

1. `notebooks/pipeline/01_datos_eda_limpieza.ipynb`
2. `notebooks/pipeline/02_split_por_paciente.ipynb`
3. `notebooks/pipeline/03_denoising_reglas_core.ipynb`
4. `notebooks/pipeline/04a_linea_base_dummy.ipynb`
5. `notebooks/pipeline/04b_linea_base_tfidf.ipynb`
6. `notebooks/pipeline/04c_linea_base_transformers.ipynb`
7. `notebooks/analysis/06_brecha_lexica_co_core_py.ipynb`
8. `notebooks/pipeline/07_ingenieria_features_hibridas.ipynb`
9. `notebooks/pipeline/08_entrenamiento_modelos_hibridos.ipynb`
10. `notebooks/pipeline/09_resultados_hibrido_vs_lineas_base.ipynb`
11. `notebooks/analysis/10_analisis_errores_hibrido.ipynb`

## Contrato entre notebooks
Cada notebook debe declarar claramente:

- objetivo
- inputs
- outputs
- notebook anterior
- notebook siguiente

### Dependencias clave
- `03` genera el dataset denoised consumido en etapas posteriores.
- `04c` justifica el uso de BETO como baseline contextual fuerte.
- `06` justifica la transición `Concept_CO -> Concept_PY -> Concept_PY_Lexicon`.
- `07` reutiliza BETO y construye `feat_*`, `feat_niega_*`, `rule_medication_*`, `sent_*`, `beto_*`.
- `08` consume únicamente la salida final de `07`.
- `09` consolida resultados exportados por `08`.
- `10` consume salidas de `08` y `09` para análisis de errores.

## Rol del LLM
El LLM solo puede usarse para:

1. normalización semántica de síntomas;
2. apoyo durante la auditoría léxica.

No debe usarse como clasificador clínico directo.

### Restricciones
- no expandir libremente el espacio de features con etiquetas generadas por LLM;
- no fusionar diagnóstico a partir de medicación detectada por LLM;
- las detecciones de medicación del LLM se usan para auditoría, apoyo léxico y verificación semántica.

## Documentación activa mínima
Los documentos activos del proyecto deben limitarse a:

- `README.md`
- `notebooks/README.md`
- `scripts/README.md`
- `docs/README.md`
- `docs/GUIA_EJECUCION.md`
- `docs/METODOLOGIA.md`
- `docs/ESTRATEGIA_VALIDACION.md`
- `docs/LIMITACIONES.md`

Todo documento histórico o redundante debe moverse a `archivo/`.

## Scripts
Estructura esperada:

- `scripts/llm/`
- `scripts/audit/`
- `scripts/export/`
- `scripts/devtools/`

Los scripts deben tener rutas portables y, cuando corresponda, interfaz CLI.

## Artefactos y outputs
Cada notebook operativo debe exportar artefactos útiles para tesis/paper. Como mínimo:

- tablas CSV
- figuras
- resúmenes JSON/CSV
- archivos de predicción o errores cuando corresponda

Los outputs no deben mezclarse con código fuente ni documentación activa.

## Qué revisar antes de aceptar cambios
Antes de aprobar una modificación, verificar:

1. que no rompa el orden oficial del pipeline;
2. que no cambie la ontología congelada;
3. que no introduzca documentación repetida;
4. que mantenga reproducibilidad;
5. que deje clara la relación entre resultados de líneas base y decisiones posteriores.

## Pendientes metodológicos
Mantener presentes estos pendientes para etapas posteriores:

- generar un compendio `.md` para NotebookLM con decisiones y narrativa metodológica;
- redactar la sección de metodología de tesis/paper;
- documentar de forma clara:
  - la brecha léxica,
  - la limpieza de Core,
  - la construcción de `PY_Lexicon`,
  - el rol del LLM en auditoría léxica,
  - la justificación de BETO como baseline y componente del híbrido.
