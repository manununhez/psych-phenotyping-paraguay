# Limitaciones

El estudio tiene límites que deben explicitarse para evitar sobreinterpretaciones.

Primero, el corpus proviene de un entorno institucional específico. Esto puede introducir sesgo de redacción y limitar la transferibilidad inmediata a otros centros.

Segundo, el corpus mezcla consultas con distinta densidad fenomenológica. Hay notas administrativas, reposiciones, seguimientos breves y registros donde la continuidad terapéutica domina sobre la fenomenología activa. El denoising mitiga ese problema, pero no garantiza que toda nota retenida sea igualmente diagnóstica para una tarea diferencial fina.

Tercero, el etiquetado clínico en EHR no siempre separa con nitidez diagnóstico longitudinal y contenido puntual de una nota. En casos frontera, parte del error puede venir de ambigüedad clínica, de superposición entre ansiedad y depresión, o de una discordancia entre etiqueta a nivel paciente y fenómeno expresado en la consulta puntual. La comorbilidad explícita queda fuera del objetivo actual y se considera línea de trabajo futuro.

Cuarto, parte de la señal psiquiátrica aparece mezclada con sueño, medicación, somatización o clínica médica concomitante. Ese solapamiento no es un defecto del corpus sino una propiedad real del problema, pero reduce la separabilidad limpia entre clases y obliga a interpretar con cuidado los errores del modelo.

Quinto, la cobertura léxica regional es dinámica. Aunque la adaptación `Concept_Core` + `Concept_PY` mejora robustez, siempre existe riesgo de variantes nuevas fuera de diccionario, abreviaturas locales todavía no capturadas o expresiones clínicas cuyo valor semántico cambie con el contexto.

Sexto, la reproducibilidad computacional depende del entorno disponible, en particular para `XGBoost` y los baselines Transformer. Por eso los artefactos versionados por corrida son parte del diseño metodológico y no un detalle operativo.

Séptimo, el universo `denoised` debe entenderse como una decisión metodológica explícita de esta fase y no como una limpieza neutral del corpus. Su propósito es alinear el espacio experimental con la tarea diferencial, pero parte del criterio de elegibilidad depende de la misma política de aseveración clínica usada luego para construir reglas explícitas. Por eso el cierre posterior debe complementarse con una sensibilidad fuera del universo purgado, sin usarla para reabrir selección de modelos.

Octavo, aunque la partición por paciente evita filtración longitudinal entre conjuntos, la evaluación principal sigue realizándose a nivel de nota. Esto permite que pacientes muy documentados pesen más dentro de un mismo split. La auditoría complementaria en `dev` confirma que esta concentración no es irrelevante y justifica reportar métricas `patient-weighted` y `patient-aggregated` como lectura secundaria.

Noveno, el corpus crudo contiene variables como sexo y fecha de nacimiento, pero estas no forman parte del dataset experimental ni del pipeline principal de modelado. Por tanto, los resultados deben interpretarse como clasificación textual supervisada sobre el universo vigente, no como desempeño ajustado por subgrupos. La auditoría descriptiva de subgrupos en `dev` muestra heterogeneidad exploratoria, pero con tamaños pequeños y sin permitir inferencias de equidad ni causalidad.

Décimo, la ausencia de grupo de control es una delimitación metodológica real. El trabajo actual resuelve diagnóstico diferencial entre dos clases clínicas dentro de una población ya psiquiátrica; no resuelve una tarea de screening general caso/no caso.

Undécimo, la explicabilidad no debe plantearse como interpretación clínica de cada dimensión latente de los embeddings. La estrategia compatible con el modelo final consiste en aplicar SHAP sobre el clasificador tabular XGB y leer las contribuciones por familias de variables, separando `ctx_beto_*` de `rule_*`. La auditoría actual muestra que el peso predictivo global del modelo final en `dev` está dominado por el bloque contextual, mientras que las reglas clínicas aportan menos globalmente aunque conservan valor para trazabilidad local y análisis de casos.

Estas limitaciones no invalidan el enfoque; delimitan su alcance y orientan el trabajo futuro hacia validación externa y auditoría léxica continua.
