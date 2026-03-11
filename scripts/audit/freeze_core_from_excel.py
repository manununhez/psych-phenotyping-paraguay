#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build a frozen ZIP of rules using IPS validation Excel as source of additions/cleanup.

Example:
  python scripts/audit/freeze_core_from_excel.py
"""

import argparse
import json, zipfile, shutil, re, unicodedata
from pathlib import Path
import pandas as pd
from collections import defaultdict

# ----------------------------
# Helpers
# ----------------------------
def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"\s+", " ", s)
    return s

STOPWORDS = set(map(norm, [
    "de","del","la","el","los","las","un","una","y","o","a","en","por","para",
    "me","te","se","le","les","lo","ya","no","si","al","con","que","mi","tu",
    "oh"
]))

EXCEPT_CORE = set(map(norm, [
    "chespi","macona","macoña","spa","oh","bpd","malgeniado","malgeniada",
    "ratico","desespero","no se halla"
]))

def load_rules(fp: Path):
    obj = json.loads(fp.read_text(encoding="utf-8"))
    if isinstance(obj, dict) and isinstance(obj.get("target_rules"), list):
        return obj, obj["target_rules"]
    if isinstance(obj, list):
        return {"target_rules": obj}, obj
    # fallback
    return {"target_rules": []}, []

def save_rules(fp: Path, obj: dict):
    fp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def iter_json(root: Path):
    for p in root.rglob("*.json"):
        if p.name.startswith(".") or p.name.startswith("._"):
            continue
        yield p

def extract_categories(core_dir: Path):
    cats=set()
    for fp in iter_json(core_dir):
        _, rules = load_rules(fp)
        for r in rules:
            if isinstance(r, dict) and r.get("category"):
                cats.add(str(r["category"]))
    return cats

def find_excel_cols(df, want):
    # want: lista de keywords
    cols = {c: norm(c) for c in df.columns}
    for c, lc in cols.items():
        if any(w in lc for w in want):
            return c
    return None


def parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[2]
    script_dir = Path(__file__).resolve().parent

    parser = argparse.ArgumentParser(description="Freeze/clean Concept_PY_Lexicon and Concept_PY from IPS Excel.")
    parser.add_argument(
        "--repo-zip",
        default=str(repo_root / "Spanish_Psych_Phenotyping_PY.zip"),
        help="Ruta al ZIP fuente del repositorio de reglas.",
    )
    parser.add_argument(
        "--excel",
        default=str(repo_root / "data" / "IPS_validacion.xlsx"),
        help="Ruta al Excel de validación IPS.",
    )
    parser.add_argument(
        "--out-zip",
        default=str(script_dir / "Spanish_Psych_Phenotyping_PY_FREEZE.zip"),
        help="ZIP de salida.",
    )
    parser.add_argument(
        "--out-report",
        default=str(script_dir / "freeze_report.json"),
        help="Reporte JSON de salida.",
    )
    parser.add_argument(
        "--tmp-dir",
        default=str(script_dir / "_tmp_freeze_repo"),
        help="Directorio temporal de trabajo.",
    )
    return parser.parse_args()


# ----------------------------
# Main
# ----------------------------
def main():
    args = parse_args()

    repo_zip = Path(args.repo_zip)
    excel = Path(args.excel)
    out_zip = Path(args.out_zip)
    out_rep = Path(args.out_report)
    tmp = Path(args.tmp_dir)

    if not repo_zip.exists():
        raise FileNotFoundError(f"No existe --repo-zip: {repo_zip}")
    if not excel.exists():
        raise FileNotFoundError(f"No existe --excel: {excel}")

    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True, exist_ok=True)

    # unzip
    with zipfile.ZipFile(repo_zip, "r") as z:
        z.extractall(tmp)

    patterns = tmp / "Spanish_Psych_Phenotyping_PY" / "escribe" / "patterns"
    core_dir = patterns / "Concept_PY"
    co_dir   = patterns / "Concept_CO"
    lex_dir  = patterns / "Concept_PY_Lexicon"

    report = {
        "paths": {
            "patterns": str(patterns),
            "core": str(core_dir),
            "co": str(co_dir),
            "lexicon": str(lex_dir),
        },
        "lexicon": {"removed_rules": 0, "removed_py_prefix": 0, "removed_source_keys": 0, "added_missing_terms": 0},
        "core": {"removed_exception_rules": 0, "exceptions_removed": []},
    }

    # read excel - sheet PY terms
    xls = pd.ExcelFile(excel)
    df_py = pd.read_excel(xls, sheet_name="03_Términos_Variante_Paraguaya")

    # detect columns robustly
    col_term = find_excel_cols(df_py, ["termino", "término", "expres", "frase", "literal"])
    col_pheno = find_excel_cols(df_py, ["id interno", "json", "category", "fenotipo", "categoria"])

    if col_term is None:
        raise RuntimeError("No pude detectar la columna de términos en hoja 03_Términos_Variante_Paraguaya.")

    # build set of lexicon literals present
    lex_literals = set()
    lex_by_cat = defaultdict(list)

    for fp in iter_json(lex_dir):
        obj, rules = load_rules(fp)
        changed = False

        for r in rules:
            if not isinstance(r, dict):
                continue

            # remove invalid key 'source'
            if "source" in r:
                r.pop("source", None)
                report["lexicon"]["removed_source_keys"] += 1
                changed = True

            # strip "PY: " prefix in literal
            lit = r.get("literal", "")
            if isinstance(lit, str) and lit.strip().lower().startswith("py:"):
                r["literal"] = lit.split(":", 1)[1].strip()
                report["lexicon"]["removed_py_prefix"] += 1
                changed = True

            cat = r.get("category")
            if cat:
                lex_by_cat[str(cat)].append(r)

            if r.get("literal"):
                lex_literals.add(norm(r["literal"]))

        # remove stopword-only single token rules
        new_rules = []
        for r in rules:
            if not isinstance(r, dict):
                continue
            pat = r.get("pattern", [])
            if isinstance(pat, list) and len(pat) == 1 and isinstance(pat[0], dict):
                lo = pat[0].get("LOWER")
                if isinstance(lo, str) and norm(lo) in STOPWORDS:
                    report["lexicon"]["removed_rules"] += 1
                    changed = True
                    continue
            new_rules.append(r)
        obj["target_rules"] = new_rules

        if changed:
            save_rules(fp, obj)

    # Ensure PY terms from Excel exist in lexicon; add missing
    # We map phenotype/category by matching to existing core categories if possible
    core_cats = extract_categories(core_dir)
    core_cats_norm = {norm(c): c for c in core_cats}

    missing_rows = []
    for _, row in df_py.iterrows():
        term = row.get(col_term, "")
        if pd.isna(term) or not str(term).strip():
            continue
        tnorm = norm(term)
        if tnorm in lex_literals:
            continue

        # decide category
        cat = None
        if col_pheno and row.get(col_pheno) and not pd.isna(row.get(col_pheno)):
            raw = str(row.get(col_pheno)).strip()
            # if already a category key
            if raw in core_cats:
                cat = raw
            else:
                cand = core_cats_norm.get(norm(raw))
                if cand:
                    cat = cand

        if not cat:
            # fallback: put in Depresion/Sntomasdepresivosgenerales (neutral) – better than losing it
            cat = "Sntomasdepresivosgenerales" if "Sntomasdepresivosgenerales" in core_cats else next(iter(core_cats))

        missing_rows.append((term, cat))

    # add missing terms into lexicon files
    # place under Depresion by default unless cat belongs to Ansiedad folder in Core
    # detect folder by searching existing Core JSON location
    cat_to_folder = {}
    for fp in iter_json(core_dir):
        _, rules = load_rules(fp)
        for r in rules:
            if isinstance(r, dict) and r.get("category"):
                cat_to_folder[str(r["category"])] = fp.parent.name  # Ansiedad/Depresion/Contexto

    for term, cat in missing_rows:
        folder = cat_to_folder.get(cat, "Depresion")
        target_fp = lex_dir / folder / f"{cat}.json"
        if not target_fp.exists():
            target_fp.parent.mkdir(parents=True, exist_ok=True)
            obj = {"target_rules": []}
        else:
            obj, _ = load_rules(target_fp)

        tokens = [t for t in re.split(r"\s+", norm(term)) if t]
        pattern = [{"LOWER": tok} for tok in tokens] if tokens else [{"LOWER": norm(term)}]

        obj["target_rules"].append({
            "literal": str(term).strip(),
            "category": cat,
            "pattern": pattern
        })
        save_rules(target_fp, obj)
        report["lexicon"]["added_missing_terms"] += 1

    # Purify CORE: remove clearly non-universal exception rules (if present)
    for fp in iter_json(core_dir):
        obj, rules = load_rules(fp)
        changed = False
        new_rules = []
        for r in rules:
            if not isinstance(r, dict):
                continue

            lit = norm(r.get("literal", ""))
            cat = str(r.get("category", ""))

            # detect exception by literal
            remove = lit in EXCEPT_CORE

            # detect exception by pattern exact phrase "no se halla"
            if not remove:
                pat = r.get("pattern", [])
                if isinstance(pat, list) and len(pat) >= 2:
                    seq = []
                    for tok in pat:
                        lo = tok.get("LOWER")
                        if isinstance(lo, str):
                            seq.append(norm(lo))
                        elif isinstance(lo, dict) and "IN" in lo:
                            # take first for sequence check
                            seq.append(norm(lo["IN"][0]))
                    if " ".join(seq) == "no se halla":
                        remove = True

            if remove:
                report["core"]["removed_exception_rules"] += 1
                report["core"]["exceptions_removed"].append({"file": str(fp), "category": cat, "literal": r.get("literal", "")})
                changed = True
                continue

            new_rules.append(r)

        if changed:
            obj["target_rules"] = new_rules
            save_rules(fp, obj)

    out_rep.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # rezip
    if out_zip.exists():
        out_zip.unlink()

    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in (tmp / "Spanish_Psych_Phenotyping_PY").rglob("*"):
            if p.is_dir():
                continue
            # skip macos junk
            if "__MACOSX" in str(p):
                continue
            rel = p.relative_to(tmp)
            z.write(p, rel.as_posix())

    print("[OK] Zip:", out_zip)
    print("[OK] Report:", out_rep)
    print("Lexicon added missing terms:", report["lexicon"]["added_missing_terms"])
    print("Core removed exception rules:", report["core"]["removed_exception_rules"])

if __name__ == "__main__":
    main()
