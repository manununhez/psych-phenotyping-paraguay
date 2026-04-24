# Estrategia de validación clínica

La validación clínica se plantea como revisión cualitativa estructurada con psiquiatría. El objetivo no es reemplazar la evaluación cuantitativa del pipeline, sino contrastar decisiones críticas de diseño en casos reales.

## Qué justifica esta validación
La fase clínica no existe para "corregir" retrospectivamente el benchmark en `dev`. Su justificación es metodológica:

- el rendimiento depende del universo de notas realmente modelado y no solo del clasificador;
- en una tarea diferencial entre ansiedad y depresión, parte del desacuerdo modelo-etiqueta puede reflejar baja separabilidad clínica de la consulta y no solo un error algorítmico;
- antes de abrir `test`, conviene contrastar con juicio experto supuestos sobre señal clínica útil, negación, notas poco diagnósticas y posibles límites del etiquetado actual.

Se priorizan tres focos de revisión:
1. decisiones de denoising (qué se excluye y qué se conserva),
2. interpretación de negación del paciente (`niega_*`) como señal clínica,
3. detección de variantes lingüísticas paraguayas no cubiertas.

## Relación con el desbalance y las métricas
La validación clínica no reemplaza las métricas cuantitativas, pero sí ayuda a interpretarlas correctamente.

El problema sigue desbalanceado a favor de `depresion`, por lo que la lectura principal del proyecto prioriza:

- `macro_f1`;
- `balanced_accuracy`;
- F1 por clase.

Eso evita sobreleer aciertos totales en la clase mayoritaria como si fueran suficiente evidencia de superioridad clínica. La revisión con IPS es especialmente útil para entender:

- por qué `ansiedad` queda más frágil;
- qué errores responden a seguimiento, baja fenomenología o solapamiento clínico;
- y qué notas quizá no deberían entrar a una tarea diferencial tan estricta.

El frente clínico vigente se organiza sobre artefactos ya cerrados en `dev`. La capa operativa actual es `notebooks/analysis/10_validacion_clinica_ips.ipynb`, apoyada por `scripts/export/generar_material_validacion_ips.py`, `scripts/export/curar_dossier_ips.py` y `scripts/export/cerrar_fase_ips.py`. Esta validación se entiende como contraste experto externo y no como una etapa que deba regenerarse de manera rutinaria en cada rerun técnico del pipeline. Además, deja un conjunto curado de casos y preguntas que puede reutilizarse más adelante en la fase de xAI.

En el estudio, esta validación aporta evidencia de validez de contenido y ayuda a justificar por qué ciertas decisiones de extracción se mantienen aun cuando no son triviales desde una lectura puramente lexical.

## Qué no debe hacer esta fase
La validación clínica externa no debe usarse para:

- reabrir libremente la ontología;
- redefinir retrospectivamente la tarea como screening general;
- cambiar la shortlist principal en función de impresiones aisladas;
- sustituir la comparación cuantitativa por anécdotas clínicas.

Su papel correcto es cerrar mejor la interpretación metodológica del sistema antes de `test`, no convertir la fase clínica en una nueva etapa de modelado.
