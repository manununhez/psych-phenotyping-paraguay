# Narrativa de la Brecha Léxica

## Punto de partida: el problema no era accesorio
La brecha léxica no apareció como observación secundaria en el análisis de errores. Fue el obstáculo principal para sostener extracción clínica estable en notas paraguayas. El sistema original (`Concept_CO`) ofrecía una base útil como referencia histórica, pero arrastraba supuestos lingüísticos que no se trasladaban de forma limpia al corpus IPS.

## Por qué `Concept_CO` resultó insuficiente
El límite no fue solamente “faltan palabras”. Hubo tres frentes simultáneos:

- expresiones colombianas con baja presencia local;
- variantes paraguayas y jopará fuera de cobertura;
- abreviaturas y usos institucionales del IPS que alteran la forma textual de síntomas y contexto.

En ese escenario, una regla técnicamente correcta podía ser clínicamente ciega en Paraguay, y una coincidencia lexical podía ser un falso positivo en plantilla.

## Limpieza de `Concept_PY (Core)`
La capa Core no se construyó para “agregar términos”. Se diseñó para reducir fragilidad:

- eliminación de disparadores ambiguos;
- ajuste de anclajes para disminuir ruido administrativo;
- depuración de reglas con propensión a activaciones fuera de contexto clínico.

La idea fue estabilizar primero el comportamiento del sistema y recién después expandir cobertura regional.

## Construcción de `Concept_PY_Lexicon`
Sobre esa base más robusta, `Concept_PY_Lexicon` cumplió el rol de adaptación lingüística específica:

- incorporación de variantes paraguayas;
- inclusión de abreviaturas frecuentes en la práctica local;
- consolidación de equivalencias semánticas observadas en el corpus.

La capa lexicon no reemplaza Core. La complementa para cubrir fenómenos regionales que Core, por diseño, no pretende abarcar completamente.

## Rol del LLM en la auditoría léxica
El LLM se usó como apoyo metodológico, no como árbitro diagnóstico. Su aporte estuvo en verificar consistencia semántica durante la auditoría:

- confirmar coloquialismos;
- detectar colombianismos heredados de `Concept_CO`;
- contrastar variantes paraguayas observadas en notas;
- evaluar equivalencias entre formas lexicales distintas.

Esta asistencia permitió acelerar revisión y reducir ambigüedad semántica, sin alterar la regla central del proyecto: la inferencia clínica final no depende de una decisión opaca del LLM.

## Resultado metodológico de la narrativa
La secuencia `Concept_CO -> Concept_PY -> Concept_PY_Lexicon` quedó justificada como estrategia científica y no como edición incremental sin criterio. Primero se sostuvo reproducibilidad histórica, luego robustez, y finalmente adaptación regional.
