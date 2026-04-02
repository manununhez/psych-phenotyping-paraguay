# Metodología

## Propósito del estudio
El objetivo es clasificar notas clínicas psiquiátricas entre dos etiquetas (`ansiedad`, `depresion`) con salida probabilística y un diseño que combine rendimiento y trazabilidad clínica.

## Restricciones metodológicas fijas
El estudio mantiene componentes congelados: `Concept_CO`, `Concept_Core`, `Concept_PY`, `patient-level split` y la regla de `late fusion` (`feat_X = max(rule_X, llm_X)`). Estas restricciones no son accesorias; permiten comparar decisiones sin reescribir la base clínica en cada iteración.

## Secuencia de trabajo
La lógica experimental sigue nueve etapas encadenadas: limpieza inicial, split por paciente, denoising clínico, líneas base, análisis de brecha léxica, ingeniería de features híbridas, entrenamiento, consolidación de resultados y análisis de errores. Esta secuencia evita mezclar decisiones de preprocesamiento con decisiones de modelado.

## Brecha léxica como problema central
La brecha entre `Concept_CO` y el uso real del español clínico paraguayo motivó la transición `Concept_CO -> Concept_Core -> Concept_PY`. El punto no fue solo agregar términos: primero se depuró la capa Core para reducir ruido y luego se extendió cobertura regional con criterios auditables.

## Rol del LLM
El LLM se usa en dos tareas delimitadas: normalización semántica de síntomas para `late fusion` y apoyo en auditoría léxica (coloquialismos, colombianismos, variantes paraguayas y equivalencias). No se usa como clasificador diagnóstico autónomo.

## Justificación de BETO en la cadena experimental
La metodología separa dos decisiones que no deben confundirse:
- `04c` compara transformers standalone y fija cuál rinde mejor como baseline contextual aislado en `dev`.
- la comparación controlada de backbone del híbrido decide qué modelo contextual conviene dentro de la arquitectura híbrida, manteniendo constante el resto de la configuración.

En la corrida vigente, `ROBERTA_CLINICAL` queda como mejor transformer standalone, mientras que `BETO` queda retenido como mejor backbone del híbrido. Por eso `06` usa `BETO` por defecto para construir `ctx_<backbone>_*`.

Si se quisiera forzar una herencia explícita desde `04c`, el notebook `06` admite `FE_TEXT_BACKBONE=auto`. Esa opción no es el comportamiento por defecto porque mezclaría dos decisiones metodológicas distintas.

## Salidas reproducibles
La reproducibilidad se apoya en artefactos versionados por corrida: features híbridas en `data/processed`, resultados de entrenamiento en `data/outputs/train_*`, consolidación en `data/outputs/results_*` y análisis de errores en `data/outputs/error_analysis_*`.

## Estado experimental de esta etapa
El cierre actual corresponde a fase de desarrollo en `dev`:
- comparación de líneas base,
- barridos y ablaciones,
- freeze léxico preliminar,
- selección formal de modelo.

La evaluación final en `test` queda explícitamente reservada para la fase siguiente y no forma parte de este cierre.

## Entorno de ejecución, herramientas y reproducibilidad

### Hardware
Las corridas reportadas en esta etapa se ejecutaron en esta misma máquina local. El entorno identificado en el repositorio corresponde a:
- equipo: `MacBook Pro` (`Mac14,9`);
- chip: `Apple M2 Pro`;
- CPU: `10` núcleos (`6` performance + `4` efficiency);
- memoria: `16 GB`;
- sistema operativo: `Darwin 24.6.0` (`arm64`).

Estado de aceleración detectado en el entorno local:
- `torch.cuda.is_available() = False`
- `torch.backends.mps.is_built() = True`
- `torch.backends.mps.is_available() = False`

Interpretación operativa para este proyecto:
- este entorno fue suficiente para `TF-IDF`, modelos tabulares, consolidación de resultados, análisis de errores y validación clínica;
- en `04c` no se asumió hardware acelerado disponible de forma estable, por lo que la comparación Transformer se implementó con restricciones de memoria y tiempo;
- no es el entorno ideal para `fine-tuning` intensivo de transformers a gran escala; la alternativa natural, si en una fase futura se necesitara ampliar barridos o repetir entrenamientos pesados desde cero, sería una GPU dedicada con `CUDA`.

### Software y librerías principales
El repositorio fija dependencias en `requirements.txt` y usa un entorno virtual local (`.venv`). Versiones detectadas en el entorno actual:

| Componente | Uso principal en el proyecto | Versión |
|---|---|---:|
| Python | ejecución general del pipeline | `3.13.0` |
| pandas | tablas, joins, consolidación de artefactos | `2.3.3` |
| numpy | operaciones numéricas y matrices | `2.3.4` |
| scipy | utilidades numéricas complementarias | `1.16.2` |
| scikit-learn | `TF-IDF`, métricas, `RandomForest`, validación y utilidades tabulares | `1.7.2` |
| transformers | baselines `BETO`, `ROBERTA_CLINICAL`, `ROBERTA_BIOMEDICAL` | `4.57.1` |
| torch | backend de inferencia/entrenamiento de transformers | `2.9.0` |
| xgboost | clasificador tabular del híbrido final | `3.2.0` |
| spaCy | procesamiento lingüístico base del pipeline clínico | `3.8.7` |
| medSpaCy | contexto clínico, negación y componentes clínicos rule-based | `1.3.1` |
| pysentimiento | features opcionales de sentimiento | `0.7.3` |
| datasets | manejo de datasets para experimentos con transformers | `4.3.0` |
| evaluate | evaluación de modelos Transformer | `0.4.6` |
| sentencepiece | tokenización requerida por ciertos modelos | `0.2.1` |
| tokenizers | tokenización rápida del stack Hugging Face | `0.22.1` |
| joblib | serialización y persistencia de artefactos | `1.5.2` |
| matplotlib | figuras y reportes | `3.10.7` |
| seaborn | visualización complementaria | `0.13.2` |
| tqdm | seguimiento de progreso | `4.67.1` |
| wordcloud | visualizaciones descriptivas del corpus | `1.9.4` |
| tabulate | exportes tabulares en Markdown | `0.9.0` |
| ipykernel | ejecución interactiva de notebooks | `7.1.0` |

Notas de uso:
- `scikit-learn` cubre no solo `TF-IDF`, sino también métricas, `RandomForest`, `LinearSVC` en contrastes auxiliares y componentes de validación.
- `transformers` + `torch` sostienen la etapa `04c` y el bloque contextual del híbrido.
- `spaCy` + `medSpaCy` + el submódulo `Spanish_Psych_Phenotyping_PY/` sostienen la extracción clínica y el denoising.
- `xgboost` es especialmente importante porque el mejor híbrido final vigente en `dev` usa `XGBoost`.

### Servicios LLM y extracción semántica
El proyecto también usa un servicio LLM externo en una etapa acotada de apoyo semántico y auditoría léxica:

| Componente | Uso principal en el proyecto | Versión / modelo |
|---|---|---:|
| Gemini API | extracción semántica restringida a ontología congelada | `gemini-2.5-pro` |
| SDK `google.genai` | cliente Python usado por `scripts/llm/run_gemini_constrained.py` | versión exacta no preservada en dependencias |

Detalles reproducibles actualmente visibles en código:
- script: `scripts/llm/run_gemini_constrained.py`;
- modelo por defecto: `MODEL_NAME = gemini-2.5-pro`;
- procesamiento por lotes: `BATCH_SIZE = 15`;
- pausa entre lotes: `SLEEP_SECS = 2.0`;
- entrada por defecto: `data/input_for_gemini.json`;
- salida por defecto: `data/processed/gemini_extraction.json`.

Delimitación metodológica:
- Gemini no se usa como clasificador clínico directo;
- se usa para extracción semántica restringida a la ontología congelada y apoyo en auditoría léxica;
- esto es adecuado para ampliar cobertura semántica bajo control, pero no sustituye reglas clínicas ni validación experta;
- el nivel de trazabilidad hoy preservado permite afirmar con certeza el modelo de servicio utilizado (`gemini-2.5-pro`), pero no reconstruir con precisión la versión histórica del SDK cliente;
- si se quisiera una trazabilidad todavía más estricta en futuras corridas, convendría fijar explícitamente en dependencias la versión del SDK `google.genai`.

### Restricciones prácticas de `04c_linea_base_transformers`
La etapa `04c` se diseñó para poder ejecutarse y regenerarse en este hardware sin asumir GPU dedicada:
- selección de dispositivo en cascada: `CUDA` -> `MPS` -> `CPU`;
- en este entorno, `CUDA` no está disponible y `MPS` no quedó disponible en la sesión medida, por lo que el flujo depende de `CPU` o de reuso de predicciones;
- por defecto se prioriza `TRF_REUSAR_PREDICCIONES=1` para recalcular métricas sobre el split vigente sin volver a entrenar innecesariamente;
- cuando se entrena desde cero: `MAX_LENGTH=512`, `BATCH_SIZE=4`, `ACCUMULATION_STEPS=4`, `EPOCHS=3`, `gradient_checkpointing=True`;
- en modo rápido: `MAX_LENGTH=256`, `BATCH_SIZE=2`, `ACCUMULATION_STEPS=2`, `EPOCHS=1`.

Estas decisiones son metodológicamente razonables para una comparación controlada en un entorno local limitado:
- preservan comparabilidad entre backbones y entre corridas;
- reducen el riesgo de fallos por memoria;
- permiten regeneración sin depender de infraestructura externa.

Su limitación es clara:
- no representan el mejor entorno posible para explorar `fine-tuning` más agresivo, barridos amplios o secuencias más largas;
- si en trabajo futuro se quisiera maximizar rendimiento Transformer puro, la opción adecuada sería repetir esa etapa en hardware con GPU dedicada.

### Trazabilidad del pipeline
La trazabilidad se resuelve con una combinación de:
- notebooks Jupyter para exploración, análisis y presentación de resultados;
- scripts modulares de Python para barridos, cierres, exportes y regeneración por lote;
- `Git` para control de versiones del repositorio;
- submódulo `Spanish_Psych_Phenotyping_PY/` para la capa clínica heredada;
- artefactos versionados por corrida en `data/processed/` y `data/outputs/`;
- punteros `latest.json` para evitar depender de carpetas con timestamp fijo;
- freezes y manifiestos específicos para backbone y recurso léxico.

En términos operativos, el repositorio combina:
- notebooks como capa legible y auditable;
- scripts como capa reproducible y regenerable.

### Fijación de semillas y estabilidad
La reproducibilidad no depende solo del código y las versiones, sino también del control de la aleatoriedad.

En el proyecto actual:
- la separación `train/dev/test` queda congelada una vez generado el `patient-level split`;
- el splitter de validación interna en utilidades compartidas usa `StratifiedGroupKFold(..., shuffle=True, random_state=42)`;
- la comparación controlada de backbones del híbrido se ejecuta con seed fija `42`;
- el barrido híbrido usa seed fija `42` en fases puntuales y una fase de estabilidad multi-seed con `42,52,62`;
- varios modelos y utilidades tabulares usan `random_state=42` cuando corresponde.

Al reportar resultados, conviene distinguir:
- corridas con seed única, útiles para comparación controlada puntual;
- corridas multi-seed, útiles para estimar estabilidad del híbrido final.

### Qué conviene reportar explícitamente
Para una descripción defendible y reproducible, conviene informar:
- hardware real de las corridas reportadas;
- versión de Python y librerías principales;
- uso de notebooks y scripts modulares;
- control de versiones con `Git` y submódulo clínico;
- semillas usadas en comparación y estabilidad;
- existencia de artefactos versionados y punteros `latest`;
- separación entre entorno local regenerable y documentación pública versionada.

### Referencias software y de reporte recomendadas
Estas referencias publicadas ayudan a justificar cómo presentar el entorno y la reproducibilidad:

1. Pedregosa et al. (2011), *Scikit-learn: Machine Learning in Python*, JMLR.
   Fuente: https://www.jmlr.org/papers/v12/pedregosa11a.html
2. Wolf et al. (2020), *Transformers: State-of-the-Art Natural Language Processing*, EMNLP System Demonstrations.
   Fuente: https://aclanthology.org/2020.emnlp-demos.6/
3. Chen y Guestrin (2016), *XGBoost: A Scalable Tree Boosting System*.
   Fuente: https://arxiv.org/abs/1603.02754
4. Eyre et al. (2022), *Launching into clinical space with medSpaCy: a new clinical text processing toolkit in Python*, AMIA Annu Symp Proc.
   Fuente: https://pmc.ncbi.nlm.nih.gov/articles/PMC8861690/
5. Digan et al. (2021), *Can reproducibility be improved in clinical natural language processing? A study of 7 clinical NLP suites*, JAMIA.
   Fuente: https://academic.oup.com/jamia/article/28/3/504/6034902
6. Collins et al. (2024), *TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods*, BMJ.
   Fuente: https://www.bmj.com/content/385/bmj-2023-078378

Interpretación práctica de estas referencias:
- las citas de software respaldan la descripción de las herramientas empleadas;
- las citas de reproducibilidad y TRIPOD+AI respaldan por qué conviene reportar entorno, versiones, trazabilidad, seeds y artefactos.
