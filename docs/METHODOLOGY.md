# Metodología

## 1. Corpus y Datos

### 1.1 Descripción del Corpus
El estudio utiliza un corpus de **3,127 notas clínicas** del Instituto de Previsión Social (IPS) de Paraguay (2021-2024), correspondientes a **90 pacientes** ambulatorios diagnosticados con Trastornos de Ansiedad (CIE-10: F40-F48) o Depresión (CIE-10: F32-F33).

*   **Distribución:** 2,202 notas de Depresión (70.4%) y 925 de Ansiedad (29.6%).
*   **Longitud:** Media de 150 caracteres por nota.
*   **Anonimización:** Datos pseudoanonimizados preservando fechas y texto clínico.

### 1.2 Preprocesamiento y Denoising
Se aplicó un pipeline de limpieza para maximizar la calidad de los datos:
1.  **Limpieza Estructural:** Eliminación de encabezados, pies de página y plantillas administrativas repetitivas.
2.  **Denoising Rule-Based:** Filtrado automático de notas sin contenido clínico relevante (e.g., "reposición de medicación" sin síntomas). Se preservaron notas con menciones de síntomas, medicamentos o diagnósticos.
3.  **Normalización:** 
    *   *Rule-Based:* Conservadora (preserva mayúsculas, tildes).
    *   *TF-IDF:* Agresiva (lowercase, sin puntuación).
    *   *Transformers:* Tokenización específica del modelo (WordPiece/BPE).

## 2. Estrategia de Partición (Splits)

Para evitar **data leakage** debido a la naturaleza longitudinal de los datos (múltiples notas por paciente), se implementó una partición estricta a **nivel de paciente**:

*   **Train (60%):** 54 pacientes (~1,860 notas).
*   **Dev (20%):** 18 pacientes (~640 notas).
*   **Test (20%):** 18 pacientes (~630 notas). *Reservado para evaluación final.*

Esta estrategia garantiza que todas las notas de un mismo paciente pertenezcan a un único conjunto, simulando un escenario clínico realista de predicción sobre pacientes nuevos.

## 3. Modelos Implementados

### 3.1 Baselines Triviales
*   **Dummy Majority:** Predice siempre la clase mayoritaria (Depresión).
*   **Dummy Stratified:** Predice aleatoriamente respetando la distribución de clases.
*   *Propósito:* Establecer el límite inferior de rendimiento aceptable.

### 3.2 TF-IDF + LinearSVC
Modelo de aprendizaje automático tradicional robusto para textos cortos y ruidosos.
*   **Features:** Character n-grams (3-5).
*   **Clasificador:** Linear Support Vector Classification.
*   **Ventajas:** Alta interpretabilidad, insensible a errores ortográficos, eficiente.

### 3.3 Transformers (Deep Learning)
Modelos de lenguaje pre-entrenados adaptados (fine-tuning) al dominio.
*   **BETO (Spanish BERT):** Pre-entrenado en corpus general en español.
*   **RoBERTa Biomedical/Clinical:** Variantes especializadas (evaluadas preliminarmente).
*   **Configuración:** Fine-tuning de 3 épocas, optimizador AdamW.

### 3.4 Rule-Based (Concept_PY)
Sistema basado en reglas y diccionarios de fenotipos (adaptado de *Spanish Psych Phenotyping*).
*   **Lógica:** Detección de términos clave y manejo de negaciones (ConText).
*   **Limitación:** Dependencia de vocabulario explícito; brecha léxica entre español colombiano (origen) y paraguayo.

## 4. Protocolo de Evaluación

*   **Métrica Principal:** **F1-Score Macro** (media armónica de precision y recall por clase, sin ponderar por soporte), adecuada para el desbalance de clases.
*   **Validación Cruzada:** 5-Fold Stratified Patient-Level sobre el conjunto de entrenamiento+desarrollo (Cross-Validation).
*   **Significancia Estadística:** Comparación de Intervalos de Confianza del 95% (IC95%) mediante bootstrap.
