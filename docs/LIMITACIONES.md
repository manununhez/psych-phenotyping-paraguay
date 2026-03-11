# Limitaciones

El estudio tiene límites que deben explicitarse para evitar sobreinterpretaciones.

Primero, el corpus proviene de un entorno institucional específico. Esto puede introducir sesgo de redacción y limitar la transferibilidad inmediata a otros centros.

Segundo, el etiquetado clínico en EHR no siempre separa con nitidez diagnóstico longitudinal y contenido puntual de una nota. En casos frontera, parte del error puede venir de ambigüedad o solapamiento clínico y no solo del modelo. La comorbilidad explícita queda fuera del objetivo actual y se considera línea de trabajo futuro.

Tercero, la cobertura léxica regional es dinámica. Aunque la adaptación `Concept_PY` y `Concept_PY_Lexicon` mejora robustez, siempre existe riesgo de variantes nuevas fuera de diccionario.

Cuarto, la reproducibilidad computacional depende del entorno disponible (por ejemplo, disponibilidad de `XGBoost` y recursos para baselines Transformer). Por eso los artefactos versionados por corrida son parte del diseño metodológico y no un detalle operativo.

Estas limitaciones no invalidan el enfoque; delimitan su alcance y orientan el trabajo futuro hacia validación externa y auditoría léxica continua.
