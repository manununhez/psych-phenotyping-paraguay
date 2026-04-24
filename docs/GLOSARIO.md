# Glosario

Este glosario reúne términos estables del proyecto que conviene poder explicar sin abrir notebooks ni artefactos locales.

## Ablación
Prueba donde se apaga o retira un bloque del sistema para estimar cuánto aporta bajo el mismo universo experimental.

## Auditabilidad clínica
Capacidad de discutir el comportamiento del modelo por familias de señales clínicas y no solo por un score agregado.

## Backbone contextual
Modelo textual que aporta embeddings densos al híbrido. En el cierre vigente del híbrido, el backbone retenido es `BETO`.

## Baseline
Modelo de referencia usado para evaluar si una propuesta más compleja realmente agrega valor.

## Balanced accuracy
Promedio del recall por clase. Es útil cuando el problema está desbalanceado.

## Comorbilidad
Coexistencia de fenómenos clínicos que no se modela como clase explícita en la fase actual, pero sí se reconoce como dificultad real de la tarea.

## Denoising
Proceso de limpieza metodológica del corpus para conservar notas con señal clínica útil para la tarea diferencial.

## Embedding contextual
Representación densa y de dimensión fija derivada de un transformer. En el híbrido se exporta como columnas `ctx_<backbone>_*`.

## Freeze léxico
Congelamiento formal del estado del recurso clínico-léxico antes del cierre metodológico y antes de la fase final experimental.

## Freeze del modelo
Decisión formal de qué configuración exacta del modelo queda retenida y deja de ajustarse en función de resultados posteriores.

## F1
Media armónica entre precisión y recall.

## Grupo de control
Conjunto de casos fuera de la población objetivo o sin el fenómeno de interés. Sería útil para otra formulación del problema, más cercana a screening general.

## Has clinical signal
Indicador binario que marca si una nota conserva al menos una entidad válida como señal clínica útil según la política de `keep_entity`.

## Híbrido
Modelo que combina señales clínicas explícitas, contexto textual denso y otros bloques auxiliares dentro de un clasificador tabular.

## Label noise
Ruido de etiqueta. Ocurre cuando la etiqueta disponible no representa con precisión lo que la consulta expresa en texto.

## Late fusion
Fusión tardía restringida al espacio sintomático, donde `feat_X = max(rule_X, llm_X)`. No se aplica a medicación.

## Leakage
Contaminación entre entrenamiento y evaluación que hace parecer al modelo mejor de lo que realmente es.

## Macro F1
Promedio del F1 por clase, dando el mismo peso a cada una. Es la métrica principal del cierre porque el problema está desbalanceado.

## Mejor backbone del híbrido
Backbone contextual que resulta más conveniente dentro del híbrido manteniendo fijo el resto de la arquitectura. No equivale necesariamente al mejor transformer standalone.

## Mejor transformer standalone
Transformer baseline que rinde mejor como clasificador textual completo en `dev`.

## Patient-level split
Separación train/dev/test en la que todas las notas de un mismo paciente quedan en el mismo conjunto para evitar leakage longitudinal.

## Parsimonia
Preferencia por una variante que mantiene rendimiento defendible sin sumar bloques difíciles de justificar ni complejidad innecesaria.

## Recall
De los casos reales de una clase, cuántos logra recuperar el modelo.

## Regla clínica explícita
Señal simbólica extraída por el pipeline rule-based a partir de patrones clínicos congelados.

## Screening general
Tarea de tamizaje amplio caso/no caso. No es la tarea actual del proyecto, que es diagnóstico diferencial entre dos clases psiquiátricas.

## Señal clínica útil
Mención que pasa el filtro de `keep_entity`: no está en contexto histórico, hipotético ni familiar y, si está negada, la negación debe provenir del paciente.

## Split por nota
Evaluación donde cada consulta cuenta como observación independiente. Es la unidad principal de análisis en esta tesis.

## TF-IDF
Representación textual basada en frecuencia y especificidad de términos dentro del corpus. En el proyecto funciona como baseline textual fuerte y parsimonioso.

## Transformer
Modelo neuronal que representa el texto usando contexto y no solo presencia de palabras aisladas.

## xAI / explicabilidad
Conjunto de técnicas para inspeccionar qué señales usa el modelo y cómo decide en casos concretos. En el cierre vigente, la lectura compatible es SHAP por familias de variables.
