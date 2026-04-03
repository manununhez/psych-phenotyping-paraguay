# Metodología Completa Del Pipeline

## Propósito de este documento
Este documento describe de forma integral cómo funciona el proyecto, qué problema resuelve, qué decisiones metodológicas toma y cómo se conectan entre sí notebooks, scripts y artefactos. Su objetivo es que una persona pueda entender el experimento sin abrir los notebooks ni reconstruir el flujo a partir del código.

## Qué hace el proyecto
El proyecto implementa un pipeline reproducible para clasificar notas clínicas psiquiátricas en español de Paraguay entre dos etiquetas:

- `ansiedad`
- `depresion`

La salida es probabilística y el diseño busca equilibrar:

- rendimiento predictivo;
- trazabilidad clínica;
- reproducibilidad experimental.

## Qué no hace el proyecto en su estado actual
Este repositorio no resuelve todavía:

- evaluación final en `test`;
- una fase formal de xAI o explicabilidad completa;
- una formulación multiclase o multilabel;
- una clase explícita de `comorbilidad`;
- un grupo de control como parte del pipeline vigente.

## Idea metodológica central
La estrategia del proyecto no consiste en aplicar un clasificador sobre texto crudo sin más. El problema se trata como una secuencia de decisiones metodológicas encadenadas:

1. limpiar y estabilizar el corpus;
2. congelar una partición por paciente;
3. definir un universo modelado clínicamente más coherente mediante denoising;
4. comparar líneas base fuertes sobre ese mismo universo;
5. justificar y construir una arquitectura léxica adaptada al español clínico paraguayo;
6. transformar el texto en una matriz híbrida de evidencia clínica, contextual y auxiliar;
7. entrenar variantes comparables del híbrido;
8. aislar la decisión del backbone contextual del híbrido;
9. explorar ablaciones y estabilidad;
10. cerrar formalmente la selección en `dev` con una rúbrica multicriterio;
11. analizar errores del modelo congelado;
12. preparar, como fase secundaria, material para revisión clínica externa y futura xAI.

## Restricciones metodológicas congeladas
Estos elementos se tratan como invariantes del proyecto y no deben alterarse sin una decisión metodológica explícita:

- `Concept_CO` como baseline histórico;
- `Concept_Core` como núcleo clínico depurado;
- `Concept_PY` como capa regional paraguaya;
- `patient-level split` como política de partición experimental;
- regla de `late fusion` restringida al espacio sintomático:
  - `feat_X = max(rule_X, llm_X)`;
- conservación de `rule_medication_*` como evidencia terapéutica separada;
- target binario actual: `ansiedad` vs `depresion`.

## Estructura conceptual del sistema
El proyecto organiza la señal clínica en cuatro capas principales.

### 1. Capa documental y de universo
Define qué registros existen, cómo se limpian y cuáles realmente entran al problema modelado.

### 2. Capa léxica y clínica
Organiza reglas y patrones sobre tres niveles:

- `Concept_CO`: baseline histórico;
- `Concept_Core`: depuración clínica portable;
- `Concept_PY`: adaptación regional paraguaya.

### 3. Capa híbrida de features
Construye familias separadas de evidencia:

- `rule_*`: reglas clínicas directas;
- `feat_*`: señal sintomática fusionada con apoyo semántico acotado;
- `feat_niega_*`: negación de síntomas;
- `rule_medication_*`: evidencia terapéutica separada;
- `sent_*`: sentimiento opcional;
- `ctx_<backbone>_*`: embeddings contextuales.

### 4. Capa de decisión experimental
Compara líneas base, resuelve backbone, explora ablaciones, congela el mejor modelo en `dev` y deja una shortlist para `test`.

## Diferencia entre universos del corpus
El repositorio trabaja con varios niveles del corpus, y esa distinción es crucial para entender las comparaciones.

### `ips_raw.csv`
Es el universo original extraído. Sirve como punto de partida y trazabilidad del volumen bruto, pero no se usa directamente como espacio canónico de evaluación de modelos.

### `ips_clean.csv`
Es la versión limpia inicial tras normalización documental básica y preparación del texto.

### `dataset_base.csv`
Es el universo deduplicado y ya particionado por paciente. Conserva más volumen que el universo final modelado y sigue siendo útil para auditorías y comparación léxica.

### `dataset_denoised.csv`
Es el universo finalmente modelado por el pipeline principal. Aquí se descarta parte del ruido administrativo o clínicamente poco útil para la tarea diferencial.

## Por qué el proyecto no compara el modelo final contra texto crudo
El pipeline principal no usa `ips_raw.csv` para las líneas base oficiales. Las comparaciones canónicas se hacen sobre el universo `denoised`, porque ese es el espacio experimental que el proyecto considera más coherente para una tarea diferencial entre ansiedad y depresión.

Existe un contraste secundario `crudo vs filtrado`, pero su rol es metodológico: justificar el denoising, no redefinir el ranking principal de modelos.

## Flujo oficial del proyecto
El flujo oficial se divide en dos capas:

- pipeline experimental principal: `01–09`;
- módulo secundario de revisión clínica externa: `10`.

### Pipeline experimental principal
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
12. `scripts/ejecutar_barrido_ablacion_hibrido.py`
13. `scripts/audit/generar_freeze_lexico.py`
14. `scripts/audit/registrar_artefactos_backbone.py`
15. `notebooks/pipeline/09b_cierre_modelos_dev.ipynb`
16. `notebooks/analysis/09_analisis_errores_hibrido.ipynb`

### Módulo secundario
17. `notebooks/analysis/10_validacion_clinica_ips.ipynb`

## Qué resuelve cada etapa

### 01. `01_datos_eda_limpieza.ipynb`
**Qué hace**
Limpia el archivo original `ips_raw.csv`, normaliza columnas y prepara la base textual inicial.

**Qué decide**
Define la versión limpia inicial del corpus que se tomará como punto de partida operativo.

**Cómo lo hace**
- carga el bruto original;
- revisa consistencia mínima del texto;
- normaliza estructura y formato;
- exporta `ips_clean.csv`.

**Por qué es importante**
Separa el problema de extracción y consistencia documental del problema de modelado.

**Artefacto principal**
- `data/ips_clean.csv`

### 02. `02_patient_level_split.ipynb`
**Qué hace**
Construye la partición experimental `train/dev/test` a nivel de paciente.

**Qué decide**
Congela el split oficial del proyecto y evita leakage longitudinal entre notas del mismo paciente.

**Cómo lo hace**
- carga `ips_clean.csv`;
- genera particiones estrictas por `patient_id`;
- exporta índices y `dataset_base.csv`.

**Por qué es importante**
Cualquier comparación posterior depende de esta decisión. Si el split cambia, ya no se está evaluando el mismo experimento.

**Artefactos principales**
- `data/splits/dataset_base.csv`
- `data/splits/train_indices.csv`
- `data/splits/dev_indices.csv`
- `data/splits/test_indices.csv`

### 03. `03_denoising_reglas_core.ipynb`
**Qué hace**
Aplica un denoising clínico rule-based para retirar ruido administrativo y conservar señal clínica relevante.

**Qué decide**
Define el universo final modelado del proyecto.

**Cómo lo hace**
- usa `dataset_base.csv` y los índices por split;
- ejecuta lógica clínica basada en el submódulo `Spanish_Psych_Phenotyping_PY/`;
- filtra notas con baja utilidad para la tarea diferencial;
- exporta datasets denoised por split y un dataset consolidado;
- prepara `input_for_gemini.json` para extracción semántica posterior.

**Por qué es importante**
El proyecto no trata el denoising como un adorno. Es la decisión que vuelve comparable y clínicamente defendible el universo sobre el cual luego se entrenan y comparan los modelos.

**Artefactos principales**
- `data/splits/train_denoised.csv`
- `data/splits/dev_denoised.csv`
- `data/splits/test_denoised.csv`
- `data/dataset_denoised.csv`
- `data/input_for_gemini.json`

### 04a. `04a_linea_base_dummy.ipynb`
**Qué hace**
Calcula un baseline mínimo para verificar que el problema es aprendible.

**Qué decide**
No decide arquitectura; fija el piso trivial del problema.

**Cómo lo hace**
- entrena sobre `train_denoised.csv`;
- evalúa sobre el mismo universo denoised del híbrido;
- exporta métricas y predicciones.

**Por qué es importante**
Evita interpretar cualquier resultado superior al azar como si fuera automáticamente significativo.

### 04b. `04b_linea_base_tfidf.ipynb`
**Qué hace**
Entrena un baseline textual lexical-estadístico con `TF-IDF`.

**Qué decide**
Establece la referencia fuerte simple sobre texto clínico.

**Cómo lo hace**
- usa `train_denoised.csv` y `<split>_denoised.csv`;
- vectoriza texto con `TF-IDF`;
- entrena un clasificador lineal;
- exporta métricas, reporte y predicciones.

**Por qué es importante**
`TF-IDF` funciona como control fuerte, barato e interpretable. En este proyecto no es un baseline decorativo: es una referencia competitiva real.

**Qué no hace**
No alimenta la arquitectura híbrida. Su rol es comparativo, no estructural.

### 04c. `04c_linea_base_transformers.ipynb`
**Qué hace**
Compara los baselines Transformer standalone en `dev`.

**Qué decide**
Resuelve cuál es el mejor transformer standalone vigente.

**Cómo lo hace**
- usa el mismo universo `denoised` que las líneas base y el híbrido;
- compara `BETO`, `ROBERTA_CLINICAL` y, cuando corresponde, `ROBERTA_BIOMEDICAL`;
- exporta métricas por modelo y un artefacto de selección explícita.

**Por qué es importante**
Responde a una pregunta metodológica específica: cuál es la mejor referencia contextual aislada. Esa pregunta no es la misma que decidir el backbone del híbrido.

**Decisión actual retenida**
- mejor transformer standalone: `ROBERTA_CLINICAL`

**Artefactos principales**
- `data/outputs/transformer_baseline_selection_<timestamp>.json`
- `data/outputs/transformer_baseline_selection_latest.json`

### 05. `05_brecha_lexica_co_core_py.ipynb`
**Qué hace**
Justifica la transición `Concept_CO -> Concept_Core -> Concept_PY`.

**Qué decide**
No decide el modelo final, pero sí consolida la lógica clínica y lingüística del recurso léxico que sostiene el resto del pipeline.

**Cómo lo hace**
- compara perfiles `co`, `core` y `py`;
- analiza cobertura, ruido y necesidad de adaptación regional;
- puede usar `gemini_extraction.json` como apoyo para auditoría léxica, no como sustituto de reglas.

**Por qué es importante**
Explica por qué el proyecto no reutiliza un léxico histórico sin adaptación local.

### 06. `06_ingenieria_features_hibridas.ipynb`
**Qué hace**
Construye la matriz final de features del sistema híbrido.

**Qué decide**
Resuelve cómo se representan las distintas familias de evidencia que luego consumirá el entrenamiento tabular.

**Cómo lo hace**
- carga `dataset_denoised.csv`;
- integra reglas clínicas, negación, medicación, sentimiento y contexto;
- usa `gemini_extraction.json` solo para apoyo semántico acotado en síntomas;
- exporta features separadas para perfil `core` y `py`.

**Decisión metodológica crítica**
`06` usa `BETO` por defecto como backbone contextual del híbrido.

**Por qué**
Porque la comparación controlada de backbone del híbrido retuvo `BETO`, y esa decisión es distinta de la selección standalone de `04c`.

**Cómo se resuelve la tensión con `04c`**
- `04c` responde: cuál es el mejor transformer standalone.
- comparación controlada de backbone responde: qué modelo conviene dentro del híbrido.
- por eso `FE_TEXT_BACKBONE=auto` existe, pero solo como override explícito;
- no es el comportamiento por defecto.

**Qué no hace**
No consume `TF-IDF` como bloque estructural. `04b` no interviene en la construcción del híbrido.

**Artefactos principales**
- `data/processed/fe_<run_id>_core/features_core.parquet`
- `data/processed/fe_<run_id>_py/features_py.parquet`
- `*_feature_summary.csv`
- `*_config.json`

### 07. `07_entrenamiento_modelos_hibridos.ipynb`
**Qué hace**
Entrena variantes tabulares del híbrido con las features generadas por `06`.

**Qué decide**
Produce las corridas base de híbridos comparables sobre las que luego se consolidan resultados y se prepara el cierre.

**Cómo lo hace**
- consume `features_core.parquet` y `features_py.parquet`;
- entrena `RandomForest` y `XGBoost`;
- activa o apaga familias de features mediante flags de ablación;
- exporta modelos, métricas, figuras, predicciones y resúmenes.

**Por qué es importante**
Esta etapa traduce la arquitectura conceptual del híbrido en experimentos comparables y reproducibles.

**Decisión práctica relevante**
`07` hoy resuelve por defecto la última corrida completa de features por tiempo real (`mtime`), no por orden alfabético. Ese ajuste fue necesario para que notebook-only y reruns reproduzcan la corrida correcta.

### Script. `scripts/comparar_backbones_hibrido.py`
**Qué hace**
Ejecuta una comparación controlada del backbone contextual dentro del híbrido.

**Qué decide**
Resuelve el mejor backbone del híbrido manteniendo fija la arquitectura alrededor.

**Cómo lo hace**
- convierte `06` y `07` a scripts temporales;
- fuerza un escenario fijo:
  - perfil `py`;
  - modelo `XGB`;
  - `llm=0`;
  - `sentiment=0`;
  - `template=0`;
  - `feat=0`;
  - `rules=1`;
  - `medication=0`;
  - `context=1`;
- corre el mismo setup cambiando solo el backbone.

**Por qué es importante**
Aísla la decisión del backbone sin mezclarla con el resto de los bloques del híbrido.

**Decisión actual retenida**
- mejor backbone del híbrido: `BETO`

### 08. `08_resultados_hibrido_vs_lineas_base.ipynb`
**Qué hace**
Consolida resultados comparables entre líneas base e híbridos.

**Qué decide**
No decide el ganador final, pero prepara la base cuantitativa sobre la que luego se apoya el cierre formal.

**Cómo lo hace**
- reúne `*_eval.csv` de baselines;
- consume la corrida base `train_<run_id>` del híbrido;
- construye tablas comparativas, gráficos y matrices de confusión;
- filtra para mantener solo comparaciones sobre el mismo split y el mismo universo canónico.

**Por qué es importante**
Separa la consolidación descriptiva de la decisión final. El proyecto no elige el modelo mirando esta tabla a mano; la usa como una de las entradas del cierre.

### Script. `scripts/ejecutar_barrido_ablacion_hibrido.py`
**Qué hace**
Orquesta el barrido y la ablación del sistema híbrido.

**Qué decide**
No decide por sí solo el modelo final, pero genera el espacio de variantes que alimenta el cierre formal.

**Cómo lo hace**
Ejecuta tres fases:

- `A`: barrido factorial amplio;
- `B`: ablaciones estructurales sobre candidatas;
- `C`: estabilidad multi-seed.

**Qué explora**
- presencia o ausencia de `llm`;
- sentimiento;
- contexto;
- template;
- features sintomáticas;
- reglas;
- medicación;
- perfil `core` vs `py`;
- `RandomForest` vs `XGBoost`;
- variantes como `sin_feat`, `sin_medication`, `beto_reglas`, etc.

**Por qué es importante**
Mide no solo rendimiento, sino dependencia estructural del híbrido respecto de cada bloque.

### Script. `scripts/audit/generar_freeze_lexico.py`
**Qué hace**
Congela el estado exacto del recurso léxico y de reglas clínicas.

**Qué decide**
No elige modelos, pero fija la versión del soporte clínico-léxico usado por el cierre.

**Cómo lo hace**
- toma snapshot de `Concept_CO`, `Concept_Core` y `Concept_PY`;
- calcula checksums;
- compara contra un freeze previo si existe;
- publica un resumen legible y diffs de términos.

**Por qué es importante**
Evita que la selección final quede apoyada en un recurso clínico implícito o cambiante.

### Script. `scripts/audit/registrar_artefactos_backbone.py`
**Qué hace**
Publica manifiestos y punteros estables para los artefactos de backbone.

**Qué decide**
No redefine resultados; ordena trazabilidad.

**Cómo lo hace**
- detecta artefactos válidos e incompletos;
- publica `latest.json` y manifiestos;
- permite que otras etapas resuelvan artefactos correctos sin depender de timestamps fijos.

### 09b. `09b_cierre_modelos_dev.ipynb`
**Qué hace**
Cierra formalmente la selección de modelos en `dev`.

**Qué decide**
Define el modelo final vigente del desarrollo y la shortlist que pasará a `test`.

**Cómo lo hace**
- consume artefactos de `08`;
- incorpora comparación controlada de backbone;
- incorpora el barrido/ablación;
- incorpora el freeze léxico;
- aplica una rúbrica multicriterio de cierre.

**Qué evalúa además de `macro_f1`**
- `balanced_accuracy`;
- métricas por clase;
- estabilidad entre semillas;
- simplicidad relativa;
- auditabilidad clínica;
- penalización de bloques metodológicamente más riesgosos.

**Por qué es importante**
La decisión final del proyecto no se apoya en una sola tabla ni en un solo decimal.

**Decisión actual retenida**
- mejor híbrido final en `dev`:
  - `B_A_llm0_sent0_beto1_tpl0_py_XGB_sin_feat_sin_medication|py|XGB`

**Shortlist actual para `test`**
- `TF-IDF`
- `ROBERTA_CLINICAL`
- híbrido final `py|XGB`
- `BETO`

### 09. `09_analisis_errores_hibrido.ipynb`
**Qué hace**
Analiza errores del modelo final ya congelado.

**Qué decide**
No redefine la selección. Interpreta el comportamiento del modelo elegido.

**Cómo lo hace**
- consume `decision_modelo_final.json`;
- recupera las predicciones del modelo efectivamente congelado;
- resume errores por clase, términos distintivos y casos mal clasificados.

**Por qué es importante**
Separa la interpretación clínica y documental de la fase de selección cuantitativa.

### 10. `10_validacion_clinica_ips.ipynb`
**Qué hace**
Orquesta la revisión clínica externa y prepara material reutilizable para una futura etapa de xAI.

**Qué decide**
No redefine la selección experimental ni reabre el entrenamiento.

**Cómo lo hace**
Usa tres scripts backend:

- `scripts/export/generar_material_validacion_ips.py`
- `scripts/export/curar_dossier_ips.py`
- `scripts/export/cerrar_fase_ips.py`

**Qué produce**
- material clínico interpretable;
- dossier curado de errores, patrones y comparación entre modelos;
- paquete final de revisión clínica externa.

**Por qué es importante**
Cumple un rol distinto del pipeline principal:

- traduce el cierre en `dev` a material legible por expertos;
- deja casos reutilizables para futura xAI;
- documenta una fase de contraste experto externo.

## Scripts transversales del proyecto

### `scripts/regenerar_pipeline_desarrollo.py`
Es el orquestador de regeneración completa del estado de desarrollo. Permite reproducir el flujo `01–09` sin ejecutar `test` ni xAI.

### `scripts/run_regeneracion_desarrollo.sh`
Es un wrapper bash opcional del regenerador principal.

### `scripts/llm/run_gemini_constrained.py`
Genera `data/processed/gemini_extraction.json` con una ontología cerrada de síntomas y medicación.

**Rol del LLM en el proyecto**
El LLM solo se usa para:

- normalización semántica de síntomas;
- apoyo en auditoría léxica.

No se usa como clasificador clínico directo.

### `scripts/audit/audit_core.py`
Sirve para auditar el recurso clínico y comparar capas léxicas. Es complementario a `05` y a los freezes.

### `scripts/cerrar_modelos_dev.py`
Es el punto de entrada estable al cierre formal; delega en `scripts/audit/cerrar_modelos_dev.py`.

### `scripts/reportes/generar_reporte_estado_actual.py`
Genera un snapshot consolidado del estado actual del experimento.

**Qué resume**
- dataset;
- baselines;
- selección Transformer;
- comparación de backbone;
- freeze léxico;
- cierre formal;
- error analysis;
- estado de `test` y xAI.

**Por qué es importante**
Es la forma más rápida de responder: cuál es el estado vigente del proyecto sin reabrir todo el pipeline.

## Qué decide cada capa
| Capa | Etapas | Pregunta que resuelve |
|---|---|---|
| Universo | `01`, `02`, `03` | qué datos entran realmente al problema y cómo se particionan |
| Baselines | `04a`, `04b`, `04c` | qué tan difícil es el problema y cuál es la mejor referencia standalone |
| Recurso léxico | `05` | por qué el léxico necesita adaptación local auditada |
| Features híbridas | `06` | cómo se representa la evidencia clínica, contextual y auxiliar |
| Entrenamiento híbrido | `07` | qué variantes tabulares son viables en el universo modelado |
| Backbone | `scripts/comparar_backbones_hibrido.py` | qué backbone conviene dentro del híbrido |
| Consolidación | `08` | cómo se comparan de forma homogénea líneas base e híbridos |
| Ablación | `scripts/ejecutar_barrido_ablacion_hibrido.py` | qué bloques del híbrido aportan o sobran |
| Freeze | `scripts/audit/generar_freeze_lexico.py` | qué versión exacta del soporte clínico se congela |
| Cierre | `09b` | cuál es el modelo final defendible en `dev` |
| Interpretación | `09` | cómo se comporta el modelo final en términos de errores |
| Revisión externa | `10` | cómo traducir el cierre en `dev` a material clínico y futura xAI |

## Diferencia entre preguntas experimentales que no deben mezclarse
Este punto fue uno de los ajustes metodológicos más importantes del desarrollo.

### Pregunta 1
¿Cuál es el mejor transformer standalone?

La responde `04c`.

### Pregunta 2
¿Cuál es el mejor backbone del híbrido?

La responde `scripts/comparar_backbones_hibrido.py`.

### Consecuencia práctica
- `ROBERTA_CLINICAL` puede ganar como baseline standalone;
- `BETO` puede ganar dentro del híbrido;
- ambas cosas pueden ser ciertas a la vez;
- por eso `06` usa `BETO` por defecto;
- y `FE_TEXT_BACKBONE=auto` solo existe para un override explícito.

## Estrategia de selección final
El proyecto no cierra el modelo final con una regla simplista del tipo “gana el mayor `macro_f1`”.

La estrategia de cierre en `dev` combina:

- rendimiento global;
- balance entre clases;
- estabilidad entre seeds;
- simplicidad relativa;
- interpretabilidad clínica;
- riesgo metodológico de ciertos bloques auxiliares;
- consistencia entre backbone, barrido, freeze y error analysis.

Eso explica por qué el proyecto puede retener una variante híbrida contenida aunque algunas líneas base textuales sigan siendo muy competitivas en `dev`.

## Contrastes secundarios y material de apoyo
El repositorio también conserva materiales metodológicos secundarios que no forman parte del benchmark canónico:

- contraste `baseline_crudo_vs_filtrado` para justificar el denoising;
- revisión clínica externa;
- dossier curado para futura xAI.

Estos materiales son útiles para explicación y defensa metodológica, pero no redefinen la comparación principal de modelos.

## Artefactos clave que conviene conocer
### En `data/processed/`
- `fe_<run_id>_core/`
- `fe_<run_id>_py/`
- `gemini_extraction.json`

### En `data/outputs/`
- `transformer_baseline_selection_latest.json`
- `comparacion_backbones_hibrido_latest.json`
- `backbone_artifacts_manifest_latest.json`
- `cierre_modelos_dev_<timestamp>/`
- `error_analysis_<timestamp>/`
- `freeze_lexico_<timestamp>/`
- `reporte_estado_actual_latest.json`

## Estado experimental vigente
A la fecha de este documento, el estado metodológico vigente es:

- mejor baseline simple: `TF-IDF`;
- mejor transformer standalone: `ROBERTA_CLINICAL`;
- mejor backbone del híbrido: `BETO`;
- mejor híbrido final en `dev`: `B_A_llm0_sent0_beto1_tpl0_py_XGB_sin_feat_sin_medication|py|XGB`;
- `test`: pendiente;
- xAI: pendiente.

## Cómo reproducir el estado actual sin interpretar código
### Camino recomendado
```bash
python scripts/regenerar_pipeline_desarrollo.py --dry-run
python scripts/regenerar_pipeline_desarrollo.py --incluir-comparacion-backbones
python scripts/reportes/generar_reporte_estado_actual.py --verbose
```

### Qué devuelve ese recorrido
- artefactos de todas las etapas de desarrollo;
- punteros `latest` para selección Transformer y backbone;
- cierre formal en `dev`;
- un reporte consolidado del estado actual.

## Resumen final
El proyecto no es un conjunto de notebooks sueltos. Es un pipeline metodológico donde cada etapa responde una pregunta distinta y deja artefactos explícitos para la etapa siguiente.

La lógica completa es:

- definir un universo modelado coherente;
- comparar líneas base fuertes en ese universo;
- justificar y congelar la capa léxica adaptada;
- construir una matriz híbrida trazable;
- separar la decisión del mejor standalone de la decisión del mejor backbone del híbrido;
- explorar variantes por barrido y ablación;
- cerrar formalmente la selección en `dev`;
- interpretar errores del modelo congelado;
- preparar revisión clínica externa y futura xAI como fase secundaria.

Entender el proyecto correctamente implica respetar esa separación de preguntas. La arquitectura híbrida, el uso acotado del LLM, la elección de `BETO` por defecto en `06`, el barrido A/B/C, el freeze léxico y el cierre formal en `09b` no son detalles de implementación: son la estructura metodológica del experimento.
