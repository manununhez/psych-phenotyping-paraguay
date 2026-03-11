#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extracción Gemini restringida a la ontología congelada (freeze v2).

Cambios principales:
- Ontología actualizada al freeze v2.
- Normalización robusta por alias hacia la ontología congelada.
- Medicación separada (no se fusiona como diagnóstico).
- Exporta `sintomas` y `sintomas_mapeados` para compatibilidad.
- Guardado incremental con deduplicación por row_id.
"""

from __future__ import annotations

import json
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional

from tqdm import tqdm
from google import genai
from google.genai import types

# ============================================================
# Configuración
# ============================================================

API_KEY = os.environ.get("GEMINI_API_KEY")
if not API_KEY:
    raise RuntimeError("Falta GEMINI_API_KEY en variables de entorno (export GEMINI_API_KEY=...).")

client = genai.Client(api_key=API_KEY)

# Si el script vive en scripts/llm/, parents[2] apunta a la raíz del repo.
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INPUT = REPO_ROOT / "data" / "input_for_gemini.json"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "gemini_extraction.json"

INPUT_FILE = Path(os.environ.get("INPUT_FILE", str(DEFAULT_INPUT)))
OUTPUT_FILE = Path(os.environ.get("OUTPUT_FILE", str(DEFAULT_OUTPUT)))

MODEL_NAME = os.environ.get("MODEL_NAME", "gemini-2.5-pro")
BATCH_SIZE = int(os.environ.get("BATCH_SIZE", "15"))
SLEEP_SECS = float(os.environ.get("SLEEP_SECS", "2.0"))

# ============================================================
# Ontología congelada (freeze v2)
# ============================================================

ALLOWED_FENOTIPOS = [
    "Abulia",
    "Agitacinpsicomotora",
    "Alcoholismo",
    "AngustiaMiedoTemor",
    "Anhedonia",
    "Animodeprimido",
    "Ansiedad",
    "Apata",
    "Apetitoaumentode",
    "Apetitodisminucinde",
    "Autolesin",
    "Bajaconcentracin",
    "Bajaenerga",
    "Compulsiones",
    "Contexto",
    "Culpa",
    "Desesperanza",
    "DespersonalizacinDesrealizacin",
    "Disforia",
    "Fatiga",
    "Hipotimia",
    "Ideacinpersecutoria",
    "Ideacinsuicida",
    "Ideasdemuerte",
    "Intentosuicida",
    "Irritabilidad",
    "Labilidademocional",
    "Llantofcil",
    "Minusvala",
    "Obsesiones",
    "Paranoia",
    "PesoIncremento",
    "PesoPrdida",
    "Pnico",
    "Prospeccindesesperanzada",
    "RetraimientosocialAislamiento",
    "Retrasopsicomotor",
    "Rumiacin",
    "Sntomasansiososgenerales",
    "Sntomasdepresivosgenerales",
    "SntomassomticosEjemplos",
    "Soledad",
    "SueoAlterado",
    "SueoDespertartemprano",
    "SueoHipersomnio",
    "SueoInsomnio",
    "SueoPesadillas",
    "UsoSustancias",
]

# Siglas IPS + formas frecuentes ya normalizadas
MED_MAP = {
    "FXT": "fluoxetina",
    "ALP": "alprazolam",
    "PREG": "pregabalina",
    "PGB": "pregabalina",
    "TRA": "trazodona",
    "CLZ": "clonazepam",
    "CNZ": "clonazepam",
    "VLF": "venlafaxina",
    "VNF": "venlafaxina",
    "QTP": "quetiapina",
    "SERT": "sertralina",
    "FLUOXETINA": "fluoxetina",
    "CLONAZEPAM": "clonazepam",
    "ALPRAZOLAM": "alprazolam",
    "TRAZODONA": "trazodona",
    "QUETIAPINA": "quetiapina",
    "SERTRALINA": "sertralina",
    "VENLAFAXINA": "venlafaxina",
    "PREGABALINA": "pregabalina",
    "AMITRIPTILINA": "amitriptilina",
    "OLANZAPINA": "olanzapina",
    "VALPROATO": "valproato",
    "ZOLPIDEM": "zolpidem",
}

def _norm_key(text: str) -> str:
    if text is None:
        return ""
    text = str(text).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text

# Alias frecuentes observados en corridas previas / lenguaje libre del LLM.
ALIASES_TO_ONTOLOGY = {
    # ansiedad / miedo / preocupación
    _norm_key("ansiedad"): "Ansiedad",
    _norm_key("crisis_ansiedad"): "Pnico",
    _norm_key("panico"): "Pnico",
    _norm_key("miedo"): "AngustiaMiedoTemor",
    _norm_key("angustia"): "AngustiaMiedoTemor",
    _norm_key("preocupacion"): "Ansiedad",
    _norm_key("ansiedad_salud"): "Ansiedad",

    # ánimo / depresión
    _norm_key("tristeza"): "Hipotimia",
    _norm_key("animo_deprimido"): "Animodeprimido",
    _norm_key("animo deprimido"): "Animodeprimido",
    _norm_key("hipotimia"): "Hipotimia",
    _norm_key("apatia"): "Apata",
    _norm_key("anhedonia"): "Anhedonia",
    _norm_key("desesperacion"): "Desesperanza",
    _norm_key("soledad"): "Soledad",
    _norm_key("culpa"): "Culpa",
    _norm_key("llanto"): "Llantofcil",
    _norm_key("irritabilidad"): "Irritabilidad",

    # ideación / suicidio / autolesión
    _norm_key("ideacion_suicida"): "Ideacinsuicida",
    _norm_key("ideas_muerte"): "Ideasdemuerte",
    _norm_key("ideacion_autoagresiva"): "Ideacinsuicida",
    _norm_key("autolesion"): "Autolesin",
    _norm_key("intento_suicida"): "Intentosuicida",
    _norm_key("intento_suicidio"): "Intentosuicida",

    # sueño
    _norm_key("insomnio"): "SueoInsomnio",
    _norm_key("hipersomnia"): "SueoHipersomnio",
    _norm_key("hipersomnio"): "SueoHipersomnio",
    _norm_key("pesadillas"): "SueoPesadillas",
    _norm_key("despertar_temprano"): "SueoDespertartemprano",
    _norm_key("sueno_alterado"): "SueoAlterado",
    _norm_key("sueño_alterado"): "SueoAlterado",
    _norm_key("somnolencia"): "SueoHipersomnio",

    # neurovegetativos / somáticos
    _norm_key("fatiga"): "Fatiga",
    _norm_key("baja_energia"): "Bajaenerga",
    _norm_key("baja energia"): "Bajaenerga",
    _norm_key("alteracion_apetito"): "Apetitodisminucinde",
    _norm_key("aumento_apetito"): "Apetitoaumentode",
    _norm_key("disminucion_apetito"): "Apetitodisminucinde",
    _norm_key("mareos"): "SntomassomticosEjemplos",
    _norm_key("somatizacion"): "SntomassomticosEjemplos",
    _norm_key("sintomas_somaticos"): "SntomassomticosEjemplos",

    # cognitivo / conductual
    _norm_key("baja_concentracion"): "Bajaconcentracin",
    _norm_key("alteracion_concentracion"): "Bajaconcentracin",
    _norm_key("aislamiento_social"): "RetraimientosocialAislamiento",
    _norm_key("retraimiento_social"): "RetraimientosocialAislamiento",
    _norm_key("rumiacion"): "Rumiacin",
    _norm_key("obsesiones"): "Obsesiones",
    _norm_key("compulsiones"): "Compulsiones",
    _norm_key("paranoia"): "Paranoia",
    _norm_key("ideas_persecutorias"): "Ideacinpersecutoria",
    _norm_key("retraso_psicomotor"): "Retrasopsicomotor",
    _norm_key("agitacion_psicomotora"): "Agitacinpsicomotora",
    _norm_key("desrealizacion"): "DespersonalizacinDesrealizacin",
    _norm_key("despersonalizacion"): "DespersonalizacinDesrealizacin",
    _norm_key("disforia"): "Disforia",

    # sustancias / alcohol
    _norm_key("alcohol"): "Alcoholismo",
    _norm_key("consumo_alcohol"): "Alcoholismo",
    _norm_key("uso_sustancias"): "UsoSustancias",
    _norm_key("uso de sustancias"): "UsoSustancias",
    _norm_key("consumo_sustancias"): "UsoSustancias",
    _norm_key("sustancias"): "UsoSustancias",

    # variantes rotas / antiguas
    _norm_key("usodesustancias"): "UsoSustancias",
    _norm_key("alcoholismo"): "Alcoholismo",
}

ALLOWED_LOOKUP = {_norm_key(x): x for x in ALLOWED_FENOTIPOS}

SYSTEM_PROMPT = f"""Actúa como auditor clínico cNLP especializado en Paraguay.

Tu tarea es hacer normalización de conceptos clínicos para alimentar una ontología cerrada (freeze v2).

1) LISTA CERRADA (NO inventar labels)
Mapea síntomas estrictamente a una de estas etiquetas permitidas:
{json.dumps(ALLOWED_FENOTIPOS, ensure_ascii=False)}

2) REGLA DE ORO (aseveración / negación)
- IGNORAR negación administrativa del médico: "sin síntomas", "no presenta", "examen normal".
- Si la negación es atribuible al paciente (por ejemplo: "paciente niega", "refiere que no"), entonces usa:
  niega_<FENOTIPO>

3) MEDICACIÓN
Extrae y normaliza fármacos a nombre genérico si aparecen.
IMPORTANTE:
- NO convertir medicación en diagnóstico.
- NO inventar etiquetas tipo medication_anxiety o medication_depression.
- Solo listar nombres de medicamentos en el campo `medicamentos`.

4) CONTEXTO
La etiqueta `Contexto` solo debe usarse si hay contexto clínicamente relevante que forme parte de la ontología congelada.
No usarla como comodín.

5) VÁLVULA DE ESCAPE
Si detectas hallazgos importantes que no encajan bien en la lista cerrada, escríbelos en:
otros_hallazgos_clinicos

FORMATO DE SALIDA: SOLO JSON válido (sin markdown)
[
  {{
    "row_id": 123,
    "sintomas": ["Ansiedad", "SueoInsomnio", "niega_Ideacinsuicida"],
    "medicamentos": ["fluoxetina"],
    "otros_hallazgos_clinicos": ""
  }}
]
"""

# ============================================================
# IO
# ============================================================

def load_input() -> List[Dict[str, Any]]:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_existing() -> List[Dict[str, Any]]:
    if not OUTPUT_FILE.exists():
        return []
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_incremental(new_items: List[Dict[str, Any]]):
    data = load_existing()
    data.extend(new_items)

    dedup: Dict[int, Dict[str, Any]] = {}
    for it in data:
        if isinstance(it, dict) and it.get("row_id") is not None:
            dedup[int(it["row_id"])] = it

    out = list(dedup.values())
    out.sort(key=lambda x: int(x["row_id"]))

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

# ============================================================
# Normalización
# ============================================================

def _norm_med(m: str) -> Optional[str]:
    if not m:
        return None
    m = str(m).strip()
    if not m:
        return None
    up = m.upper()
    if up in MED_MAP:
        return MED_MAP[up]
    return m.lower()

def normalize_symptom_label(label: str) -> Optional[str]:
    if not label:
        return None
    raw = str(label).strip()
    if not raw:
        return None

    key = _norm_key(raw)

    if key in ALLOWED_LOOKUP:
        return ALLOWED_LOOKUP[key]
    if key in ALIASES_TO_ONTOLOGY:
        return ALIASES_TO_ONTOLOGY[key]
    return None

def sanitize_item(it: Dict[str, Any]) -> Dict[str, Any]:
    row_id = it.get("row_id", None)

    sintomas = it.get("sintomas", None)
    if sintomas is None:
        sintomas = it.get("sintomas_mapeados", []) or []

    meds = it.get("medicamentos", []) or []
    otros = str(it.get("otros_hallazgos_clinicos", "") or "").strip()

    clean_sint: List[str] = []
    for s in sintomas:
        if not s:
            continue
        s = str(s).strip()
        if not s:
            continue

        neg = s.lower().startswith("niega_")
        base = s[len("niega_"):].strip() if neg else s

        mapped = normalize_symptom_label(base)
        if mapped is None:
            otros = (otros + f" | label_fuera_ontologia:{s}").strip(" |")
            continue

        clean_sint.append(f"niega_{mapped}" if neg else mapped)

    clean_meds: List[str] = []
    for m in meds:
        nm = _norm_med(m)
        if nm:
            clean_meds.append(nm)

    clean_sint = sorted(set(clean_sint))
    clean_meds = sorted(set(clean_meds))

    return {
        "row_id": int(row_id) if row_id is not None else None,
        "sintomas": clean_sint,
        "sintomas_mapeados": clean_sint,  # compatibilidad hacia atrás
        "medicamentos": clean_meds,
        "otros_hallazgos_clinicos": otros,
    }

# ============================================================
# Robustez de parseo
# ============================================================

def robust_json_load(txt: str):
    txt = (txt or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(txt)
    except Exception:
        pass

    if "[" in txt and "]" in txt:
        a = txt.find("[")
        b = txt.rfind("]")
        try:
            return json.loads(txt[a:b+1])
        except Exception:
            return None
    return None

# ============================================================
# Llamada al modelo
# ============================================================

def process_batch(
    client,
    model_name: str,
    system_prompt: str,
    batch: List[Dict[str, Any]],
    max_retries: int = 3,
) -> List[Dict[str, Any]]:
    payload = json.dumps(batch, ensure_ascii=False)

    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=model_name,
                contents="Procesa estos registros y devuelve SOLO JSON válido.\n\n" + payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
            )

            data = robust_json_load(getattr(resp, "text", ""))
            if data is None or not isinstance(data, list):
                raise ValueError("Respuesta no parseable como lista JSON.")

            cleaned = [sanitize_item(it) for it in data if isinstance(it, dict)]
            cleaned = [it for it in cleaned if it.get("row_id") is not None]
            return cleaned

        except Exception as e:
            err_str = str(e)

            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                wait = 65
                print(f"[RATE LIMIT] Cuota excedida (intento {attempt+1}/{max_retries}). Pausando {wait}s...")
            else:
                wait = (2 ** attempt) * 2
                print(f"[WARN] batch failed attempt {attempt+1}/{max_retries}: {e} | retry in {wait}s")

            if "NOT_FOUND" in err_str and attempt == 0:
                print("\n[DIAGNÓSTICO] Error 404 detectado. Buscando modelos 'pro' disponibles en tu cuenta/región...")
                try:
                    available = [m.name for m in client.models.list() if "pro" in m.name.lower()]
                    print(f"Modelos permitidos encontrados:\n{available}\nCompárteme esta lista si quieres que ajuste el default.")
                except Exception as ex:
                    print("No se pudieron listar los modelos:", ex)
                raise

            time.sleep(wait)

    return []

# ============================================================
# Main
# ============================================================

def main():
    print(f"🚀 Gemini constrained extraction | model={MODEL_NAME} | batch={BATCH_SIZE}")
    print(f"[INFO] INPUT : {INPUT_FILE}")
    print(f"[INFO] OUTPUT: {OUTPUT_FILE}")
    print(f"[INFO] Ontología freeze v2: {len(ALLOWED_FENOTIPOS)} categorías")

    records = load_input()
    done = {
        int(it.get("row_id"))
        for it in load_existing()
        if isinstance(it, dict) and it.get("row_id") is not None
    }
    to_process = [
        r for r in records
        if isinstance(r, dict) and r.get("row_id") is not None and int(r.get("row_id")) not in done
    ]

    print(f"Total input: {len(records)} | pending: {len(to_process)} | done: {len(done)}")
    if not to_process:
        print("✅ Nada que procesar.")
        return

    for i in tqdm(range(0, len(to_process), BATCH_SIZE), desc="Gemini"):
        batch = to_process[i:i+BATCH_SIZE]
        out = process_batch(client, MODEL_NAME, SYSTEM_PROMPT, batch)
        if out:
            save_incremental(out)
        time.sleep(SLEEP_SECS)

    print(f"✅ Listo. Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()