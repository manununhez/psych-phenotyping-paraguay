# Estrategia de validación clínica

La validación clínica se plantea como revisión cualitativa estructurada con psiquiatría. El objetivo no es reemplazar la evaluación cuantitativa del pipeline, sino contrastar decisiones críticas de diseño en casos reales.

Se priorizan tres focos de revisión:
1. decisiones de denoising (qué se excluye y qué se conserva),
2. interpretación de negación del paciente (`niega_*`) como señal clínica,
3. detección de variantes lingüísticas paraguayas no cubiertas.

El frente clínico vigente se organiza sobre artefactos ya cerrados en `dev`. La capa operativa actual es `notebooks/analysis/10_validacion_clinica_ips.ipynb`, apoyada por `scripts/export/generar_material_validacion_ips.py`, `scripts/export/curar_dossier_ips.py` y `scripts/export/cerrar_fase_ips.py`. Esta validación se entiende como contraste experto externo y no como una etapa que deba regenerarse de manera rutinaria en cada rerun técnico del pipeline.

En el estudio, esta validación aporta evidencia de validez de contenido y ayuda a justificar por qué ciertas decisiones de extracción se mantienen aun cuando no son triviales desde una lectura puramente lexical.
