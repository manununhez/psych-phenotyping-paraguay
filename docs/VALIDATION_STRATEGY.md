# Estrategia de Validación con Psiquiatras

Este documento detalla la estrategia para validar clínicamente los resultados del sistema, enfocándose en la calidad del filtrado (denoising), el manejo de negaciones y la identificación de vocabulario local.

## 1. Objetivo de la Validación
Validar las decisiones críticas de diseño del pipeline y la calidad de los datos procesados, específicamente:
1.  **Denoising (Filtrado):** Confirmar que no se están eliminando casos con información clínica relevante (Falsos Negativos del filtro) y que los casos mantenidos son útiles (Falsos Positivos del filtro).
2.  **Negación:** Validar la inclusión de síntomas negados (e.g., "niega ansiedad") como señal clínica relevante (falta de insight vs. ausencia de patología).
3.  **Vocabulario:** Identificar términos coloquiales del español paraguayo no capturados por el sistema.

## 2. Metodología de Selección de Casos
Se seleccionó una muestra estratégica de **25 casos** del conjunto de desarrollo, divididos en tres grupos clave:

### Grupo A: Exclusiones "Sospechosas" (Posibles Falsos Negativos del Denoising)
*   **Criterio:** Notas eliminadas por el filtro de denoising pero con longitud considerable (>50 caracteres).
*   **Pregunta al Psiquiatra:** *"¿Hay información clínica en estos textos que nuestro sistema borró por error?"*
*   **Hipótesis:** Podrían contener descripciones fenomenológicas complejas o vocabulario local no detectado por las reglas actuales.

### Grupo B: Inclusiones con Negación
*   **Criterio:** Notas mantenidas que contienen términos de negación explícita ("no", "niega", "sin").
*   **Pregunta al Psiquiatra:** *"El sistema incluyó este caso donde el paciente dice 'no tener ansiedad'. ¿Es correcto considerarlo evidencia de patología (ej. falta de insight) o debería ser descartado?"*
*   **Hipótesis:** La negación en psiquiatría a menudo indica un síntoma (e.g., paciente maníaco negando problemas) o un motivo de consulta relevante, justificando su inclusión.

### Grupo C: Inclusiones Cortas (Posibles Falsos Positivos del Denoising)
*   **Criterio:** Notas muy breves (<100 caracteres) que pasaron el filtro.
*   **Pregunta al Psiquiatra:** *"¿Este texto corto es suficiente para justificar una etiqueta diagnóstica?"*
*   **Hipótesis:** Validar el umbral mínimo de información necesaria para una clasificación confiable.

## 3. Preguntas Clave para la Reunión

### Sobre el Filtrado
1.  **Reposición de Medicación:** *"Hemos eliminado automáticamente notas que solo dicen 'reposición'. ¿Existe algún escenario donde esto contenga información clínica implícita?"*
2.  **Vocabulario Local:** *"En los casos excluidos, ¿ven algún término coloquial paraguayo para 'tristeza' o 'ansiedad' que se nos haya pasado?"*

### Sobre Negación e Insight
3.  **Validez de la Negación:** *"¿Están de acuerdo con que 'niega ansiedad' puede ser un indicador relevante en su población, o deberíamos ser más estrictos?"*
4.  **Disimulación:** *"¿Cómo documentan la diferencia entre un paciente eutímico y uno que disimula síntomas?"*

### Sobre Comorbilidad
5.  **Etiquetado:** *"Hemos notado casos etiquetados como 'Depresión' que solo mencionan síntomas de ansiedad. ¿Es común etiquetar la comorbilidad bajo el diagnóstico principal?"*

## 4. Instrumento de Validación
Se utiliza el archivo `VALIDACION_PSIQUIATRAS_POST_DENOISING.xlsx`, que contiene los casos seleccionados y columnas para:
*   **Validación:** Acuerdo/Desacuerdo con la decisión del sistema.
*   **Comentarios:** Observaciones cualitativas y términos nuevos identificados.
