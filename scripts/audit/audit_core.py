#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AUDITORÍA CORE (Concept_PY) vs CO (Concept_CO)

Qué hace:
- Extrae "vocabulario" de reglas: literal + tokens de LOWER/IN de patterns.
- Compara CO vs Core: intersección, solo_CO, solo_Core.
- Señala candidatos a regionalismo/no-clínico con heurísticas:
  * palabras con ñ/guarani-ish (opcional), diminutivos, insultos, jerga, etc.
  * tokens muy cortos (<=3) y abreviaturas (alto riesgo FP)
  * tokens genéricos de meds (ej: "acido", "difenil") si están como IN de 1 token
- Chequea "medication_*.json" por tokens sueltos peligrosos en IN.
- Exporta reportes en ./data/outputs/audit_core_YYYYmmdd_HHMMSS/

Uso:
  python scripts/audit/audit_core.py --patterns_root Spanish_Psych_Phenotyping_PY/escribe/patterns --co Concept_CO --core Concept_PY
  python scripts/audit/audit_core.py --patterns_root Spanish_Psych_Phenotyping_PY/escribe/patterns --co Concept_CO --core Concept_PY --lexicon Concept_PY_Lexicon
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from datetime import datetime
import csv

# -------------------------
# Helpers
# -------------------------

def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s)
    return s

def iter_json_files(root: Path):
    if not root.exists():
        return
    for p in root.rglob("*.json"):
        if p.name.startswith(".") or p.name.startswith("._"):
            continue
        yield p

def load_rules(fp: Path) -> list[dict]:
    try:
        obj = json.loads(fp.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(obj, dict) and isinstance(obj.get("target_rules"), list):
        return obj["target_rules"]
    if isinstance(obj, list):
        return obj
    # fallback: dict con listas
    rules = []
    if isinstance(obj, dict):
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                rules.extend(v)
    return rules

def extract_vocab_and_meta(layer_dir: Path):
    """
    Retorna:
      vocab: set[str]  (términos/alias)
      by_token: dict[token] -> {'count':int, 'files':set, 'categories':set}
      categories: set[str]
      file_to_categories: dict[file] -> set[cats]
    """
    vocab = set()
    by_token = {}
    categories = set()
    file_to_categories = {}

    for fp in iter_json_files(layer_dir):
        rules = load_rules(fp)
        cats_here = set()
        for r in rules:
            if not isinstance(r, dict):
                continue

            cat = r.get("category")
            if cat:
                categories.add(str(cat))
                cats_here.add(str(cat))

            lit = r.get("literal")
            if lit:
                vocab.add(norm(lit))

            pat = r.get("pattern", [])
            if isinstance(pat, list):
                for tok in pat:
                    if not isinstance(tok, dict):
                        continue
                    lo = tok.get("LOWER")
                    if isinstance(lo, str):
                        t = norm(lo)
                        vocab.add(t)
                        _acc(by_token, t, fp, cat)
                    elif isinstance(lo, dict) and "IN" in lo and isinstance(lo["IN"], list):
                        for x in lo["IN"]:
                            t = norm(x)
                            vocab.add(t)
                            _acc(by_token, t, fp, cat)

        file_to_categories[str(fp)] = cats_here

    return vocab, by_token, categories, file_to_categories

def _acc(by_token, token: str, fp: Path, cat: str | None):
    d = by_token.setdefault(token, {"count": 0, "files": set(), "categories": set()})
    d["count"] += 1
    d["files"].add(str(fp))
    if cat:
        d["categories"].add(str(cat))

# -------------------------
# Heurísticas de “banderas rojas”
# -------------------------

SHORT = re.compile(r"^[a-z0-9]{1,3}$")
HAS_DIGIT = re.compile(r".*\d+.*")
NON_LETTER = re.compile(r"[^a-z0-9\s]")

def flag_token(token: str) -> list[str]:
    """
    Devuelve etiquetas de riesgo (heurísticas).
    Ajustá si querés más estricto.
    """
    flags = []
    if len(token) <= 2:
        flags.append("too_short")
    if SHORT.match(token):
        flags.append("short_or_abbrev")
    if HAS_DIGIT.match(token):
        flags.append("has_digit")
    if NON_LETTER.search(token):
        flags.append("has_non_alnum")
    # posibles diminutivos/jergas (muy heurístico)
    if token.endswith(("ito", "ita", "azo", "aza")) and len(token) > 4:
        flags.append("diminutive_or_slang_like")
    # términos genéricos problemáticos en meds
    if token in {"acido", "difenil", "hidantoinato"}:
        flags.append("generic_med_token_risk")
    return flags

# -------------------------
# Reporters
# -------------------------

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--patterns_root", type=str, required=True, help="Ej: patterns o escribe/patterns")
    ap.add_argument("--co", type=str, default="Concept_CO")
    ap.add_argument("--core", type=str, default="Concept_PY")
    ap.add_argument("--lexicon", type=str, default="", help="Opcional: Concept_PY_Lexicon")
    ap.add_argument("--out", type=str, default="", help="Salida. Por defecto data/outputs/audit_core_...")
    args = ap.parse_args()

    root = Path(args.patterns_root).resolve()
    co_dir = root / args.co
    core_dir = root / args.core
    lex_dir = (root / args.lexicon) if args.lexicon else None

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.out) if args.out else Path("data/outputs") / f"audit_core_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("patterns_root:", root)
    print("CO:", co_dir, "exists:", co_dir.exists())
    print("CORE:", core_dir, "exists:", core_dir.exists())
    if lex_dir:
        print("LEXICON:", lex_dir, "exists:", lex_dir.exists())
    print("out_dir:", out_dir)

    # Load layers
    co_vocab, co_by, co_cats, _ = extract_vocab_and_meta(co_dir)
    core_vocab, core_by, core_cats, core_file_cats = extract_vocab_and_meta(core_dir)

    # Compare vocab
    inter = co_vocab & core_vocab
    only_co = co_vocab - core_vocab
    only_core = core_vocab - co_vocab

    # Report summary
    summary = {
        "co_vocab": len(co_vocab),
        "core_vocab": len(core_vocab),
        "intersection": len(inter),
        "only_co": len(only_co),
        "only_core": len(only_core),
        "co_categories": len(co_cats),
        "core_categories": len(core_cats),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY:", summary)

    # Flag candidates in only_core (posibles regionalismos/no-clínicos)
    flagged = []
    for t in sorted(only_core):
        fl = flag_token(t)
        if fl:
            meta = core_by.get(t, {"count": 0, "files": set(), "categories": set()})
            flagged.append({
                "token": t,
                "flags": "|".join(fl),
                "count": meta["count"],
                "n_files": len(meta["files"]),
                "categories": ",".join(sorted(meta["categories"]))[:500],
                "example_file": next(iter(meta["files"]), ""),
            })

    write_csv(out_dir / "only_core_flagged.csv", flagged,
              ["token", "flags", "count", "n_files", "categories", "example_file"])

    # Export raw lists (útil para paper)
    (out_dir / "only_core.txt").write_text("\n".join(sorted(only_core)), encoding="utf-8")
    (out_dir / "only_co.txt").write_text("\n".join(sorted(only_co)), encoding="utf-8")
    (out_dir / "intersection.txt").write_text("\n".join(sorted(inter)), encoding="utf-8")

    # Chequeo meds “tokens sueltos” dentro de Core
    meds_rows = []
    for fp_str, cats in core_file_cats.items():
        fp = Path(fp_str)
        if fp.name in {"medication_anxiety.json", "medication_depression.json"}:
            rules = load_rules(fp)
            for r in rules:
                pat = r.get("pattern", [])
                # recolectar IN de 1 token
                for tok in pat:
                    lo = tok.get("LOWER")
                    if isinstance(lo, dict) and "IN" in lo:
                        for x in lo["IN"]:
                            tx = norm(x)
                            fl = flag_token(tx)
                            if "generic_med_token_risk" in fl or "short_or_abbrev" in fl:
                                meds_rows.append({
                                    "file": fp.name,
                                    "token": tx,
                                    "flags": "|".join(fl),
                                    "category": r.get("category", ""),
                                    "literal": r.get("literal", ""),
                                })
    write_csv(out_dir / "meds_tokens_risk.csv", meds_rows,
              ["file", "token", "flags", "category", "literal"])

    # Opcional: comparar Lexicon vs Core para verificar “regionalismos” aislados
    if lex_dir and lex_dir.exists():
        lex_vocab, _, _, _ = extract_vocab_and_meta(lex_dir)
        lex_in_core = sorted(lex_vocab & core_vocab)
        (out_dir / "lexicon_terms_also_in_core.txt").write_text("\n".join(lex_in_core), encoding="utf-8")
        print("Lexicon terms that also appear in Core:", len(lex_in_core))

    print("\n[OK] Reportes generados en:", out_dir)

if __name__ == "__main__":
    main()
