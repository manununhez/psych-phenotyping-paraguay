# Limitaciones del Estudio

Este documento detalla las limitaciones metodológicas y técnicas del proyecto, cruciales para la interpretación de los resultados y la definición de trabajos futuros.

## 1. Limitaciones del Dataset

### 1.1 Tamaño de la Muestra
*   **Descripción:** El estudio se basó en 90 pacientes únicos (3,127 notas).
*   **Impacto:** Aunque suficiente para demostrar la viabilidad técnica (proof-of-concept), el tamaño es pequeño para estándares de Deep Learning. Esto se refleja en los intervalos de confianza amplios (±12 puntos en F1) y limita la capacidad de fine-tuning de modelos grandes como BETO.
*   **Mitigación:** Uso de validación cruzada estratificada y técnicas de regularización.

### 1.2 Sesgo Institucional
*   **Descripción:** Todos los datos provienen de una única institución (IPS Central, Asunción).
*   **Impacto:** Los resultados pueden no ser generalizables a poblaciones rurales o a otros sistemas de salud con diferentes prácticas de documentación.
*   **Futuro:** Se requiere validación externa multicéntrica.

### 1.3 Ausencia de Grupo Control
*   **Descripción:** El dataset solo incluye casos diagnosticados con Ansiedad o Depresión. No hay casos "sanos" o "neutrales" puros.
*   **Impacto:** El sistema es un clasificador binario (A vs. B) y no una herramienta de screening poblacional (Sano vs. Patológico). Asume *a priori* que existe una patología.

## 2. Limitaciones de Etiquetado

### 2.1 Filosofía de Etiquetado (Paciente vs. Consulta)
*   **Problema:** Se identificaron notas administrativas (e.g., "reposición") etiquetadas con el diagnóstico del paciente (e.g., "Ansiedad").
*   **Ambigüedad:** No está claro si la etiqueta debe reflejar el *contenido de la nota* (nivel consulta) o el *diagnóstico de base* (nivel paciente).
*   **Impacto:** Introduce ruido en el entrenamiento, ya que el modelo intenta asociar textos vacíos de síntomas con patologías.

### 2.2 Comorbilidad
*   **Problema:** Muchos pacientes presentan síntomas mixtos. La clasificación binaria forzada ignora la realidad clínica de la comorbilidad ansioso-depresiva.
*   **Impacto:** Casos frontera pueden ser penalizados injustamente como errores del modelo.

## 3. Limitaciones Técnicas

### 3.1 Brecha de Vocabulario (Gap Dialectal)
*   **Descripción:** El sistema Rule-Based original fue diseñado con vocabulario colombiano.
*   **Hallazgo:** Se identificó una brecha del 75% en términos de ansiedad en Paraguay (e.g., uso de "preocupación constante" vs. "ansiedad generalizada").
*   **Impacto:** Rendimiento catastrófico del sistema basado en reglas para la clase Ansiedad sin adaptación local.

### 3.2 Negación
*   **Descripción:** La detección de negación es compleja. Frases como "niega ansiedad" pueden ser síntomas de falta de insight o mecanismos de defensa, no necesariamente ausencia de patología.
*   **Decisión:** Se optó por incluir negaciones en el dataset de entrenamiento, pero esto requiere validación clínica específica.
