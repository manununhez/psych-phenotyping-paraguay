# Metodología Del Híbrido, Ablación Y Cierre En `dev`

## Propósito de este documento
Este documento explica de forma completa cómo el proyecto construye, compara y cierra la familia de modelos híbridos. Su objetivo es que una persona pueda entender esta etapa sin abrir los notebooks ni reconstruir la lógica a partir del código.

La pregunta que resuelve no es solo "qué modelo rindió más". Resuelve algo más exigente:

- qué matriz de características se construyó;
- qué bloques clínicos, contextuales y auxiliares se activaron o desactivaron;
- por qué se compararon `RandomForest` y `XGBoost`;
- cómo se definió la ablación;
- qué significa parsimonia en este proyecto;
- y cómo se decide formalmente cuál es el mejor híbrido en `dev`.

## Alcance de esta etapa dentro del pipeline
La etapa híbrida empieza metodológicamente en `05` y se ejecuta entre `06` y `09`.

Secuencia relevante:

1. `notebooks/analysis/05_brecha_lexica_co_core_py.ipynb`
2. `notebooks/pipeline/06_ingenieria_features_hibridas.ipynb`
3. `notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb`
4. `scripts/comparar_backbones_hibrido.py`
5. `notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`
6. `scripts/ejecutar_barrido_ablacion_hibrido.py`
7. `scripts/audit/generar_freeze_lexico.py`
8. `notebooks/pipeline/09b_cierre_modelos_dev.ipynb`
9. `notebooks/analysis/09_analisis_errores_hibrido.ipynb`

Cada pieza cumple un rol distinto:

- `05` justifica qué capas léxicas se comparan.
- `06` transforma texto clínico en una matriz tabular híbrida.
- `07` entrena clasificadores sobre esa matriz.
- `comparar_backbones_hibrido.py` aísla la decisión del backbone contextual.
- `08` consolida la comparación entre líneas base y familia híbrida.
- `ejecutar_barrido_ablacion_hibrido.py` explora variantes y ablaciones.
- `generar_freeze_lexico.py` congela el estado del recurso clínico-léxico.
- `09b` aplica la rúbrica multicriterio y congela el mejor híbrido en `dev`.
- `09` analiza errores del modelo efectivamente congelado.

## Idea metodológica central del híbrido
El proyecto no trata el híbrido como una bolsa indiferenciada de features. La arquitectura está diseñada para mantener separadas familias de evidencia con distinto nivel de interpretabilidad y distinto riesgo metodológico.

La lógica es:

1. extraer señal clínica explícita con reglas;
2. recuperar variantes semánticas solo en el espacio sintomático mediante `late fusion`;
3. conservar la medicación como evidencia terapéutica separada;
4. añadir contexto distribuido con embeddings `ctx_<backbone>_*`;
5. evaluar bloques auxiliares como sentimiento o template sin convertirlos en el centro del modelo;
6. someter todo ese espacio a ablación sistemática antes de decidir.

El híbrido no se cierra por acumulación de complejidad. Se cierra por rendimiento defendible bajo control clínico y metodológico.

## Qué decide `05`: el problema léxico y los perfiles comparables
Notebook:
- `notebooks/analysis/05_brecha_lexica_co_core_py.ipynb`

Esta etapa no entrena modelos. Su función es justificar por qué el proyecto no se queda con un único léxico histórico.

El razonamiento es:

- `Concept_CO` sirve como baseline histórico, pero no cubre adecuadamente el uso real del español clínico paraguayo.
- `Concept_Core` depura la capa clínica base y reduce ruido.
- `Concept_PY` amplía cobertura regional sobre una base ya depurada.

De ahí salen los perfiles comparables del híbrido:

- `core`: usa `Concept_Core`.
- `py`: usa `Concept_Core + Concept_PY`.

En la etapa híbrida vigente, la comparación relevante es `core` vs `py`. El perfil `co` queda como referencia histórica, no como perfil principal de entrenamiento híbrido en esta fase.

## Qué construye exactamente `06`: la matriz híbrida
Notebook:
- `notebooks/pipeline/06_ingenieria_features_hibridas.ipynb`

### Objetivo operativo
`06` toma `data/dataset_denoised.csv` y lo convierte en una matriz tabular por fila clínica. Esa matriz es la entrada real de `07`.

### Entradas reales de `06`
- `data/dataset_denoised.csv`
- reglas clínicas congeladas del submódulo `Spanish_Psych_Phenotyping_PY/`
- `data/processed/gemini_extraction.json` si existe y se habilita
- selección standalone de `04c` solo si se fuerza `FE_TEXT_BACKBONE=auto`

### Salidas reales de `06`
- `data/processed/fe_<run_id>_core/features_core.parquet`
- `data/processed/fe_<run_id>_py/features_py.parquet`
- `data/processed/fe_<run_id>_core/feature_summary.csv`
- `data/processed/fe_<run_id>_py/feature_summary.csv`
- `data/processed/fe_<run_id>_config.json`

### Familias de features que componen el híbrido
La matriz de `06` no es monolítica. Tiene bloques distintos.

#### 1. `rule_*`
Evidencia clínica simbólica explícita extraída desde el pipeline clínico rule-based.

Uso:
- anclaje clínico interpretable;
- señal directa de categorías fenotípicas observadas en el texto.

#### 2. `niega_*` y `feat_niega_*`
Capturan negación a nivel de paciente o de relato.

Uso:
- preservar la negación como información clínica;
- evitar convertir toda negación en simple ausencia de fenómeno.

#### 3. `feat_*`
Señal sintomática final tras `late fusion`.

Regla congelada:
- `feat_X = max(rule_X, llm_X)`

Y para negación:
- `feat_niega_X = max(niega_X, llm_niega_X)`

Esto ocurre solo en el espacio sintomático. No se usa `late fusion` para mezclar medicación como si fuera diagnóstico.

#### 4. `rule_medication_*`
Evidencia terapéutica separada.

Uso:
- conservar información farmacológica;
- permitir estudiar si la medicación actúa como proxy útil o espurio;
- evitar inferencias diagnósticas directas no controladas.

Razón metodológica:
- una medicación puede sugerir manejo clínico, gravedad o antecedentes, pero no equivale por sí sola a una etiqueta diagnóstica limpia.

#### 5. `sent_*`
Señal afectiva auxiliar.

Uso:
- bloque opcional, no nuclear;
- útil para contrastes y ablaciones;
- nunca se interpreta como sustituto de la señal clínica explícita.

#### 6. `ctx_<backbone>_*`
Embeddings contextuales del backbone textual seleccionado.

Uso:
- aportar contexto distribuido y variación lingüística no capturada por reglas;
- complementar, no reemplazar, la señal clínica auditada.

## Qué significa `late fusion` en este proyecto
La integración con LLM está acotada por diseño.

No se añade un gran bloque de features semánticas libres. Se usa una estrategia controlada:

- el LLM normaliza síntomas a una ontología cerrada;
- luego esa salida solo puede reforzar el espacio sintomático ya definido por reglas;
- la integración se hace por máximo lógico entre regla y LLM.

Razones para esta decisión:

1. mantener la ontología congelada;
2. evitar crecimiento desordenado del espacio de features;
3. preservar interpretabilidad clínica;
4. hacer que la ablación sea legible;
5. impedir que el LLM funcione como clasificador clínico encubierto.

## Por qué `06` usa `BETO` por defecto
`06` admite varios backbones contextuales, pero no decide por sí mismo cuál usar. Esa decisión metodológica se separa en dos niveles:

- `04c` compara transformers standalone en `dev`;
- `scripts/comparar_backbones_hibrido.py` compara backbones dentro del híbrido manteniendo constante el resto.

La arquitectura híbrida usa `BETO` por defecto porque la comparación controlada del híbrido retuvo `BETO` como mejor backbone contextual vigente.

Esto evita un error metodológico importante: confundir el mejor transformer standalone con el mejor backbone del híbrido.

Si se quiere heredar explícitamente la selección de `04c`, `06` permite:

- `FE_TEXT_BACKBONE=auto`

Pero esa no es la conducta por defecto, porque mezclaría dos decisiones distintas.

## Qué compara `07`: clasificadores sobre la misma matriz
Notebook:
- `notebooks/pipeline/07_entrenamiento_modelos_hibridos.ipynb`

### Objetivo operativo
`07` toma las matrices exportadas por `06` y entrena clasificadores tabulares sobre exactamente esas columnas.

### Entradas reales
- `features_core.parquet`
- `features_py.parquet`
- split congelado por paciente
- configuración exacta de features desde `fe_<run_id>_config.json`

### Salidas reales
- `comparacion_modelos_<split>.csv`
- `predicciones_<profile>_<model>_<split>.csv`
- `modelo_<profile>_<model>.joblib`
- `<profile>_X_cols.json`
- `resumen_entrenamiento.json`
- `resumen_ablacion.json`
- `detalle_columnas_ablacion.json`
- `ablacion_perfiles_<split>.csv`

## Por qué se usaron `RandomForest` y `XGBoost`
La entrada del híbrido ya no es texto crudo. Es una tabla mixta con:

- columnas binarias clínicas;
- columnas de negación;
- columnas auxiliares;
- embeddings contextuales densos;
- bloques con escalas distintas;
- posibles interacciones no lineales entre familias.

En ese contexto, `RandomForest` y `XGBoost` son elecciones razonables por razones distintas y complementarias.

### `RandomForest`
Se usa porque:

- es robusto sobre espacios heterogéneos;
- tolera bien relaciones no lineales;
- no exige una fuerte ingeniería de escalado;
- suele comportarse bien como baseline tabular fuerte;
- exporta artefactos interpretables y comparables;
- en esta implementación admite `class_weight='balanced'`, útil dada la dificultad relativa de `ansiedad`.

En el proyecto cumple el rol de:
- clasificador tabular estable de referencia dentro del híbrido.

### `XGBoost`
Se usa porque:

- suele capturar mejor interacciones complejas en espacios tabulares mixtos;
- puede explotar combinaciones entre reglas, contexto y señales auxiliares;
- es una referencia fuerte en problemas tabulares con no linealidad;
- exporta un bundle reproducible y comparable con `RF`.

En el proyecto cumple el rol de:
- clasificador tabular más competitivo cuando la señal híbrida realmente aporta estructura adicional.

### Por qué no fijar un único clasificador desde el inicio
Comparar `RF` y `XGB` evita atribuir indebidamente a la matriz de features una mejora que en realidad podría venir solo del clasificador.

La comparación se hace para separar dos preguntas:

1. qué tan buena es la matriz híbrida;
2. qué clasificador la explota mejor.

Eso también vuelve más limpia la ablación: si una familia de features cambia el resultado en ambos clasificadores, la señal es más confiable que si solo mejora en uno.

## Cómo se entrenan `RF` y `XGB` en esta etapa
`07` entrena ambos clasificadores sobre exactamente el mismo conjunto de columnas resultante de la ablación aplicada a cada perfil.

La lógica de entrenamiento es:

- `RF`: `RandomForestClassifier` con `class_weight='balanced'`;
- `XGB`: `XGBClassifier` con objetivo probabilístico multiclase para preservar salida por clase y probabilidades exportables;
- ambos usan la misma semilla trazable de corrida;
- ambos exportan predicciones por fila, bundle serializado y metadatos de configuración.

El notebook permite dos modos:

- entrenamiento directo sin tuning;
- tuning opcional con `RandomizedSearchCV`.

### Por qué `RandomizedSearchCV` y no una grilla exhaustiva
La etapa híbrida no busca optimización infinita del clasificador. Busca comparación reproducible entre matrices y familias de features.

Por eso se permite tuning acotado por búsqueda aleatoria:

- reduce costo computacional;
- mantiene comparabilidad entre variantes;
- evita convertir la etapa en una búsqueda hiperparamétrica desproporcionada frente al objetivo metodológico real.

### Cómo se evita leakage durante el tuning
Cuando hay grupos suficientes, `07` usa `GroupKFold` sobre identificadores de paciente dentro de `RandomizedSearchCV`.

Eso importa porque incluso dentro de `train` una validación interna ingenua podría mezclar notas del mismo paciente entre folds. La estrategia por grupos mantiene coherencia con el principio central del proyecto: no evaluar una variante aprovechando estructura longitudinal del mismo paciente de forma encubierta.

## Por qué no se usa oversampling en esta etapa
La versión vigente del pipeline híbrido no aplica oversampling ni sampling sintético.

Razones metodológicas:

- agrega otra fuente de variación al experimento;
- complica la comparación limpia entre familias de features y entre clasificadores;
- puede inflar mejoras aparentes en la clase minoritaria sin aclarar si la ganancia viene del modelo o del procedimiento de rebalanceo;
- vuelve menos transparente la lectura clínica del cierre en `dev`.

En lugar de eso, la etapa vigente prefiere:

- métricas robustas al desbalance (`macro_f1`, `balanced_accuracy`, F1 por clase);
- `class_weight='balanced'` en `RF`;
- y una lectura explícita de la dificultad relativa de `ansiedad`.

## Por qué no se usa accuracy como métrica principal
La tarea está desbalanceada y `depresion` tiene mayor soporte que `ansiedad` en el universo final modelado.

Si se usara solo accuracy, un modelo podría parecer fuerte simplemente por acertar más la clase mayoritaria. Eso sería metodológicamente pobre para un problema clínico diferencial.

Por eso la etapa híbrida prioriza:

- `macro_f1`
- `balanced_accuracy`
- `f1_ansiedad`
- `f1_depresion`

### `macro_f1`
Es la métrica principal dentro de la comparación de variantes.

Razón:
- da el mismo peso a ambas clases;
- penaliza mejor los modelos que ignoran a la clase más difícil;
- resume precisión y recall por clase en un problema binario clínicamente asimétrico.

### `balanced_accuracy`
Se usa como complemento indispensable.

Razón:
- promedia recall por clase;
- corrige la lectura sesgada por prevalencia;
- permite detectar configuraciones con macro F1 aceptable pero sensibilidad pobre en una clase.

### `f1_ansiedad` y `f1_depresion`
Se usan para abrir la caja negra del promedio.

Razón:
- permiten ver si una mejora global viene solo de `depresion`;
- hacen visible si `ansiedad` queda clínicamente descuidada;
- entran después en la rúbrica de cierre como balance por clase.

### `precision_macro` y `recall_macro`
Se exportan como apoyo interpretativo.

Razón:
- ayudan a entender el perfil de error;
- no reemplazan a `macro_f1`, pero complementan la lectura.

## Cómo se define la ablación en `07`
`07` no entrena una sola configuración fija. Define un contrato explícito de activación y desactivación de familias de columnas.

Toggles principales:

- `TRAIN_USE_CONTEXT`
- `TRAIN_USE_TEMPLATE`
- `TRAIN_USE_FEAT`
- `TRAIN_USE_RULES`
- `TRAIN_USE_MEDICATION`
- `TRAIN_USE_SENTIMENT`
- `TRAIN_USE_LLM`

Además permite ablación fina por:

- columnas individuales (`TRAIN_DROP_COLUMNS`)
- prefijos (`TRAIN_DROP_PREFIXES`)
- universo restringido (`TRAIN_KEEP_PREFIXES`)

Esto vuelve trazable qué columnas quedaron realmente dentro de cada variante.

## Qué significa parsimonia en este proyecto
Parsimonia no significa "modelo pequeño" en un sentido abstracto. Significa preferir una variante que:

- use menos bloques auxiliares;
- dependa menos de proxies difíciles de defender;
- mantenga capacidad predictiva sin inflar complejidad;
- conserve auditabilidad clínica.

En esta familia, una variante es más parsimoniosa cuando logra buen desempeño con menos dependencia de:

- `template`
- `medicación`
- `LLM`
- combinaciones redundantes de bloques

Y cuando usa una estructura más contenida de columnas activas.

## Qué compara `scripts/comparar_backbones_hibrido.py`
Script:
- `scripts/comparar_backbones_hibrido.py`

Este script existe para aislar una decisión que no debe resolverse mezclada con el resto: el backbone contextual del híbrido.

### Escenario fijo de comparación
Mantiene constante:

- perfil: `py`
- modelo: `XGB`
- `llm = 0`
- `sentimiento = 0`
- `template = 0`
- `feat = 0`
- `rules = 1`
- `medication = 0`
- `contexto = 1`

Luego reemplaza únicamente el backbone contextual.

### Qué pregunta responde
No pregunta cuál transformer standalone es mejor. Pregunta:

- manteniendo fijo el híbrido, ¿qué backbone contextual conviene dentro de esta arquitectura?

### Por qué esa comparación es necesaria
Sin este script, el proyecto correría el riesgo de heredar en el híbrido la selección de `04c` y mezclar dos experimentos distintos.

## Qué hace `scripts/ejecutar_barrido_ablacion_hibrido.py`
Script:
- `scripts/ejecutar_barrido_ablacion_hibrido.py`

Este script es el corazón del análisis metodológico de la familia híbrida. No vuelve a abrir el corpus ni cambia el problema. Explora sistemáticamente qué bloques sostienen mejor al híbrido bajo el mismo universo de evaluación.

### Fase A: barrido amplio de bloques
Activa y desactiva combinaciones de:

- `llm`
- `sentimiento`
- `beto/contexto`
- `template`

Mantiene inicialmente activos:
- `feat`
- `rules`
- `medication`

Y deja que `07` compare:
- perfil `core` vs `py`
- `RF` vs `XGB`

Esta fase sirve para abrir el espacio experimental.

### Fase B: ablaciones estructurales dirigidas
A partir de las mejores variantes de A, aplica presets de ablación como:

- `sin_feat`
- `sin_rules`
- `sin_medication`
- `sin_feat_sin_rules`
- `sin_feat_sin_medication`
- `sin_rules_sin_medication`
- `solo_beto`
- `solo_reglas_feat_sin_beto`
- `beto_feat`
- `beto_reglas`
- `beto_medication`
- `beto_feat_reglas`
- `sin_beto`

Esta fase responde preguntas estructurales:

- cuánto aporta el contexto;
- cuánto aportan reglas explícitas;
- cuánto depende el modelo de medicación;
- si el bloque `feat_*` realmente mejora o solo añade complejidad;
- si una variante funciona por combinación clínica defendible o por atajo.

### Fase C: estabilidad multi-seed
Toma las mejores variantes de A y B y las vuelve a correr con múltiples seeds, típicamente:

- `42`
- `52`
- `62`

Esta fase evita seleccionar una configuración por accidente de una única corrida.

## Cómo se leen las variantes del barrido
Los nombres de variantes codifican la configuración. Por ejemplo:

- `A_llm0_sent0_beto1_tpl0`
- `B_A_llm0_sent0_beto1_tpl0_py_XGB_sin_feat_sin_medication`

Eso significa, respectivamente:

- fase del barrido (`A`, `B`, `C`);
- bloques activados o desactivados (`llm`, `sentimiento`, `beto/contexto`, `template`);
- perfil (`core` o `py`);
- clasificador (`RF` o `XGB`);
- ablación específica aplicada (`sin_feat`, `sin_medication`, etc.).

Este esquema importa porque vuelve auditable por nombre una parte relevante del experimento.

## Qué papel juega `08`
Notebook:
- `notebooks/pipeline/08_resultados_hibrido_vs_lineas_base.ipynb`

`08` no decide el mejor híbrido final. Su función es consolidar resultados comparativos entre:

- líneas base textuales;
- híbrido base entrenado en `07`.

Sirve para:
- comparar familias de modelos en `dev`;
- dejar artefactos homogéneos de resultados;
- preparar el terreno para el cierre formal.

La decisión final del híbrido no ocurre aquí porque todavía faltan:
- barrido/ablación;
- freeze léxico;
- rúbrica multicriterio de cierre.

## Qué congela `generar_freeze_lexico.py`
Script:
- `scripts/audit/generar_freeze_lexico.py`

El freeze no mejora métricas. Congela el estado del recurso clínico-léxico con el que se tomó la decisión.

Sirve para:
- registrar categorías y recursos usados;
- detectar cambios en ontología o medicación;
- asegurar que el cierre en `dev` no quede desligado del estado léxico real.

Esto es importante porque el híbrido no depende solo de un clasificador: depende también de la capa clínica que define y extrae su señal.

## Dónde y cómo se decide el mejor híbrido
La decisión formal ocurre en:

- `notebooks/pipeline/09b_cierre_modelos_dev.ipynb`
- `scripts/audit/cerrar_modelos_dev.py`

El notebook `09b` es la etapa metodológica visible. El script `cerrar_modelos_dev.py` implementa la rúbrica operativa exacta.

## Qué no hace `09b`
`09b` no elige al ganador simplemente por la fila con mayor `macro_f1`.

Tampoco hace estas cosas:

- no toma cualquier barrido viejo por nombre si no es compatible;
- no ignora el freeze léxico;
- no reemplaza la comparación de backbone por una heurística informal;
- no congela el modelo final solo porque gane una seed única.

## Cómo construye `09b` el pool de candidatos
El cierre toma la tabla maestra del barrido y la reorganiza.

### 1. Reagrupa variantes equivalentes
Si una variante aparece en varias fases o seeds, el script la consolida por `model_key` y evita duplicarla de forma engañosa.

### 2. Prioriza fases más informativas
La fase `C` tiene prioridad sobre `B`, y `B` sobre `A`, porque incorpora más estabilidad o una ablación más informativa.

### 3. Agrega por seed
Para cada candidato calcula, entre otros:

- `macro_f1_mean`
- `macro_f1_std`
- `balanced_accuracy_mean`
- `f1_ansiedad_mean`
- `f1_depresion_mean`
- `n_seeds`

### 4. Mantiene un pool mixto de referencias
El cierre no se limita a híbridos. Mantiene en la tabla:

- baselines textuales;
- el híbrido de referencia;
- top variantes del barrido;
- variantes multi-seed.

Esto permite decir no solo cuál híbrido gana, sino también qué tan lejos o cerca queda respecto de las referencias fuertes.

## La rúbrica de cierre: qué combina exactamente
La selección final en `dev` combina cuatro capas:

1. bloque cuantitativo;
2. bloque metodológico;
3. bloque de interpretabilidad;
4. penalización explícita de riesgo.

### 1. Bloque cuantitativo
Integra:

- `macro_f1`
- `balanced_accuracy`
- mínimo F1 entre clases
- estabilidad entre seeds
- brecha contra el mejor baseline textual

#### Por qué cada una
- `macro_f1`: resume rendimiento global sin favorecer a la clase dominante.
- `balanced_accuracy`: protege la lectura frente al desbalance.
- `min(f1_ansiedad, f1_depresion)`: evita que el promedio oculte un colapso en una clase.
- estabilidad por seeds: evita ganadores accidentales.
- brecha vs mejor baseline textual: exige que el híbrido no quede metodológicamente demasiado lejos de las referencias fuertes.

### 2. Bloque metodológico
Integra:

- `parsimonia`
- `auditabilidad_clinica`

#### `parsimonia`
Se calcula, para híbridos, en función de la cantidad relativa de features activas. Menos complejidad efectiva implica mayor parsimonia, siempre que el rendimiento siga siendo defendible.

#### `auditabilidad_clinica`
Favorece variantes con:

- reglas activas;
- `feat_*` cuando aportan señal controlada;
- perfil `py` cuando mejora cobertura regional.

Y penaliza dependencia de:

- `template`
- `medicación`
- `LLM`

### 3. Bloque de interpretabilidad
La rúbrica incluye además `interpretabilidad_aporte`.

Este bloque valora configuraciones donde la contribución del modelo sea más legible clínicamente. Favorece:

- reglas explícitas;
- bloques clínicos identificables;
- perfil `py` cuando agrega cobertura interpretable.

Penaliza configuraciones demasiado cercanas a "solo contexto" o con dependencia excesiva de bloques poco auditables.

### 4. Penalización explícita de riesgo
La rúbrica resta una penalización a variantes con riesgos metodológicos claros.

Riesgos modelados de forma explícita:

- dependencia de `template`
- medicación como proxy
- LLM sin ganancia robusta
- casi solo contexto

Esto es central: el cierre no premia complejidad por sí misma. Prefiere una variante defendible.

## Por qué el mejor híbrido no tiene que ser el mejor modelo absoluto del repositorio
El proyecto compara familias distintas de modelos:

- baselines textuales simples;
- transformers standalone;
- híbridos tabulares clínico-contextuales.

Una línea base textual puede seguir siendo muy competitiva en `dev`. Eso no invalida el híbrido.

La pregunta del cierre híbrido es otra:

- dentro de la familia híbrida, ¿qué variante es la más defendible combinando rendimiento, balance, estabilidad, parsimonia y auditabilidad?

Por eso es posible retener una variante híbrida contenida aunque `TF-IDF` o `ROBERTA_CLINICAL` sigan siendo referencias fuertes en `dev`.

## Robustecimiento secundario sobre `dev`
Después del cierre formal se ejecutó una auditoría secundaria para revisar tres riesgos: concentración documental por paciente, desempeño específico en `ansiedad` y explicabilidad mínima del XGB final.

Esta auditoría no reabre la selección de modelo. Usa la shortlist y los artefactos congelados para medir robustez antes de abrir `test`.

### Métricas por nivel de agregación
La evaluación principal sigue siendo por nota, pero se añadieron dos lecturas complementarias:

- `patient-weighted`: cada nota pesa `1 / n_notas_paciente`;
- `patient-aggregated`: se agrega una predicción por paciente con regla reproducible.

| Modelo | Macro F1 note-level | Macro F1 patient-weighted | Macro F1 patient-aggregated | AP ansiedad |
|---|---:|---:|---:|---:|
| `TF-IDF` | `0.740564` | `0.751384` | `0.887500` | `0.725725` |
| `ROBERTA_CLINICAL` | `0.741078` | `0.768400` | `0.828571` | `0.655111` |
| híbrido final `py|XGB` | `0.728894` | `0.692788` | `0.750000` | `0.589144` |

La concentración documental en `dev_denoised` no es irrelevante: el híbrido final baja de `macro_f1 = 0.728894` a `0.692788` bajo lectura `patient-weighted`. En cambio, TF-IDF mantiene un comportamiento comparativamente fuerte en las lecturas secundarias.

### Sensibilidad con pesos de entrenamiento
También se ejecutó una única variante de sensibilidad con:

```text
sample_weight = 1 / n_notas_paciente_train
```

El resultado fue negativo: el híbrido ponderado bajó a `macro_f1 = 0.707644`, `f1_ansiedad = 0.572973` y `AP ansiedad = 0.569447`. Por tanto, no se adopta como nuevo cierre ni se interpreta como nueva competencia de modelos. Sirve únicamente como control metodológico.

### Ansiedad, PR-AUC y umbral
La auditoría confirma que `ansiedad` sigue siendo la clase más débil. En Average Precision para `ansiedad`, el híbrido final alcanza `0.589144`, por debajo de TF-IDF (`0.725725`) y `ROBERTA_CLINICAL` (`0.655111`).

Se exploró el umbral del híbrido en `dev`. El umbral canónico `0.50` queda como referencia principal. El mejor umbral observado en `dev` para F1 de ansiedad fue `0.466311`, pero su mejora fue marginal, por lo que no conviene mover el umbral oficial salvo pre-especificación explícita antes de abrir `test`.

### SHAP mínimo sobre el XGB final
La auditoría SHAP se ejecutó sobre el XGB final congelado. El modelo usa `861` columnas:

- `768` columnas `ctx_beto_*`;
- `45` columnas `rule_*`;
- `47` columnas `niega_*`;
- `has_clinical_signal`.

No usa `rule_medication_*`, `sent_*`, `template`, `feat_*` fusionadas ni LLM en la variante final.

La importancia SHAP global queda dominada por `ctx_beto_*`. Las reglas clínicas aportan menos globalmente, aunque conservan valor para trazabilidad local y análisis de casos. La lectura correcta es que el modelo final es un XGB tabular parsimonioso con embeddings BETO y reglas auditables; no un clasificador principalmente simbólico.

## Qué significa que el híbrido final sea parsimonioso
En la corrida vigente, el híbrido retenido es:

- `B_A_llm0_sent0_beto1_tpl0_py_XGB_sin_feat_sin_medication|py|XGB`

Ese nombre resume su lógica:

- `llm0`: no depende del bloque LLM en la variante final retenida;
- `sent0`: no depende de sentimiento;
- `beto1`: mantiene contexto con `BETO`;
- `tpl0`: no depende del bloque template;
- `py`: conserva la cobertura regional paraguaya;
- `XGB`: el clasificador retenido es `XGBoost`;
- `sin_feat_sin_medication`: elimina `feat_*` y `rule_medication_*` en esa variante final.

Interpretación metodológica:
- el cierre favoreció una combinación contenida de contexto + reglas + perfil regional, sin necesidad de retener todos los bloques auxiliares.

Eso es precisamente lo que aquí se entiende por parsimonia.

## Cómo interviene `09`
Notebook:
- `notebooks/analysis/09_analisis_errores_hibrido.ipynb`

`09` no elige el modelo. Analiza errores del modelo ya congelado por `09b`.

Su función es:
- verificar cómo falla el híbrido seleccionado;
- identificar asimetrías entre clases;
- dejar material interpretable y reusable para revisión clínica externa y xAI.

Es importante porque la consistencia del cierre no es solo numérica. También debe sostenerse al mirar los errores del modelo efectivamente retenido.

## Qué artefactos prueban que el cierre ocurrió correctamente
La etapa híbrida deja trazabilidad explícita en artefactos concretos.

### De `06`
- `features_core.parquet`
- `features_py.parquet`
- `feature_summary.csv`
- `fe_<run_id>_config.json`

### De `07`
- `comparacion_modelos_dev.csv`
- `predicciones_*_dev.csv`
- `modelo_*.joblib`
- `resumen_entrenamiento.json`
- `resumen_ablacion.json`
- `detalle_columnas_ablacion.json`

### De comparación de backbone
- `comparacion_backbones_hibrido.csv`
- `comparacion_backbones_hibrido.json`
- `resumen_backbones_hibrido.md`

### Del barrido y la ablación
- `tabla_maestra_comparativa.csv`
- `ranking_variantes.csv`
- `estabilidad_variantes.csv`
- `analisis_dependencia_beto.csv`
- `resumen_barrido.json`
- `resumen_interpretativo.md`

### Del cierre formal
- `ranking_modelos_dev.csv`
- `rubrica_seleccion_modelos.csv`
- `decision_modelo_final.json`
- `shortlist_para_test.json`

## Resumen ejecutivo de la lógica metodológica
La etapa híbrida del proyecto sigue esta secuencia conceptual:

1. justificar perfiles clínico-léxicos comparables (`05`);
2. construir una matriz híbrida interpretable y reproducible (`06`);
3. comparar clasificadores tabulares sobre esa misma matriz (`07`);
4. separar la decisión del backbone contextual de la selección standalone (`comparar_backbones_hibrido.py`);
5. explorar ablaciones amplias, dirigidas y multi-seed (`ejecutar_barrido_ablacion_hibrido.py`);
6. congelar el recurso léxico vigente (`generar_freeze_lexico.py`);
7. aplicar una rúbrica multicriterio para cerrar el mejor híbrido en `dev` (`09b`);
8. analizar errores del modelo efectivamente retenido (`09`).

## Conclusión metodológica
El mejor híbrido del proyecto no se define como la variante más compleja ni como la que maximiza un solo número. Se define como la variante que mejor equilibra:

- rendimiento diferencial entre clases;
- estabilidad;
- control del desbalance;
- parsimonia;
- interpretabilidad clínica;
- menor dependencia de bloques auxiliares de mayor riesgo;
- y consistencia con el backbone, el barrido, el freeze y el análisis de errores.

Esa es la razón por la que el cierre puede retener una variante híbrida contenida, incluso cuando algunas líneas base textuales siguen siendo altamente competitivas en `dev`.
