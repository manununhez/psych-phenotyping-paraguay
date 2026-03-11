# Compendio metodológico para LLM / NotebookLM

## 1. Propósito del proyecto
Este proyecto estudia el fenotipado psiquiátrico en notas clínicas en español de Paraguay. El objetivo actual es clasificar probabilísticamente entre ansiedad y depresion. No se plantea un sistema puramente estadístico ni puramente simbólico. La propuesta final es híbrida: combina reglas clínicas, adaptación léxica regional, normalización semántica acotada con LLM, embeddings BETO y features de sentimiento.

## 2. Problema central
El problema principal no fue únicamente elegir un buen clasificador. El obstáculo más importante fue la brecha léxica entre un recurso heredado de otro contexto hispanohablante y la escritura clínica real observada en Paraguay. En términos prácticos, eso significó dos cosas: por un lado, síntomas relevantes que no quedaban cubiertos por el lexicón original; por otro, activaciones espurias producidas por términos poco transferibles o demasiado ambiguos.

## 3. Secuencia conceptual del recurso léxico
La narrativa metodológica del recurso queda organizada en tres capas:

- `Concept_CO`: baseline histórico.
- `Concept_PY (Core)`: núcleo clínico depurado y más robusto.
- `Concept_PY_Lexicon`: capa de adaptación paraguaya.

Esta secuencia es importante porque muestra que la adaptación no fue una acumulación desordenada de términos. Primero se conservó un punto de comparación histórico, luego se limpió la base clínica, y recién después se amplió cobertura local.

## 4. Qué justifica la brecha léxica
La brecha léxica se justifica por varios fenómenos simultáneos:

- presencia de colombianismos y supuestos lingüísticos heredados de `Concept_CO`;
- expresiones paraguayas y jopará fuera de cobertura;
- abreviaturas clínicas e institucionales del IPS;
- variantes ortográficas y formas indirectas de expresar síntomas.

Por eso, el desempeño del sistema no dependía solo del modelo. Dependía también de si la representación clínica era capaz de “ver” el lenguaje real del corpus.

## 5. Cómo se construyó el Core
La construcción de `Concept_PY (Core)` no se pensó como expansión, sino como depuración. El objetivo fue reducir fragilidad estructural:

- remover disparadores ambiguos;
- disminuir ruido administrativo;
- ajustar reglas con alta propensión a falsos positivos;
- preservar términos clínicos más generales y transportables.

El Core debe entenderse como una capa relativamente portable, no como un diccionario regional.

## 6. Cómo se construyó `Concept_PY_Lexicon`
Una vez estabilizado el Core, se incorporó una capa específica para la variación local. `Concept_PY_Lexicon` reúne paraguayismos, abreviaturas frecuentes y variantes detectadas en el corpus IPS que no quedaban bien absorbidas por el Core. La función de esta capa no es reemplazar el núcleo clínico, sino completar su cobertura donde el uso regional lo exige.

## 7. Rol del LLM en la auditoría léxica
El LLM no se usó solo como componente posterior del modelo. También tuvo un papel metodológico durante la auditoría léxica. Se utilizó para contrastar expresiones dudosas, verificar equivalencias semánticas y revisar si ciertos términos heredados eran colombianismos, coloquialismos o variantes locales. Esto fue útil para ordenar la limpieza de Core y para decidir qué debía quedar reservado a `Concept_PY_Lexicon`.

Es importante dejar claro que esta asistencia no reemplazó el criterio del proyecto. El LLM ayudó a acelerar verificación semántica y revisión manual, pero no definió por sí solo la ontología.

## 8. Split por paciente
El split por paciente es una decisión metodológica central. En un corpus longitudinal, dividir por nota puede inflar artificialmente el rendimiento porque el modelo termina viendo fragmentos del mismo paciente en entrenamiento y evaluación. El `patient-level split` reduce esa fuga de información y aproxima mejor el escenario real de uso.

## 9. Denoising clínico
Antes de modelar, el texto se limpia para eliminar ruido administrativo y de plantilla. Esta decisión mejora la calidad de la señal modelada y evita que el sistema aprenda patrones documentales sin relevancia clínica. El denoising no es un detalle de preprocesamiento; es parte de la validez del pipeline.

## 10. Líneas base
Las líneas base cumplen funciones distintas:

- Dummy: fija un piso mínimo.
- TF-IDF: sirve como baseline textual estándar y económico.
- BETO / Transformers: capturan contexto semántico más rico.

TF-IDF no se redefine como un sistema basado en `Concept_CO`. Se mantiene como baseline clásico de texto. Su valor está en mostrar hasta dónde llega una representación lexical-estadística cuando existe variación regional y clínica que no queda bien resuelta con vocabulario superficial.

BETO se vuelve especialmente importante porque, además de actuar como baseline contextual fuerte, luego se reutiliza como parte de la arquitectura híbrida. Esa reutilización debe justificarse como continuidad experimental, no como conveniencia arbitraria.

## 11. Reglas, negación y medicación
Las reglas se mantienen porque aportan trazabilidad clínica. Dentro de ellas, la negación se trata de forma diferenciada:

- la negación del paciente se conserva como señal (`feat_niega_*`);
- la negación de plantilla o del médico se considera ruido documental y se filtra.

La medicación se mantiene en un espacio separado como `rule_medication_*`. Esto evita confundir evidencia terapéutica con evidencia fenotípica directa.

## 12. Rol del LLM en el modelo final
En el modelo final, el LLM se usa de manera acotada: normaliza síntomas y recupera equivalencias semánticas que las reglas pueden perder. La integración se hace con `late fusion`:

`feat_X = max(rule_X, llm_X)`

La decisión de usar `late fusion` busca preservar interpretabilidad, mantener control sobre la ontología y evitar crecimiento desordenado del espacio de features.

## 13. Por qué el LLM no fusiona medicación
Aunque el LLM puede detectar menciones de fármacos, esas detecciones no se fusionan como diagnóstico. La razón es metodológica: un medicamento puede sugerir varios cuadros o decisiones terapéuticas, pero no equivale a una evidencia diagnóstica inequívoca. Por eso, las menciones de medicación detectadas por LLM se usan para auditoría, apoyo léxico y revisión semántica, mientras que `rule_medication_*` se conserva como evidencia terapéutica separada.

## 14. Arquitectura híbrida final
La arquitectura final combina:

- reglas clínicas;
- normalización semántica acotada con LLM;
- embeddings BETO;
- features de sentimiento;
- clasificadores tabulares como RandomForest y XGBoost.

La justificación del híbrido es práctica y metodológica: ningún bloque, por sí solo, resolvía cobertura regional, interpretabilidad clínica y contexto semántico al mismo tiempo.

## 15. Flujo final del proyecto
El flujo activo del proyecto queda así:

1. limpieza y EDA;
2. split por paciente;
3. denoising con reglas;
4. líneas base;
5. brecha léxica;
6. ingeniería de features híbridas;
7. entrenamiento;
8. resultados y ablaciones;
9. análisis de errores.

La dependencia entre etapas no es solo técnica. También es argumental. Por ejemplo, BETO primero se evalúa como línea base contextual y después se reutiliza en la arquitectura híbrida. De la misma forma, la construcción de `Core` y `PY_Lexicon` se justifica a partir de la brecha léxica y no como una decisión aislada.

## 16. Aportes principales
Los aportes del trabajo pueden resumirse en cuatro líneas:

1. adaptación léxica clínica regional con trazabilidad (`Concept_CO -> Core -> PY_Lexicon`);
2. uso acotado y metodológicamente controlado del LLM;
3. arquitectura híbrida explicable y reproducible;
4. pipeline con artefactos exportables para reporte metodológico, análisis y auditoría.

## 17. Limitaciones
Las principales limitaciones son:

- dependencia del corpus y del entorno institucional de origen;
- posibilidad de que aparezcan nuevas variantes regionales fuera de cobertura;
- sensibilidad del resultado al etiquetado clínico disponible;
- necesidad de validación externa antes de afirmar transferibilidad amplia.

## 18. Pendientes útiles para escritura metodológica
Quedan como pendientes de redacción y consolidación:

- compendio final de decisiones metodológicas;
- sección metodológica para reporte/paper;
- exposición ordenada de la brecha léxica;
- justificación del rol de BETO;
- discusión del rol del LLM en auditoría léxica y late fusion.

Este archivo está pensado como base de conocimiento para NotebookLM y como apoyo para redactar metodología, resultados y discusión sin depender de reconstruir todo el proceso desde cero.


# Compendio Metodológico Integrado

## 1. Problema y alcance real del proyecto
El estudio aborda fenotipado psiquiátrico en notas clínicas en español de Paraguay, con objetivo binario (`ansiedad`, `depresion`) y salida probabilística. El diseño final no se apoya en un único paradigma. Combina reglas clínicas, normalización semántica acotada con LLM, `embeddings` BETO, features de sentimiento y clasificadores tabulares (`RandomForest` / `XGBoost`).

El alcance está explícitamente acotado por componentes congelados: ontologías (`Concept_CO`, `Concept_PY`, `Concept_PY_Lexicon`), lógica de `late fusion` y separación de evidencia terapéutica (`rule_medication_*`).

## 2. Flujo experimental y lógica de dependencia
El flujo operativo sigue una secuencia que evita atajos metodológicos:

1. limpieza y EDA;
2. split por paciente;
3. denoising clínico;
4. líneas base;
5. análisis de brecha léxica;
6. ingeniería de features híbridas;
7. entrenamiento y comparación de modelos;
8. consolidación de resultados;
9. análisis de errores.

La dependencia entre etapas no es solo técnica; es argumental. Por ejemplo, BETO no entra al híbrido por conveniencia: primero se evalúa como baseline contextual y luego se reutiliza en 07/08 con una justificación explícita.

## 3. Por qué la brecha léxica es el núcleo científico
El problema central fue la distancia entre cobertura lexical de `Concept_CO` y escritura clínica paraguaya. Esto exigió una secuencia en tres capas:

- `Concept_CO`: baseline histórico para trazabilidad;
- `Concept_PY (Core)`: depuración estructural para robustez;
- `Concept_PY_Lexicon`: adaptación regional para cobertura efectiva.

Esta transición no fue cosmética. Sin ella, los errores no provenían solo del clasificador, sino de una representación clínica incompleta.

## 4. Rol del LLM: útil, pero acotado
El LLM se utiliza para normalización semántica de síntomas y apoyo de auditoría léxica. En auditoría ayuda a verificar:

- coloquialismos;
- colombianismos heredados;
- variantes paraguayas;
- equivalencias semánticas.

No se usa como clasificador diagnóstico directo. La integración con reglas se hace por `late fusion` (`feat_X = max(rule_X, llm_X)`), para preservar ontología, control de dimensionalidad y auditabilidad.

## 5. Líneas base y criterio comparativo
Se incluyeron tres familias con funciones distintas:

- Dummy para piso metodológico.
- TF-IDF como baseline de texto convencional.
- Transformers para referencia contextual.

TF-IDF se mantiene como baseline lexical-estadístico sobre texto y no se redefine como sistema ontológico. Su valor está en mostrar hasta dónde llega un enfoque clásico y dónde la variación regional exige adaptación lexical explícita.

BETO se justifica como baseline contextual fuerte y, por continuidad metodológica, se reutiliza como bloque de `embeddings` en el híbrido.

## 6. Split por paciente y denoising: dos decisiones estructurales
El `patient-level split` es indispensable en corpus longitudinal para evitar leakage entre notas del mismo paciente. Sin ese control, la evaluación puede inflarse por memorizar estilo documental más que fenómeno clínico.

El denoising previo reduce ruido administrativo que, de otro modo, contamina entrenamiento, comparaciones de baseline y análisis de errores. Esta limpieza mejora validez clínica de la señal modelada.

## 7. Reglas, negación y medicación
Las reglas siguen siendo el eje explicable del sistema. La negación se trata de forma diferenciada:

- negación del paciente: señal clínicamente informativa;
- negación de plantilla/médico: ruido a filtrar.

La medicación se conserva como evidencia terapéutica en `rule_medication_*`. Aunque el LLM puede detectar fármacos, esas detecciones no se fusionan para diagnóstico directo. Se usan en auditoría, apoyo léxico y verificación semántica.

## 8. Racional del híbrido final
El híbrido responde a una necesidad práctica: ninguna fuente aislada resolvía simultáneamente cobertura regional, contexto semántico y trazabilidad clínica.

- Reglas: precisión estructural e interpretabilidad.
- LLM acotado: recuperación semántica sin reemplazar ontología.
- BETO: contexto distribuido.
- Sentimiento: señal complementaria.
- RandomForest/XGBoost: robustez en espacio de features heterogéneo.

Esta combinación ofrece una base metodológica defendible: explícita en decisiones, reproducible en pipeline y auditable en errores.

## 9. Reproducibilidad y artefactos
El flujo produce artefactos claros por etapa:

- features híbridas (`data/processed/fe_<run_id>_*`);
- entrenamiento (`data/outputs/train_<run_id>/`);
- consolidación (`data/outputs/results_<run_id>/`);
- análisis de errores (`data/outputs/error_analysis_<run_id>/`).

Esto facilita revisión, trazabilidad y reutilización en redacción técnica/paper.

## 10. Cierre crítico
La contribución principal no es solo un modelo final, sino una metodología de adaptación clínica regional con control de explicabilidad. El principal límite es la generalización fuera del entorno institucional de origen, por lo que el siguiente paso razonable es validación externa y auditoría léxica continua.
