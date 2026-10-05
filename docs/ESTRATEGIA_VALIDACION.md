# Estrategia de validación clínica

## Alcance y estado
La revisión experta es una fase secundaria de interpretación, no una nueva selección de modelos. Hay materiales y casos preparados para revisión externa; generarlos o enviarlos no equivale a validación completada. No se documenta una revisión experta completa para estimar la correctitud del denoising ni validar cada expresión local.

`notebooks/analysis/10_validacion_clinica_ips.ipynb` organiza materiales desde artefactos históricos cerrados en `dev`, con los generadores versionados de `scripts/export/`. No reentrena ni sustituye la evaluación final. SHAP mínimo de `09c` corresponde a un híbrido histórico; la explicabilidad del ensamble final sigue pendiente.

## Preguntas de revisión
Conviene distinguir cuatro objetos:

1. **Denoising:** si las retenidas contienen evidencia útil y las excluidas contienen señal omitida por el filtro.
2. **Aseveración:** si las menciones son del paciente, actuales, afirmadas o negadas, en vez de históricas, hipotéticas, familiares o de plantilla.
3. **Diccionario:** si Core y PY capturan el concepto en contexto, incluidos medicamentos y expresiones regionales.
4. **Clasificación:** si los desacuerdos reflejan errores del modelo, ambigüedad clínica o límites de la etiqueta. No se presume una explicación antes de revisar.

## Diseño para auditar el filtro
La muestra debe incluir retenidas y excluidas por clase y partición. Un diseño orientativo es revisar 120 notas: diez por cada una de doce celdas (dos clases, tres particiones y dos estados de retención), combinando casos aleatorios y dirigidos. La revisión sigue pendiente; este diseño no constituye un resultado clínico ni una etapa obligatoria del pipeline público.

El formulario debería registrar señal relevante, concepto, sujeto, temporalidad, negación, motivo de inclusión/exclusión, desacuerdo con el extractor y decisión del revisor. La primera lectura debe evitar mostrar la predicción; una segunda puede revisar la regla activada. Dos revisores y adjudicación permiten medir acuerdo. Los casos dirigidos deben analizarse aparte: no estiman tasas representativas sin ponderar el diseño.

Puede complementarse con la lectura cualitativa solicitada de notas de ansiedad y con casos de información perdida al truncar. Una inspección pequeña permite formular hipótesis, pero no prueba causalidad ni valida todo el filtro.

## Controles descriptivos y técnicos
El EDA de `01` aporta distribuciones globales y por partición: pacientes, notas, clases, sexo, edad con histogramas e intervalos, consultas por paciente, longitud, tokens, vocabulario, duplicados y retención. Permite observar diferencias, no demostrar su efecto sobre el rendimiento.

El cierre `10` verifica checkpoint, tokenizer, longitud máxima, clases, alineación de probabilidades y reproducción en `dev`. Son controles computacionales distintos de validación clínica. No hay metadata suficiente para comparar profesionales; ese análisis no debe presentarse como realizado.

## Límites y resguardo
Revisar prueba después del cierre solo permite interpretar resultados congelados; no habilita cambiar reglas, instrucciones LLM, modelos, pesos o umbral y seguir llamando independiente a esa evaluación. Un cambio requeriría otro protocolo y datos de evaluación independientes.

Textos, formularios y observaciones individuales son material restringido. Antes de compartirlos debe verificarse desidentificación y alcance de la autorización. Los documentos públicos deben contener resultados agregados, sin notas ni identificadores de pacientes.
