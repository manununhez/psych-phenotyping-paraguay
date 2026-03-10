# Justificación de Líneas Base

## Para qué se incluyeron varias líneas base
Se incluyeron tres familias porque responden preguntas distintas:

- Dummy: define el piso mínimo.
- TF-IDF: mide qué logra un baseline lexical clásico sobre texto clínico.
- Transformers (BETO/RoBERTa): evalúan ganancia contextual con modelos preentrenados.

Sin esta escala, el rendimiento del híbrido no sería interpretable.

## Línea base dummy
Su valor no es competitivo. Su valor es metodológico: verificar que el problema no se “resuelve” por distribución de clases o sesgo trivial. Si un modelo propuesto no supera cómodamente esa referencia, no hay argumento científico sólido.

## TF-IDF como baseline de texto
TF-IDF se mantiene como baseline estándar de NLP clínico tabularizado. No depende de `Concept_CO`; opera sobre el texto como representación lexical-estadística.

Esa independencia es importante porque permite separar dos discusiones:

- qué capta un modelo de texto convencional;
- qué fenómenos quedan fuera cuando hay variación regional, abreviaturas locales y cambios semánticos de uso clínico.

El aporte de TF-IDF en esta tesis es justamente marcar ese límite: puede capturar señal útil, pero no resuelve de manera confiable la brecha dialectal por sí solo.

## Baselines Transformer
Los baselines Transformer se incluyeron para evaluar si el contexto subléxico y semántico mejora respecto a enfoques puramente lexicales. No se asumió superioridad automática; se evaluó su comportamiento en el mismo marco de split por paciente y denoising previo.

## Por qué BETO se vuelve referencia contextual
BETO se justifica como baseline Transformer principal por su adecuación al español clínico en este entorno y por estabilidad práctica en la cadena experimental. Esa decisión habilita una reutilización coherente en la arquitectura híbrida:

- primero como baseline autónomo en 04c;
- luego como componente de embeddings en 07/08.

Esa continuidad evita duplicar decisiones semánticas sin control y mantiene trazabilidad entre la fase de líneas base y el modelo final.
