# Limitaciones

## Alcance clínico y población
El estudio clasifica notas entre dos etiquetas en una población psiquiátrica institucional. No estima diagnóstico autónomo, comorbilidad, screening caso/no caso ni transferibilidad a otros centros. La etiqueta puede reflejar el diagnóstico longitudinal más que el contenido de una consulta; esto no permite atribuir todos los desacuerdos a errores de etiquetado.

El universo modelado está condicionado por denoising: conserva 1835 de 3143 notas limpias (58.38%). El filtro comparte recursos de extracción con los modelos clínico-léxicos. No se demostró mediante revisión clínica completa la correctitud de todas las exclusiones ni una mejora causal del rendimiento. La señal terapéutica/contextual puede retener notas con poca información diferencial.

## Muestra, particiones y dependencias
Solo hay 90 pacientes y 18 en prueba, siete de ellos de ansiedad. La evaluación por nota concede mayor peso a pacientes con más consultas; las lecturas secundarias por paciente no sustituyen validación externa.

La separación de pacientes no elimina duplicación textual: el EDA identifica ocho grupos de texto idéntico con 94 notas; cuatro grupos aparecen en las tres particiones y reúnen 86 notas. No prueba filtración de identidades, pero limita la independencia documental.

Las particiones no se estratificaron simultáneamente por edad, sexo, longitud y vocabulario. Las 17 edades conocidas de prueba van de 37.03 a 62.21 años, con menor dispersión que en desarrollo/entrenamiento; la edad restante no está informada. La demografía es descriptiva, no evaluación de equidad ni explicación causal de la caída de rendimiento. No hay metadata utilizable para evaluar diferencias por profesional.

## Longitud y recursos lingüísticos
Con el tokenizer clínico de RoBERTa, 366 de 1835 notas (19.95%) superan 512 tokens; en prueba son 82 de 385 (21.30%). El truncamiento potencial está medido, pero no se demostró que la información descartada explique los errores. Vocabulario y abreviaturas dependen del tamaño del subconjunto y de prácticas institucionales.

La comparación de cobertura `co/core/py` documentada en `dev` no constituye validación clínica formal ni demuestra ganancia predictiva aislada de `Concept_PY`. No se conserva procedencia individual suficiente para cada expresión local ni evidencia completa de qué subconjuntos se consultaron al construirla. Congelar antes del cierre final no demuestra independencia inicial respecto del texto posteriormente asignado a prueba.

## LLM, privacidad y reproducibilidad
El LLM recibió texto y `row_id`, sin etiqueta ni identificador del paciente como campos separados. Eso no acredita por sí mismo desidentificación del texto. La anonimización institucional previa fue informada; su alcance y la verificación de identificadores residuales deben distinguirse de ese testimonio y documentarse junto con autorización y resguardo del uso de una API externa.

La extracción cubre los tres conjuntos. Aplicarla como transformación no demuestra filtración de etiquetas, pero tampoco permite reconstruir toda posible inspección previa de salidas. Faltan registros inequívocos del modelo efectivo y de la configuración exacta de ejecución. Validar JSON comprueba estructura, no exactitud clínica. Repetir llamadas no garantiza reproducir el artefacto original.

La identidad de resultados depende de corpus, índices, reglas, extracción conservada, checkpoints, modelos, columnas, entorno y orden de clases. Código y seeds no bastan para recuperar un checkpoint ausente; `latest` puede apuntar a otra corrida. Véase [Revalidación](REVALIDACION_RESULTADOS_REFERENCIA.md).

## Inferencia e interpretación
Los pesos se seleccionaron entre 231 combinaciones sobre el mismo `dev`; el mejor resultado puede contener optimismo de selección. El ensamble fue el mejor en desarrollo, no en prueba. El desbalance no demuestra por sí solo la causa de esa diferencia.

El bootstrap de 18 pacientes mide incertidumbre del rendimiento del modelo congelado, no validación cruzada ni diferencia pareada entre métodos. No debe afirmarse superioridad estadística a partir de valores puntuales próximos.

Las ramas aisladas describen desempeño, no aporte causal de cada recurso. Core + PY frente a Core + LLM cambia más de un factor y no es ablación aislada de PY. El SHAP histórico del XGBoost reducido no explica el ensamble final. La revisión clínica de retenidas/excluidas y la explicabilidad final siguen pendientes, separadas de cualquier reajuste con prueba.
