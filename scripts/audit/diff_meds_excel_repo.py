#!/usr/bin/env python3
"""Compare medication names between IPS Excel and repository JSON rules."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


def strip(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


def load_meds(path: Path, include_aliases: bool = True) -> set[str]:
    """
    include_aliases=True:
      - incluye abreviaturas (alp, dzp, etc.) en el set JSON
    include_aliases=False:
      - devuelve solo nombres canónicos y frases compuestas
    """
    obj = json.loads(path.read_text(encoding="utf-8"))
    meds: set[str] = set()
    aliases: set[str] = set()

    for r in obj.get("target_rules", []):
        pat = r.get("pattern", [])

        # 1) Extraer LOWER.IN (lista)
        for tok in pat:
            lo = tok.get("LOWER")
            if isinstance(lo, dict) and "IN" in lo:
                for x in lo["IN"]:
                    sx = strip(x)
                    # heurística simple: abreviaturas cortas suelen ser alias
                    if len(sx) <= 3 or re.fullmatch(r"[a-z]{1,4}\d*", sx or ""):
                        aliases.add(sx)
                    else:
                        meds.add(sx)
            elif isinstance(lo, str):
                meds.add(strip(lo))

        # 2) Detectar bigramas exactos: dos tokens LOWER consecutivos
        lowers = []
        for tok in pat:
            lo = tok.get("LOWER")
            if isinstance(lo, str):
                lowers.append(strip(lo))
            elif isinstance(lo, dict) and "IN" in lo:
                lowers.append(tuple(strip(x) for x in lo["IN"]))

        if len(lowers) == 2:
            w1, w2 = lowers
            if isinstance(w1, tuple) and isinstance(w2, str):
                for a in w1:
                    meds.add(f"{a} {w2}".strip())
            elif isinstance(w1, str) and isinstance(w2, str):
                meds.add(f"{w1} {w2}".strip())
            elif isinstance(w1, str) and isinstance(w2, tuple):
                for b in w2:
                    meds.add(f"{w1} {b}".strip())

    return meds | aliases if include_aliases else meds


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    default_excel = repo_root / "data" / "IPS_validacion.xlsx"
    default_dep = (
        repo_root
        / "Spanish_Psych_Phenotyping_PY"
        / "escribe"
        / "patterns"
        / "Concept_PY"
        / "Depresion"
        / "medication_depression.json"
    )
    default_anx = (
        repo_root
        / "Spanish_Psych_Phenotyping_PY"
        / "escribe"
        / "patterns"
        / "Concept_PY"
        / "Ansiedad"
        / "medication_anxiety.json"
    )

    parser = argparse.ArgumentParser(description="Diff meds between Excel and JSON rules.")
    parser.add_argument("--excel", default=str(default_excel), help="Ruta del Excel IPS_validacion.xlsx")
    parser.add_argument("--dep-json", default=str(default_dep), help="Ruta medication_depression.json")
    parser.add_argument("--anx-json", default=str(default_anx), help="Ruta medication_anxiety.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    excel = Path(args.excel)
    dep_json = Path(args.dep_json)
    anx_json = Path(args.anx_json)

    df = pd.read_excel(excel, sheet_name="04_Medicamentos", header=1)
    df.columns = [str(c).strip() for c in df.columns]
    df = df[df["Medicamento"].notna()]
    meds_excel = set(strip(x) for x in df["Medicamento"].tolist())

    m_dep = load_meds(dep_json, include_aliases=False)
    m_anx = load_meds(anx_json, include_aliases=False)
    m_json = m_dep | m_anx

    missing = sorted(meds_excel - m_json)
    extra = sorted(m_json - meds_excel)

    print("EXCEL meds:", len(meds_excel))
    print("JSON meds:", len(m_json))
    print("Missing in JSON:", len(missing), missing[:50])
    print("Extra in JSON:", len(extra), extra[:50])


if __name__ == "__main__":
    main()
