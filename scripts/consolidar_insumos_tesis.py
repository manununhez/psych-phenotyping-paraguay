#!/usr/bin/env python3
"""
Consolida insumos metodológicos y de resultados para tesis.

Objetivo:
- detectar artefactos vigentes (priorizando punteros latest/manifiestos);
- validar consistencia entre artefactos clave;
- exportar un paquete consolidado y trazable para redacción.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd


BACKBONE_TO_MODEL = {
    "beto": "BETO",
    "roberta_clinical": "ROBERTA_CLINICAL",
    "roberta_biomedical": "ROBERTA_BIOMEDICAL",
}
MODEL_TO_BACKBONE = {v: k for k, v in BACKBONE_TO_MODEL.items()}


@dataclass
class ResolverResult:
    componente: str
    path: str | None
    estado: str
    fuente: str
    detalle: dict[str, Any]


def _now_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _safe_read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        if not path.exists():
            return None, "no_existe"
        if path.stat().st_size == 0:
            return None, "vacio"
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:  # pragma: no cover - robustez
        return None, f"json_invalido: {e}"


def _latest_dirs(base: Path, pattern: str) -> list[Path]:
    return sorted([p for p in base.glob(pattern) if p.is_dir()], key=lambda p: p.stat().st_mtime, reverse=True)


def _latest_files(base: Path, pattern: str) -> list[Path]:
    return sorted([p for p in base.glob(pattern) if p.is_file()], key=lambda p: p.stat().st_mtime, reverse=True)


def _to_upper_model(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    up = raw.upper()
    if up in {"BETO", "ROBERTA_CLINICAL", "ROBERTA_BIOMEDICAL"}:
        return up
    low = raw.lower()
    return BACKBONE_TO_MODEL.get(low)


def _git_info(repo: Path) -> dict[str, Any]:
    out = {"commit": None, "commit_short": None, "branch": None, "dirty": None}
    try:
        out["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
        out["commit_short"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo, text=True
        ).strip()
        out["branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo, text=True
        ).strip()
        out["dirty"] = bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True).strip()
        )
    except Exception:
        pass
    return out


def _resolver_cierre_dev(outputs_dir: Path, warnings: list[str]) -> ResolverResult:
    dirs = _latest_dirs(outputs_dir, "cierre_modelos_dev_*")
    required = {
        "decision_modelo_final.json",
        "ranking_modelos_dev.csv",
        "rubrica_seleccion_modelos.csv",
        "lista_modelos_para_test.json",
    }
    for d in dirs:
        if not required.issubset({p.name for p in d.iterdir() if p.is_file()}):
            continue
        decision_path = d / "decision_modelo_final.json"
        decision, err = _safe_read_json(decision_path)
        if err or decision is None:
            continue
        if str(decision.get("split_decision", "")).lower() != "dev":
            warnings.append(f"Cierre descartado por split no-dev: {d}")
            continue
        return ResolverResult(
            componente="cierre_formal_dev",
            path=str(d),
            estado="COMPLETO",
            fuente="patron_timestamp",
            detalle={"decision": decision, "decision_path": str(decision_path), "ranking_path": str(d / "ranking_modelos_dev.csv")},
        )
    return ResolverResult(
        componente="cierre_formal_dev",
        path=None,
        estado="FALTANTE",
        fuente="patron_timestamp",
        detalle={},
    )


def _resolver_manifest_backbone(outputs_dir: Path) -> ResolverResult:
    latest = outputs_dir / "backbone_artifacts_manifest_latest.json"
    payload, err = _safe_read_json(latest)
    if payload is not None:
        return ResolverResult("manifiesto_backbone", str(latest), "COMPLETO", "latest_json", payload)
    return ResolverResult("manifiesto_backbone", None, "FALTANTE", "latest_json", {"error": err})


def _resolver_transformer_selection(
    outputs_dir: Path,
    cierre_decision: dict[str, Any],
    manifest: dict[str, Any],
    warnings: list[str],
) -> ResolverResult:
    candidates: list[tuple[str, Path]] = []

    # Prioridad 1: latest estable
    latest_sel = outputs_dir / "transformer_baseline_selection_latest.json"
    if latest_sel.exists():
        candidates.append(("latest_json", latest_sel))

    # Prioridad 1b: referencia explícita en cierre
    ref_cierre = ((cierre_decision.get("seleccion_transformer_04c") or {}).get("path") or "").strip()
    if ref_cierre:
        candidates.append(("referencia_cierre", Path(ref_cierre)))

    # Prioridad 1c: manifiesto backbone
    ref_manifest = (((manifest.get("latest_valid_selection") or {}).get("ruta")) or "").strip()
    if ref_manifest:
        candidates.append(("manifest_latest", Path(ref_manifest)))

    # Prioridad 2: scan
    for p in _latest_files(outputs_dir, "transformer_baseline_selection_*.json"):
        if p.name == "transformer_baseline_selection_latest.json":
            continue
        candidates.append(("scan_timestamp", p))

    seen: set[str] = set()
    valid_options: list[dict[str, Any]] = []
    for fuente, path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)

        payload, err = _safe_read_json(path)
        if payload is None:
            continue
        best_raw = ((payload.get("mejor_transformer_baseline") or {}).get("modelo")) or ""
        best_model = _to_upper_model(best_raw)
        modelos = payload.get("modelos_comparados")
        eval_split = str(payload.get("eval_split", "")).lower()
        if best_model and isinstance(modelos, list) and len(modelos) > 0 and eval_split == "dev":
            valid_options.append(
                {
                    "fuente": fuente,
                    "path": str(path),
                    "payload": payload,
                    "best_model": best_model,
                    "eval_split": eval_split,
                }
            )

    if not valid_options:
        return ResolverResult("seleccion_transformer_baseline", None, "FALTANTE", "resolucion", {})

    selected = valid_options[0]
    if len(valid_options) > 1:
        models = sorted({x["best_model"] for x in valid_options})
        if len(models) > 1:
            warnings.append(
                "Ambigüedad en selección Transformer: múltiples artefactos válidos con modelos distintos "
                f"({', '.join(models)}). Se tomó {selected['path']} por prioridad."
            )

    model_cierre = _to_upper_model(((cierre_decision.get("seleccion_transformer_04c") or {}).get("modelo_seleccionado_04c")))
    if model_cierre and model_cierre != selected["best_model"]:
        warnings.append(
            "La selección Transformer del cierre difiere del artefacto seleccionado por prioridad "
            f"({model_cierre} vs {selected['best_model']})."
        )

    return ResolverResult(
        componente="seleccion_transformer_baseline",
        path=selected["path"],
        estado="COMPLETO",
        fuente=selected["fuente"],
        detalle=selected,
    )


def _validar_backbone_comparison_dir(run_dir: Path) -> dict[str, Any] | None:
    csv_path = run_dir / "comparacion_backbones_hibrido.csv"
    json_path = run_dir / "comparacion_backbones_hibrido.json"
    if not csv_path.exists() or not json_path.exists():
        return None
    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return None
    if df.empty or not {"backbone", "macro_f1"}.issubset(df.columns):
        return None
    dff = df.copy()
    dff["backbone"] = dff["backbone"].astype(str).str.lower()
    dff["macro_f1"] = pd.to_numeric(dff["macro_f1"], errors="coerce")
    dff = dff[dff["backbone"].isin(set(BACKBONE_TO_MODEL.keys()))].dropna(subset=["macro_f1"])
    if dff.empty:
        return None
    top = dff.sort_values("macro_f1", ascending=False).iloc[0]
    best_backbone = str(top["backbone"])
    best_model = BACKBONE_TO_MODEL.get(best_backbone)
    best_macro = float(top["macro_f1"])
    delta_vs_beto = None
    if (dff["backbone"] == "beto").any():
        beto_macro = float(dff.loc[dff["backbone"] == "beto", "macro_f1"].iloc[0])
        delta_vs_beto = best_macro - beto_macro
    return {
        "run_dir": str(run_dir),
        "csv_path": str(csv_path),
        "json_path": str(json_path),
        "df": dff,
        "best_backbone": best_backbone,
        "best_model": best_model,
        "best_macro_f1": best_macro,
        "delta_vs_beto": delta_vs_beto,
    }


def _resolver_backbone_comparison(
    outputs_dir: Path,
    cierre_decision: dict[str, Any],
    manifest: dict[str, Any],
    warnings: list[str],
) -> ResolverResult:
    candidates: list[tuple[str, Path]] = []

    pointer = outputs_dir / "comparacion_backbones_hibrido_latest.json"
    ptr_payload, _ = _safe_read_json(pointer)
    if ptr_payload:
        p = (((ptr_payload.get("latest_valid_backbone_comparison") or {}).get("ruta")) or "").strip()
        if p:
            candidates.append(("latest_json", Path(p)))

    ref_cierre = (((cierre_decision.get("comparacion_controlada_backbones_hibrido") or {}).get("run_dir")) or "").strip()
    if ref_cierre:
        candidates.append(("referencia_cierre", Path(ref_cierre)))

    ref_manifest = (((manifest.get("latest_valid_backbone_comparison") or {}).get("ruta")) or "").strip()
    if ref_manifest:
        candidates.append(("manifest_latest", Path(ref_manifest)))

    for d in _latest_dirs(outputs_dir, "comparacion_backbones_hibrido_*"):
        candidates.append(("scan_timestamp", d))

    seen: set[str] = set()
    valid_options: list[dict[str, Any]] = []
    for fuente, path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if not path.exists() or not path.is_dir():
            continue
        v = _validar_backbone_comparison_dir(path)
        if v is None:
            continue
        valid_options.append({"fuente": fuente, **v})

    if not valid_options:
        return ResolverResult("comparacion_backbones_hibrido", None, "FALTANTE", "resolucion", {})

    selected = valid_options[0]
    if len(valid_options) > 1:
        winners = sorted({x["best_backbone"] for x in valid_options})
        if len(winners) > 1:
            warnings.append(
                "Ambigüedad en comparación de backbones: hay corridas válidas con ganadores distintos "
                f"({', '.join(winners)}). Se tomó {selected['run_dir']} por prioridad."
            )

    cierre_winner = (((cierre_decision.get("comparacion_controlada_backbones_hibrido") or {}).get("backbone_ganador")) or "").strip().lower()
    if cierre_winner and cierre_winner != selected["best_backbone"]:
        warnings.append(
            "El backbone ganador del cierre difiere del backbone ganador en el artefacto seleccionado "
            f"({cierre_winner} vs {selected['best_backbone']})."
        )

    return ResolverResult(
        componente="comparacion_backbones_hibrido",
        path=selected["run_dir"],
        estado="COMPLETO",
        fuente=selected["fuente"],
        detalle=selected,
    )


def _resolver_freeze_lexico(outputs_dir: Path, cierre_decision: dict[str, Any], warnings: list[str]) -> ResolverResult:
    candidates: list[tuple[str, Path]] = []
    ref = (((cierre_decision.get("freeze_lexico") or {}).get("ruta")) or "").strip()
    if ref:
        candidates.append(("referencia_cierre", Path(ref)))
    for d in _latest_dirs(outputs_dir, "freeze_lexico_*"):
        candidates.append(("scan_timestamp", d))

    seen: set[str] = set()
    for fuente, d in candidates:
        key = str(d.resolve()) if d.exists() else str(d)
        if key in seen:
            continue
        seen.add(key)
        freeze_json = d / "freeze_lexico_resumen.json"
        payload, err = _safe_read_json(freeze_json)
        if payload is None or err:
            continue
        freeze_id = str(payload.get("freeze_id", "")).strip()
        if not freeze_id:
            continue
        cierre_id = (((cierre_decision.get("freeze_lexico") or {}).get("freeze_id")) or "").strip()
        if cierre_id and cierre_id != freeze_id:
            warnings.append(
                f"Freeze léxico del cierre ({cierre_id}) difiere del freeze seleccionado ({freeze_id})."
            )
        return ResolverResult("freeze_lexico", str(d), "COMPLETO", fuente, {"payload": payload, "json_path": str(freeze_json)})

    return ResolverResult("freeze_lexico", None, "FALTANTE", "resolucion", {})


def _resolver_auditoria_test(outputs_dir: Path, warnings: list[str]) -> ResolverResult:
    # Preferencia por alias estables si existieran
    aliases = _latest_files(outputs_dir, "auditoria_test_latest.*")
    if aliases:
        alias = aliases[0]
        return ResolverResult("auditoria_test", str(alias), "COMPLETO", "latest_alias", {"path": str(alias)})

    md_candidates = _latest_files(outputs_dir, "auditoria_test_*.md")
    if not md_candidates:
        return ResolverResult("auditoria_test", None, "FALTANTE", "scan_timestamp", {})

    md_path = md_candidates[0]
    csv_path = md_path.with_suffix(".csv")
    verdict = "NO_DETERMINADO"
    text = md_path.read_text(encoding="utf-8")
    for key in ["TEST_VIRGEN", "TEST_PARCIALMENTE_TOCADO", "TEST_CONTAMINADO"]:
        if key in text:
            verdict = key
            break
    if verdict == "NO_DETERMINADO":
        warnings.append(f"No se pudo inferir veredicto formal en auditoría de test: {md_path}")
    return ResolverResult(
        "auditoria_test",
        str(md_path),
        "COMPLETO",
        "scan_timestamp",
        {"md_path": str(md_path), "csv_path": str(csv_path) if csv_path.exists() else None, "veredicto": verdict},
    )


def _resolver_error_analysis(
    outputs_dir: Path,
    cierre_dir: Path,
    cierre_decision: dict[str, Any],
    warnings: list[str],
) -> ResolverResult:
    ranking_path = cierre_dir / "ranking_modelos_dev.csv"
    train_run_ref = None
    modelo_final = (((cierre_decision.get("modelo_hibrido_final") or {}).get("modelo_variante")) or "").strip()
    if ranking_path.exists() and modelo_final:
        try:
            rnk = pd.read_csv(ranking_path)
            hit = rnk[rnk["modelo_variante"].astype(str) == modelo_final]
            if not hit.empty:
                train_run_ref = str(hit.iloc[0].get("run_id_train_referencia", "")).strip() or None
        except Exception:
            pass

    candidates = _latest_dirs(outputs_dir, "error_analysis_*")
    aligned: list[dict[str, Any]] = []
    fallback: list[dict[str, Any]] = []
    for d in candidates:
        summary_json = d / "resumen_error_analysis.json"
        payload, err = _safe_read_json(summary_json)
        if payload is None or err:
            continue
        item = {
            "dir": str(d),
            "summary_path": str(summary_json),
            "payload": payload,
            "train_run_id_origen": str(payload.get("train_run_id_origen", "")).strip(),
        }
        fallback.append(item)
        if train_run_ref and item["train_run_id_origen"] == train_run_ref:
            aligned.append(item)

    selected = aligned[0] if aligned else (fallback[0] if fallback else None)
    if selected is None:
        return ResolverResult("error_analysis_modelo_final", None, "FALTANTE", "scan_timestamp", {"train_run_referencia": train_run_ref})

    if train_run_ref and selected["train_run_id_origen"] != train_run_ref:
        warnings.append(
            "No se encontró error_analysis alineado al modelo final del cierre; se tomó el más reciente disponible."
        )

    return ResolverResult(
        "error_analysis_modelo_final",
        selected["dir"],
        "COMPLETO",
        "scan_timestamp",
        {"train_run_referencia": train_run_ref, **selected},
    )


def _resolver_resultados_hibridos(outputs_dir: Path, cierre_decision: dict[str, Any]) -> ResolverResult:
    table_path = (((cierre_decision.get("tabla_fuente")) or "")).strip()
    if table_path:
        p = Path(table_path)
        if p.exists():
            return ResolverResult("resultados_hibridos_dev", str(p), "COMPLETO", "referencia_cierre", {"tabla_path": str(p)})
    # fallback
    candidates = _latest_files(outputs_dir, "results_*/tabla_comparativa_modelos.csv")
    if candidates:
        return ResolverResult("resultados_hibridos_dev", str(candidates[0]), "COMPLETO", "scan_timestamp", {"tabla_path": str(candidates[0])})
    return ResolverResult("resultados_hibridos_dev", None, "FALTANTE", "resolucion", {})


def _resolver_baselines_eval(data_dir: Path) -> ResolverResult:
    mapping = {
        "DUMMY": "dummy_eval.csv",
        "TF-IDF": "tfidf_eval.csv",
        "BETO": "beto_eval.csv",
        "ROBERTA_CLINICAL": "roberta_clinical_eval.csv",
        "ROBERTA_BIOMEDICAL": "roberta_biomedical_eval.csv",
    }
    found = {k: str(data_dir / v) for k, v in mapping.items() if (data_dir / v).exists()}
    if found:
        return ResolverResult("baselines_eval", str(data_dir), "COMPLETO", "paths_estables", {"files": found})
    return ResolverResult("baselines_eval", None, "FALTANTE", "paths_estables", {})


def _detect_test_outputs(repo: Path) -> dict[str, Any]:
    outputs_dir = repo / "data" / "outputs"
    patterns = [
        "**/comparacion_modelos_test.csv",
        "**/predicciones_*_test.csv",
        "**/matriz_confusion_*_test.csv",
        "**/tabla_comparativa_modelos_test.csv",
    ]
    hits = []
    for pat in patterns:
        hits.extend(str(p) for p in outputs_dir.glob(pat))
    hits = sorted(set(hits))
    return {"n_hits": len(hits), "paths_muestra": hits[:20]}


def _detect_xai_outputs(repo: Path) -> dict[str, Any]:
    outputs_dir = repo / "data" / "outputs"
    patterns = ["**/*xai*", "**/*explicab*", "**/*shap*", "**/*lime*"]
    hits = []
    for pat in patterns:
        hits.extend(str(p) for p in outputs_dir.glob(pat))
    hits = sorted(set(hits))
    return {"n_hits": len(hits), "paths_muestra": hits[:20]}


def _pick_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def _text_length_stats(series: pd.Series) -> tuple[float | None, float | None]:
    if series is None or len(series) == 0:
        return None, None
    lengths = (
        series.fillna("")
        .astype(str)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
        .str.split(" ")
        .map(lambda toks: len([t for t in toks if t]))
    )
    if lengths.empty:
        return None, None
    return float(lengths.mean()), float(lengths.median())


def _dataset_summary(splits_dir: Path, warnings: list[str]) -> tuple[pd.DataFrame, str]:
    split_defs = [
        ("dataset_base.csv", "base"),
        ("train_denoised.csv", "train"),
        ("dev_denoised.csv", "dev"),
        ("test_denoised.csv", "test"),
    ]
    rows: list[dict[str, Any]] = []
    split_dfs: dict[str, pd.DataFrame] = {}

    for fname, split in split_defs:
        p = splits_dir / fname
        if not p.exists():
            rows.append(
                {
                    "split": split,
                    "path": str(p),
                    "n_registros": None,
                    "n_pacientes_unicos": None,
                    "target_col": None,
                    "dist_clase": None,
                    "longitud_texto_media": None,
                    "longitud_texto_mediana": None,
                    "notas": "archivo_no_encontrado",
                }
            )
            continue

        df = pd.read_csv(p)
        split_dfs[split] = df

        target_col = _pick_col(df, ["etiqueta", "target", "diagnostico", "label", "clase", "y"])
        patient_col = _pick_col(df, ["patient_id", "id_paciente", "paciente_id", "subject_id"])
        text_col = _pick_col(df, ["texto", "text", "note", "nota"])

        dist = None
        if target_col is not None:
            dist = json.dumps(df[target_col].astype(str).value_counts(dropna=False).to_dict(), ensure_ascii=False)
        else:
            warnings.append(f"Dataset {fname}: no se detectó columna de clase.")

        n_pat = int(df[patient_col].nunique()) if patient_col is not None else None
        if patient_col is None:
            warnings.append(f"Dataset {fname}: no se detectó columna de paciente.")

        mean_len, med_len = (None, None)
        if text_col is not None:
            mean_len, med_len = _text_length_stats(df[text_col])
        else:
            warnings.append(f"Dataset {fname}: no se detectó columna de texto.")

        rows.append(
            {
                "split": split,
                "path": str(p),
                "n_registros": int(len(df)),
                "n_pacientes_unicos": n_pat,
                "target_col": target_col,
                "dist_clase": dist,
                "longitud_texto_media": mean_len,
                "longitud_texto_mediana": med_len,
                "notas": "",
            }
        )

    # Resumen global consolidado (preferencia dataset_base; fallback train+dev+test)
    global_df = split_dfs.get("base")
    global_source = "dataset_base.csv"
    if global_df is None:
        parts = [split_dfs[s] for s in ["train", "dev", "test"] if s in split_dfs]
        if parts:
            global_df = pd.concat(parts, ignore_index=True)
            global_source = "train+dev+test"

    if global_df is not None:
        target_col = _pick_col(global_df, ["etiqueta", "target", "diagnostico", "label", "clase", "y"])
        patient_col = _pick_col(global_df, ["patient_id", "id_paciente", "paciente_id", "subject_id"])
        text_col = _pick_col(global_df, ["texto", "text", "note", "nota"])
        dist = (
            json.dumps(global_df[target_col].astype(str).value_counts(dropna=False).to_dict(), ensure_ascii=False)
            if target_col is not None
            else None
        )
        mean_len, med_len = _text_length_stats(global_df[text_col]) if text_col is not None else (None, None)
        rows.append(
            {
                "split": "global",
                "path": global_source,
                "n_registros": int(len(global_df)),
                "n_pacientes_unicos": int(global_df[patient_col].nunique()) if patient_col is not None else None,
                "target_col": target_col,
                "dist_clase": dist,
                "longitud_texto_media": mean_len,
                "longitud_texto_mediana": med_len,
                "notas": "agregado_global",
            }
        )
    else:
        warnings.append("No fue posible construir resumen global de dataset.")

    dataset_df = pd.DataFrame(rows)
    md = []
    md.append("# Dataset: resumen consolidado")
    md.append("")
    md.append("- Este resumen usa artefactos ya existentes en `data/splits`.")
    md.append("- Incluye registros, pacientes únicos, distribución de clase y longitud de texto por split.")
    md.append("")
    for _, r in dataset_df.iterrows():
        md.append(f"## Split: {r['split']}")
        md.append(f"- Fuente: `{r['path']}`")
        md.append(f"- n_registros: `{r['n_registros']}`")
        md.append(f"- n_pacientes_unicos: `{r['n_pacientes_unicos']}`")
        md.append(f"- columna_clase: `{r['target_col']}`")
        md.append(f"- distribución_clase: `{r['dist_clase']}`")
        md.append(f"- longitud_texto_media: `{r['longitud_texto_media']}`")
        md.append(f"- longitud_texto_mediana: `{r['longitud_texto_mediana']}`")
        if str(r.get("notas", "")).strip():
            md.append(f"- notas: `{r['notas']}`")
        md.append("")

    missing = dataset_df[dataset_df["n_registros"].isna()]
    if not missing.empty:
        md.append("## Campos no extraíbles con confianza")
        for _, r in missing.iterrows():
            md.append(f"- `{r['split']}`: archivo no disponible.")
        md.append("")

    return dataset_df, "\n".join(md) + "\n"


def _extract_terms_from_rule_file(path: Path) -> set[str]:
    payload, err = _safe_read_json(path)
    if payload is None or err:
        return set()

    terms: set[str] = set()

    def _norm(s: str) -> str:
        return re.sub(r"\s+", " ", s.strip().lower())

    def _push(text: str | None) -> None:
        if text is None:
            return
        t = _norm(str(text))
        if t:
            terms.add(t)

    def _pattern_to_text(pattern: Any) -> str | None:
        if not isinstance(pattern, list):
            return None
        chunks: list[str] = []
        for tok in pattern:
            if not isinstance(tok, dict):
                continue
            for key in ["LOWER", "TEXT", "ORTH", "NORM", "LEMMA"]:
                if key in tok and isinstance(tok[key], str):
                    chunks.append(tok[key])
                    break
        return " ".join(chunks).strip() if chunks else None

    target_rules = None
    if isinstance(payload, dict) and isinstance(payload.get("target_rules"), list):
        target_rules = payload.get("target_rules")

    if isinstance(target_rules, list):
        for rule in target_rules:
            if not isinstance(rule, dict):
                continue
            _push(rule.get("literal"))
            _push(_pattern_to_text(rule.get("pattern")))

    # fallback mínimo por seguridad si no hay target_rules estándar
    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in {"literal", "term", "variant"} and isinstance(v, str):
                    _push(v)
                _walk(v)
        elif isinstance(obj, list):
            for item in obj:
                _walk(item)

    if not terms:
        _walk(payload)
    return terms


def _layer_terms(layer_dir: Path) -> tuple[set[str], int]:
    if not layer_dir.exists():
        return set(), 0
    json_files = sorted(layer_dir.rglob("*.json"))
    terms: set[str] = set()
    for f in json_files:
        terms |= _extract_terms_from_rule_file(f)
    return terms, len(json_files)


def _arquitectura_lexica_df(
    freeze_payload: dict[str, Any],
    freeze_path: str | None,
    warnings: list[str],
) -> tuple[pd.DataFrame, str]:
    freeze_id = freeze_payload.get("freeze_id") if isinstance(freeze_payload, dict) else None
    fecha_freeze = freeze_payload.get("fecha_freeze") if isinstance(freeze_payload, dict) else None

    rows: list[dict[str, Any]] = []
    md: list[str] = []
    md.append("# Arquitectura léxica: resumen cuantitativo")
    md.append("")
    md.append(f"- Freeze preliminar canónico usado: `{freeze_id}`")
    md.append("- Nota metodológica: este freeze es **preliminar**, no freeze oficial final.")
    md.append("")

    if freeze_path is None:
        warnings.append("No se encontró freeze léxico para resumen cuantitativo.")
        return (
            pd.DataFrame(
                [
                    {
                        "freeze_id": freeze_id,
                        "fecha_freeze": fecha_freeze,
                        "seccion": "estado",
                        "item": "freeze_no_encontrado",
                        "valor": None,
                        "detalle": None,
                    }
                ]
            ),
            "\n".join(md) + "\n",
        )

    freeze_dir = Path(freeze_path)
    snapshot_patterns = (
        freeze_dir
        / "snapshot"
        / "Spanish_Psych_Phenotyping_PY"
        / "escribe"
        / "patterns"
    )
    layer_map = {
        "CO": snapshot_patterns / "Concept_CO",
        "Core": snapshot_patterns / "Concept_PY",
        "PY": snapshot_patterns / "Concept_PY_Lexicon",
    }

    layer_terms: dict[str, set[str]] = {}
    layer_files: dict[str, int] = {}
    for layer, path in layer_map.items():
        terms, n_files = _layer_terms(path)
        layer_terms[layer] = terms
        layer_files[layer] = n_files
        rows.append(
            {
                "freeze_id": freeze_id,
                "fecha_freeze": fecha_freeze,
                "seccion": "capa",
                "item": layer,
                "valor": len(terms),
                "detalle": json.dumps(
                    {
                        "n_reglas_json": n_files,
                        "ruta": str(path),
                    },
                    ensure_ascii=False,
                ),
            }
        )

    # Intersecciones y exclusivos
    co = layer_terms.get("CO", set())
    core = layer_terms.get("Core", set())
    py = layer_terms.get("PY", set())
    inters = {
        "CO∩Core": len(co & core),
        "CO∩PY": len(co & py),
        "Core∩PY": len(core & py),
        "CO∩Core∩PY": len(co & core & py),
        "CO_exclusivo": len(co - core - py),
        "Core_exclusivo": len(core - co - py),
        "PY_exclusivo": len(py - co - core),
    }
    for k, v in inters.items():
        rows.append(
            {
                "freeze_id": freeze_id,
                "fecha_freeze": fecha_freeze,
                "seccion": "interseccion_exclusivo",
                "item": k,
                "valor": v,
                "detalle": "",
            }
        )

    # Resumen cuantitativo del freeze/audit
    tabla_csv = freeze_dir / "freeze_lexico_tabla.csv"
    diff_resumen_csv = freeze_dir / "freeze_lexico_diff_resumen.csv"
    diff_terms_csv = freeze_dir / "freeze_lexico_diff_terminos.csv"
    comp_prev = freeze_payload.get("comparacion_version_previa", {}) if isinstance(freeze_payload, dict) else {}
    recursos_faltantes = freeze_payload.get("recursos_faltantes", []) if isinstance(freeze_payload, dict) else []

    if tabla_csv.exists():
        tabla_df = pd.read_csv(tabla_csv)
        for _, r in tabla_df.iterrows():
            rows.append(
                {
                    "freeze_id": freeze_id,
                    "fecha_freeze": fecha_freeze,
                    "seccion": "recurso_congelado",
                    "item": r.get("nombre_recurso"),
                    "valor": r.get("archivos_detectados"),
                    "detalle": json.dumps(
                        {
                            "estado": r.get("estado"),
                            "tipo": r.get("tipo"),
                            "observaciones": r.get("observaciones"),
                        },
                        ensure_ascii=False,
                    ),
                }
            )
    else:
        warnings.append(f"No existe freeze_lexico_tabla.csv en {freeze_dir}")

    rows.append(
        {
            "freeze_id": freeze_id,
            "fecha_freeze": fecha_freeze,
            "seccion": "audit_resumen",
            "item": "comparacion_version_previa",
            "valor": comp_prev.get("archivos_json_con_cambios_de_terminos"),
            "detalle": json.dumps(comp_prev, ensure_ascii=False),
        }
    )
    rows.append(
        {
            "freeze_id": freeze_id,
            "fecha_freeze": fecha_freeze,
            "seccion": "advertencia",
            "item": "recursos_faltantes",
            "valor": len(recursos_faltantes) if isinstance(recursos_faltantes, list) else None,
            "detalle": json.dumps(recursos_faltantes, ensure_ascii=False),
        }
    )

    # Markdown
    md.append("## Cantidad de términos/reglas por capa")
    for layer in ["CO", "Core", "PY"]:
        md.append(
            f"- `{layer}`: n_términos={len(layer_terms.get(layer, set()))}, n_reglas_json={layer_files.get(layer, 0)}"
        )
    md.append("")
    md.append("## Intersecciones y exclusivos")
    for k, v in inters.items():
        md.append(f"- `{k}`: {v}")
    md.append("")
    md.append("## Advertencias y estado del freeze")
    md.append(
        f"- recursos_faltantes: {len(recursos_faltantes) if isinstance(recursos_faltantes, list) else 'N/D'}"
    )
    md.append(
        f"- comparación con freeze previo: {json.dumps(comp_prev, ensure_ascii=False)}"
    )
    if diff_resumen_csv.exists():
        d = pd.read_csv(diff_resumen_csv)
        md.append(f"- `freeze_lexico_diff_resumen.csv`: {len(d)} filas")
    else:
        md.append("- `freeze_lexico_diff_resumen.csv`: no disponible")
    if diff_terms_csv.exists():
        d = pd.read_csv(diff_terms_csv)
        md.append(f"- `freeze_lexico_diff_terminos.csv`: {len(d)} filas")
    else:
        md.append("- `freeze_lexico_diff_terminos.csv`: no disponible")
    md.append("")

    return pd.DataFrame(rows), "\n".join(md) + "\n"


def _baselines_df(eval_files: dict[str, str]) -> pd.DataFrame:
    rows = []
    for modelo, path in eval_files.items():
        p = Path(path)
        try:
            df = pd.read_csv(p)
        except Exception:
            continue
        if df.empty:
            continue
        r = df.iloc[0].to_dict()
        rows.append(
            {
                "modelo": modelo,
                "eval_split": r.get("eval_split", "dev"),
                "f1_macro": r.get("f1_macro"),
                "balanced_acc": r.get("balanced_acc"),
                "precision_macro": r.get("precision_macro"),
                "recall_macro": r.get("recall_macro"),
                "accuracy": r.get("accuracy"),
                "n_train": r.get("n_train"),
                "n_eval": r.get("n_eval"),
                "source_path": str(p),
            }
        )
    return pd.DataFrame(rows)


def _transformers_baseline_df(selection_payload: dict[str, Any]) -> pd.DataFrame:
    best = _to_upper_model(((selection_payload.get("mejor_transformer_baseline") or {}).get("modelo")))
    rows = []
    for item in selection_payload.get("modelos_comparados", []) or []:
        modelo = _to_upper_model(item.get("modelo")) or str(item.get("modelo", "")).upper()
        rows.append(
            {
                "modelo": modelo,
                "f1_macro": item.get("f1_macro"),
                "balanced_acc": item.get("balanced_acc"),
                "precision_macro": item.get("precision_macro"),
                "recall_macro": item.get("recall_macro"),
                "accuracy": item.get("accuracy"),
                "n_train": item.get("n_train"),
                "n_eval": item.get("n_eval"),
                "es_mejor_transformer_standalone": int(modelo == best),
            }
        )
    return pd.DataFrame(rows)


def _backbones_df(comp_df: pd.DataFrame, best_backbone: str | None) -> pd.DataFrame:
    if comp_df.empty:
        return pd.DataFrame(
            columns=[
                "backbone",
                "modelo_transformer",
                "macro_f1",
                "balanced_accuracy",
                "f1_ansiedad",
                "f1_depresion",
                "n_features",
                "seed",
                "run_id_features",
                "run_id_train",
                "eval_split",
                "es_backbone_ganador_hibrido",
            ]
        )
    out = comp_df.copy()
    out["modelo_transformer"] = out["backbone"].map(BACKBONE_TO_MODEL).fillna(out["backbone"])
    out["es_backbone_ganador_hibrido"] = (out["backbone"].astype(str).str.lower() == str(best_backbone).lower()).astype(int)
    return out[
        [
            "backbone",
            "modelo_transformer",
            "macro_f1",
            "balanced_accuracy",
            "f1_ansiedad",
            "f1_depresion",
            "n_features",
            "seed",
            "run_id_features",
            "run_id_train",
            "eval_split",
            "es_backbone_ganador_hibrido",
        ]
    ]


def _infer_backbone_model(
    modelo_variante: str | None,
    train_run_id: str | None,
    outputs_dir: Path,
    fallback_backbone_model: str | None,
) -> tuple[str | None, str]:
    v = (modelo_variante or "").lower()
    if "roberta_clinical" in v:
        return "ROBERTA_CLINICAL", "inferido_por_modelo_variante"
    if "roberta_biomedical" in v:
        return "ROBERTA_BIOMEDICAL", "inferido_por_modelo_variante"
    if "beto1" in v or "beto" in v:
        return "BETO", "inferido_por_modelo_variante"

    if train_run_id:
        comp_path = outputs_dir / train_run_id / "comparacion_modelos_dev.csv"
        if comp_path.exists():
            try:
                comp_df = pd.read_csv(comp_path)
                if not comp_df.empty and "beto_activo" in comp_df.columns:
                    beto_flag = int(pd.to_numeric(comp_df.iloc[0]["beto_activo"], errors="coerce") or 0)
                    if beto_flag == 1:
                        return "BETO", "inferido_por_beto_activo_train_run"
            except Exception:
                pass

    return fallback_backbone_model, "fallback_comparacion_backbone"


def _error_analysis_enriched_df(
    error_res: ResolverResult,
    cierre_decision: dict[str, Any],
    ranking_df: pd.DataFrame,
    outputs_dir: Path,
    backbone_best_model: str | None,
    warnings: list[str],
) -> tuple[pd.DataFrame, str]:
    md: list[str] = []
    md.append("# Error analysis: resumen del modelo final")
    md.append("")

    if not error_res.path:
        warnings.append("No se encontró error_analysis vigente para enriquecer.")
        return (
            pd.DataFrame(
                [
                    {
                        "train_run_id": None,
                        "backbone_modelo": None,
                        "backbone_fuente": None,
                        "split": None,
                        "clase": None,
                        "n": None,
                        "errores": None,
                        "tasa_error": None,
                        "patrones_principales": None,
                        "hallazgo_resumido": "error_analysis_no_disponible",
                        "ancla_alineacion": None,
                    }
                ]
            ),
            "\n".join(md) + "\n",
        )

    err_dir = Path(error_res.path)
    err_json_path = err_dir / "resumen_error_analysis.json"
    err_cls_path = err_dir / "resumen_error_por_clase.csv"
    err_terms_path = err_dir / "terminos_distintivos_errores.csv"

    err_payload, _ = _safe_read_json(err_json_path)
    err_payload = err_payload or {}
    train_run_id = str(err_payload.get("train_run_id_origen", "")).strip() or None
    pred_file = str(err_payload.get("predicciones_analizadas", "")).strip()
    split_eval = "dev" if pred_file.endswith("_dev.csv") else ("test" if pred_file.endswith("_test.csv") else "desconocido")

    modelo_final = (((cierre_decision.get("modelo_hibrido_final") or {}).get("modelo_variante")) or "").strip()
    run_ref = None
    if not ranking_df.empty and modelo_final:
        hit = ranking_df[ranking_df["modelo_variante"].astype(str) == modelo_final]
        if not hit.empty:
            run_ref = str(hit.iloc[0].get("run_id_train_referencia", "")).strip() or None

    backbone_modelo, backbone_fuente = _infer_backbone_model(
        modelo_variante=modelo_final,
        train_run_id=train_run_id,
        outputs_dir=outputs_dir,
        fallback_backbone_model=backbone_best_model,
    )

    if run_ref and train_run_id and run_ref != train_run_id:
        warnings.append(
            f"Error analysis con train_run_id distinto al cierre: cierre={run_ref}, error={train_run_id}."
        )

    # Patrones por clase (si existen)
    patterns_by_class: dict[str, str] = {}
    if err_terms_path.exists():
        try:
            tdf = pd.read_csv(err_terms_path)
            if not tdf.empty and {"termino", "conteo", "clase_objetivo"}.issubset(tdf.columns):
                tdf["conteo"] = pd.to_numeric(tdf["conteo"], errors="coerce").fillna(0)
                for clase, g in tdf.groupby("clase_objetivo"):
                    top_terms_raw = g.sort_values("conteo", ascending=False).head(15)["termino"].astype(str).tolist()
                    top_terms: list[str] = []
                    for t in top_terms_raw:
                        if t not in top_terms:
                            top_terms.append(t)
                        if len(top_terms) >= 5:
                            break
                    patterns_by_class[str(clase)] = ", ".join(top_terms)
        except Exception:
            warnings.append(f"No se pudo procesar patrones de error en {err_terms_path}.")

    rows: list[dict[str, Any]] = []
    if err_cls_path.exists():
        cls_df = pd.read_csv(err_cls_path)
        for _, r in cls_df.iterrows():
            clase = str(r.get("y_true"))
            rows.append(
                {
                    "train_run_id": train_run_id,
                    "backbone_modelo": backbone_modelo,
                    "backbone_fuente": backbone_fuente,
                    "split": split_eval,
                    "clase": clase,
                    "n": r.get("n"),
                    "errores": r.get("errores"),
                    "tasa_error": r.get("tasa_error"),
                    "patrones_principales": patterns_by_class.get(clase, None),
                    "hallazgo_resumido": None,
                    "ancla_alineacion": train_run_id,
                }
            )
    else:
        rows.append(
            {
                "train_run_id": train_run_id,
                "backbone_modelo": backbone_modelo,
                "backbone_fuente": backbone_fuente,
                "split": split_eval,
                "clase": None,
                "n": None,
                "errores": None,
                "tasa_error": None,
                "patrones_principales": None,
                "hallazgo_resumido": "resumen_error_por_clase_no_disponible",
                "ancla_alineacion": train_run_id,
            }
        )

    # Hallazgo resumido global
    if rows and any(r.get("tasa_error") is not None for r in rows):
        valid = [r for r in rows if r.get("tasa_error") is not None]
        worst = max(valid, key=lambda x: float(x["tasa_error"]))
        global_msg = (
            f"Mayor tasa de error en clase '{worst.get('clase')}' "
            f"(tasa={worst.get('tasa_error')}, errores={worst.get('errores')})."
        )
        for r in rows:
            r["hallazgo_resumido"] = global_msg

    md.append(f"- Directorio error_analysis: `{err_dir}`")
    md.append(f"- train_run_id (ancla): `{train_run_id}`")
    md.append(f"- split evaluado: `{split_eval}`")
    md.append(f"- backbone inferido: `{backbone_modelo}` (fuente: `{backbone_fuente}`)")
    md.append("")
    md.append(
        "- Nota: si `resumen_error_analysis.json` no declara explícitamente `modelo_variante` o `backbone`, "
        "la alineación se cierra por `train_run_id`."
    )
    md.append("")
    md.append("## Errores por clase")
    for r in rows:
        if r.get("clase") is None:
            continue
        md.append(
            f"- `{r['clase']}`: n={r.get('n')}, errores={r.get('errores')}, tasa_error={r.get('tasa_error')}, "
            f"patrones={r.get('patrones_principales')}"
        )
    md.append("")

    return pd.DataFrame(rows), "\n".join(md) + "\n"


def _decision_table(
    cierre_decision: dict[str, Any],
    transformer_best: str | None,
    backbone_best_model: str | None,
    audit_veredicto: str | None,
    xai_pendiente: bool,
) -> pd.DataFrame:
    rows = []
    rows.append(
        {
            "decision": "baseline_fuerte_simple",
            "valor": "TF-IDF",
            "fuente": "baselines_dev_resumen.csv",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "mejor_transformer_standalone",
            "valor": transformer_best,
            "fuente": "transformer_baseline_selection_latest.json",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "mejor_backbone_hibrido",
            "valor": backbone_best_model,
            "fuente": "comparacion_backbones_hibrido_latest.json",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "mejor_hibrido_final_dev",
            "valor": ((cierre_decision.get("modelo_hibrido_final") or {}).get("modelo_variante")),
            "fuente": "decision_modelo_final.json",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "estado_test",
            "valor": audit_veredicto or "NO_DETERMINADO",
            "fuente": "auditoria_test",
            "estado": "confirmado" if audit_veredicto else "faltante",
        }
    )
    rows.append(
        {
            "decision": "estado_xai",
            "valor": "PENDIENTE" if xai_pendiente else "DISPONIBLE",
            "fuente": "deteccion_outputs_xai",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "estado_fase",
            "valor": "CASI_LISTO_PARA_FREEZE_OFICIAL_Y_TEST",
            "fuente": "consolidacion_metodologica",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "transformer_vs_backbone_son_distintos",
            "valor": str(bool(transformer_best and backbone_best_model and transformer_best != backbone_best_model)),
            "fuente": "transformer_vs_backbone_decision.csv",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "freeze_lexico_preliminar",
            "valor": ((cierre_decision.get("freeze_lexico") or {}).get("freeze_id")),
            "fuente": "decision_modelo_final.json",
            "estado": "preliminar",
        }
    )
    rows.append(
        {
            "decision": "split_decision_modelos",
            "valor": cierre_decision.get("split_decision"),
            "fuente": "decision_modelo_final.json",
            "estado": "confirmado",
        }
    )
    rows.append(
        {
            "decision": "nota_freeze_pre_test",
            "valor": cierre_decision.get("nota_freeze"),
            "fuente": "decision_modelo_final.json",
            "estado": "confirmado",
        }
    )
    return pd.DataFrame(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolida insumos vigentes de metodología y resultados para tesis.")
    parser.add_argument("--dry-run", action="store_true", help="No escribe archivos; solo valida y reporta.")
    parser.add_argument("--verbose", action="store_true", help="Imprime detalle de resolución de artefactos.")
    parser.add_argument(
        "--output-tag",
        default="",
        help="Tag opcional para nombre de salida (sin espacios). Ejemplo: rerun_dev_1",
    )
    parser.add_argument("--out-root", default="data/outputs", help="Directorio base de outputs.")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]
    outputs_dir = (repo / args.out_root).resolve()
    data_dir = repo / "data"
    splits_dir = data_dir / "splits"

    warnings: list[str] = []
    selected_components: list[ResolverResult] = []

    cierre_res = _resolver_cierre_dev(outputs_dir, warnings)
    selected_components.append(cierre_res)
    if cierre_res.path is None:
        raise SystemExit("No se encontró cierre formal de modelos en dev válido (cierre_modelos_dev_*).")
    cierre_dir = Path(cierre_res.path)
    cierre_decision = cierre_res.detalle["decision"]

    manifest_res = _resolver_manifest_backbone(outputs_dir)
    selected_components.append(manifest_res)
    manifest_payload = manifest_res.detalle if manifest_res.detalle else {}

    transformer_res = _resolver_transformer_selection(outputs_dir, cierre_decision, manifest_payload, warnings)
    selected_components.append(transformer_res)

    backbone_res = _resolver_backbone_comparison(outputs_dir, cierre_decision, manifest_payload, warnings)
    selected_components.append(backbone_res)

    freeze_res = _resolver_freeze_lexico(outputs_dir, cierre_decision, warnings)
    selected_components.append(freeze_res)

    audit_test_res = _resolver_auditoria_test(outputs_dir, warnings)
    selected_components.append(audit_test_res)

    error_res = _resolver_error_analysis(outputs_dir, cierre_dir, cierre_decision, warnings)
    selected_components.append(error_res)

    resultados_res = _resolver_resultados_hibridos(outputs_dir, cierre_decision)
    selected_components.append(resultados_res)

    baselines_res = _resolver_baselines_eval(data_dir)
    selected_components.append(baselines_res)

    # Cargas de datos para exportes
    freeze_payload = {}
    if freeze_res.path:
        freeze_payload, _ = _safe_read_json(Path(freeze_res.path) / "freeze_lexico_resumen.json")
        freeze_payload = freeze_payload or {}

    selection_payload = {}
    transformer_best = None
    if transformer_res.path:
        selection_payload, _ = _safe_read_json(Path(transformer_res.path))
        selection_payload = selection_payload or {}
        transformer_best = _to_upper_model(((selection_payload.get("mejor_transformer_baseline") or {}).get("modelo")))

    comp_df = pd.DataFrame()
    backbone_best_model = None
    backbone_best = None
    if backbone_res.path:
        comp_df = pd.read_csv(Path(backbone_res.path) / "comparacion_backbones_hibrido.csv")
        backbone_best = backbone_res.detalle.get("best_backbone")
        backbone_best_model = backbone_res.detalle.get("best_model")

    ranking_path = cierre_dir / "ranking_modelos_dev.csv"
    ranking_df = pd.read_csv(ranking_path) if ranking_path.exists() else pd.DataFrame()

    table_maestra_path = Path(str(resultados_res.detalle.get("tabla_path", ""))) if resultados_res.detalle else None
    tabla_maestra_df = pd.read_csv(table_maestra_path) if table_maestra_path and table_maestra_path.exists() else pd.DataFrame()

    baselines_df = _baselines_df(baselines_res.detalle.get("files", {}) if baselines_res.detalle else {})
    transformers_df = _transformers_baseline_df(selection_payload)
    backbones_df = _backbones_df(comp_df, backbone_best)
    hibridos_df = ranking_df[ranking_df["source"].astype(str).isin(["barrido", "hibrido_referencia"])].copy() if not ranking_df.empty else pd.DataFrame()
    dataset_df, dataset_md = _dataset_summary(splits_dir, warnings)
    arq_lex_df, arq_lex_md = _arquitectura_lexica_df(freeze_payload, freeze_res.path, warnings)
    error_analysis_df, error_analysis_md = _error_analysis_enriched_df(
        error_res=error_res,
        cierre_decision=cierre_decision,
        ranking_df=ranking_df,
        outputs_dir=outputs_dir,
        backbone_best_model=backbone_best_model,
        warnings=warnings,
    )

    # Consistencia cruzada
    consistency: dict[str, Any] = {"ok": True, "checks": []}
    freeze_cierre = ((cierre_decision.get("freeze_lexico") or {}).get("freeze_id"))
    freeze_sel = freeze_payload.get("freeze_id")
    if freeze_cierre and freeze_sel and freeze_cierre != freeze_sel:
        consistency["ok"] = False
        warnings.append(f"Inconsistencia freeze léxico: cierre={freeze_cierre} vs seleccionado={freeze_sel}.")
    consistency["checks"].append(
        {"check": "freeze_lexico_alineado_con_cierre", "ok": (freeze_cierre == freeze_sel) if freeze_cierre and freeze_sel else None}
    )

    cmp_cierre_run = (((cierre_decision.get("comparacion_controlada_backbones_hibrido") or {}).get("run_dir")) or "").strip()
    cmp_sel_run = backbone_res.path
    cmp_aligned = (cmp_cierre_run == cmp_sel_run) if (cmp_cierre_run and cmp_sel_run) else None
    if cmp_aligned is False:
        consistency["ok"] = False
        warnings.append(f"Inconsistencia comparación backbone: cierre={cmp_cierre_run} vs seleccionado={cmp_sel_run}.")
    consistency["checks"].append({"check": "comparacion_backbone_alineada_con_cierre", "ok": cmp_aligned})

    trf_cierre = _to_upper_model(
        ((cierre_decision.get("seleccion_transformer_04c") or {}).get("modelo_seleccionado_04c"))
    )
    trf_aligned = (trf_cierre == transformer_best) if (trf_cierre and transformer_best) else None
    if trf_aligned is False:
        warnings.append(f"Selección Transformer difiere: cierre={trf_cierre} vs seleccion={transformer_best}.")
    consistency["checks"].append({"check": "seleccion_transformer_alineada_con_cierre", "ok": trf_aligned})

    train_ref = error_res.detalle.get("train_run_referencia")
    train_err = error_res.detalle.get("train_run_id_origen")
    err_aligned = (train_ref == train_err) if (train_ref and train_err) else None
    if err_aligned is False:
        consistency["ok"] = False
        warnings.append(
            f"Error analysis no alineado al modelo final: referencia={train_ref}, analizado={train_err}."
        )
    consistency["checks"].append({"check": "error_analysis_alineado_modelo_final", "ok": err_aligned})

    test_outputs = _detect_test_outputs(repo)
    xai_outputs = _detect_xai_outputs(repo)

    # Salida
    tag = re.sub(r"[^a-zA-Z0-9_\-]+", "_", args.output_tag).strip("_") if args.output_tag else _now_ts()
    run_id = f"insumos_tesis_metodologia_resultados_{tag}"
    out_dir = outputs_dir / run_id

    reporte_json = {
        "run_id": run_id,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "repo": str(repo),
        "git": _git_info(repo),
        "artefactos_seleccionados": [
            {
                "componente": r.componente,
                "path": r.path,
                "estado": r.estado,
                "fuente": r.fuente,
            }
            for r in selected_components
        ],
        "consistencia": consistency,
        "warnings": warnings,
        "estado_componentes": {
            r.componente: r.estado for r in selected_components
        },
        "resumen_decision_transformer_vs_backbone": {
            "mejor_transformer_standalone_dev": transformer_best,
            "backbone_ganador_hibrido_dev": backbone_best_model,
            "coinciden": bool(transformer_best and backbone_best_model and transformer_best == backbone_best_model),
        },
        "estado_fase_final": {
            "test_outputs_detectados": test_outputs,
            "xai_outputs_detectados": xai_outputs,
            "test_pendiente": (audit_test_res.detalle.get("veredicto") == "TEST_VIRGEN") if audit_test_res.detalle else None,
            "xai_pendiente": xai_outputs.get("n_hits", 0) == 0,
        },
        "fuentes_de_verdad": {
            "cierre_formal_dev": cierre_res.path,
            "freeze_lexico": freeze_res.path,
            "auditoria_test": audit_test_res.path,
            "seleccion_transformer": transformer_res.path,
            "comparacion_backbones_hibrido": backbone_res.path,
            "error_analysis_modelo_final": error_res.path,
            "tabla_maestra_resultados": str(table_maestra_path) if table_maestra_path else None,
        },
    }

    if args.verbose:
        print(json.dumps(reporte_json, ensure_ascii=False, indent=2))

    if args.dry_run:
        print(f"[dry-run] Consolidación validada. Salida prevista: {out_dir}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    dataset_df.to_csv(out_dir / "dataset_resumen.csv", index=False)
    arq_lex_df.to_csv(out_dir / "arquitectura_lexica_resumen.csv", index=False)
    baselines_df.to_csv(out_dir / "baselines_dev_resumen.csv", index=False)
    transformers_df.to_csv(out_dir / "transformers_baseline_resumen.csv", index=False)
    backbones_df.to_csv(out_dir / "backbones_hibrido_resumen.csv", index=False)

    transformer_vs_backbone = pd.DataFrame(
        [
            {
                "mejor_transformer_standalone_dev": transformer_best,
                "backbone_ganador_hibrido_dev": backbone_best_model,
                "coinciden": int(bool(transformer_best and backbone_best_model and transformer_best == backbone_best_model)),
                "decision_04c_path": transformer_res.path,
                "comparacion_backbone_path": backbone_res.path,
                "nota": (
                    "Coinciden."
                    if transformer_best and backbone_best_model and transformer_best == backbone_best_model
                    else "No coinciden; no mezclar baseline standalone con backbone del híbrido."
                ),
            }
        ]
    )
    transformer_vs_backbone.to_csv(out_dir / "transformer_vs_backbone_decision.csv", index=False)

    hibridos_cols = [
        "posicion_final",
        "recomendacion",
        "modelo_variante",
        "source",
        "perfil",
        "modelo",
        "macro_f1_mean",
        "balanced_accuracy_mean",
        "f1_ansiedad_mean",
        "f1_depresion_mean",
        "macro_f1_std",
        "n_seeds",
        "n_features",
        "score_final_seleccion",
        "riesgos_metodologicos",
        "run_id_train_referencia",
        "run_id_features",
    ]
    if not hibridos_df.empty:
        keep = [c for c in hibridos_cols if c in hibridos_df.columns]
        hibridos_df[keep].to_csv(out_dir / "hibridos_dev_resumen.csv", index=False)
    else:
        pd.DataFrame(columns=hibridos_cols).to_csv(out_dir / "hibridos_dev_resumen.csv", index=False)

    modelo_final_resumen = {
        "fecha_cierre": cierre_decision.get("fecha_decision"),
        "split_decision": cierre_decision.get("split_decision"),
        "modelo_hibrido_final": cierre_decision.get("modelo_hibrido_final"),
        "modelos_que_pasan_a_test": cierre_decision.get("modelos_que_pasan_a_test"),
        "freeze_lexico": cierre_decision.get("freeze_lexico"),
        "seleccion_transformer_04c": cierre_decision.get("seleccion_transformer_04c"),
        "comparacion_controlada_backbones_hibrido": cierre_decision.get("comparacion_controlada_backbones_hibrido"),
        "paths_fuente": {
            "cierre_dir": str(cierre_dir),
            "decision_json": str(cierre_dir / "decision_modelo_final.json"),
            "ranking_csv": str(cierre_dir / "ranking_modelos_dev.csv"),
        },
    }
    _write_json(out_dir / "modelo_final_dev_resumen.json", modelo_final_resumen)

    auditoria_test_resumen = {
        "path_md": audit_test_res.detalle.get("md_path") if audit_test_res.detalle else None,
        "path_csv": audit_test_res.detalle.get("csv_path") if audit_test_res.detalle else None,
        "veredicto": audit_test_res.detalle.get("veredicto") if audit_test_res.detalle else "NO_ENCONTRADO",
        "estado": audit_test_res.estado,
    }
    _write_json(out_dir / "auditoria_test_resumen.json", auditoria_test_resumen)

    error_analysis_df.to_csv(out_dir / "error_analysis_modelo_final_resumen.csv", index=False)
    (out_dir / "error_analysis_modelo_final_resumen.md").write_text(error_analysis_md, encoding="utf-8")

    # Tabla maestra insumos tesis: usar tabla de barrido/referencia del cierre y enriquecer con flags de selección
    if not tabla_maestra_df.empty:
        tdf = tabla_maestra_df.copy()
        final_variant = (((cierre_decision.get("modelo_hibrido_final") or {}).get("modelo_variante")) or "").strip()
        tdf["es_modelo_hibrido_final"] = (tdf["nombre_variante"].astype(str) == final_variant).astype(int)
        tdf.to_csv(out_dir / "tabla_maestra_insumos_tesis.csv", index=False)
    else:
        pd.DataFrame().to_csv(out_dir / "tabla_maestra_insumos_tesis.csv", index=False)

    decisiones_df = _decision_table(
        cierre_decision=cierre_decision,
        transformer_best=transformer_best,
        backbone_best_model=backbone_best_model,
        audit_veredicto=(audit_test_res.detalle.get("veredicto") if audit_test_res.detalle else None),
        xai_pendiente=(xai_outputs.get("n_hits", 0) == 0),
    )
    decisiones_df.to_csv(out_dir / "tabla_decisiones_metodologicas_clave.csv", index=False)
    decisiones_md_lines = ["# Decisiones metodológicas clave", ""]
    for _, r in decisiones_df.iterrows():
        decisiones_md_lines.append(
            f"- `{r['decision']}` = `{r['valor']}` | fuente: `{r['fuente']}` | estado: `{r['estado']}`"
        )
    (out_dir / "tabla_decisiones_metodologicas_clave.md").write_text(
        "\n".join(decisiones_md_lines) + "\n", encoding="utf-8"
    )

    (out_dir / "dataset_resumen.md").write_text(dataset_md, encoding="utf-8")
    (out_dir / "arquitectura_lexica_resumen.md").write_text(arq_lex_md, encoding="utf-8")

    _write_json(out_dir / "reporte_consolidacion_insumos.json", reporte_json)

    md = []
    md.append("# Reporte de consolidación de insumos de tesis")
    md.append("")
    md.append(f"- Run ID: `{run_id}`")
    md.append(f"- Fecha: {reporte_json['fecha']}")
    md.append("")
    md.append("## Fuentes de verdad seleccionadas")
    for k, v in reporte_json["fuentes_de_verdad"].items():
        md.append(f"- `{k}`: `{v}`")
    md.append("")
    md.append("## Estado por componente")
    for comp, estado in reporte_json["estado_componentes"].items():
        md.append(f"- `{comp}`: `{estado}`")
    md.append("")
    md.append("## Consistencia")
    md.append(f"- Consistencia global: `{ 'OK' if reporte_json['consistencia']['ok'] else 'CON_OBSERVACIONES' }`")
    for chk in reporte_json["consistencia"]["checks"]:
        md.append(f"- {chk['check']}: `{chk['ok']}`")
    md.append("")
    md.append("## Transformer standalone vs backbone híbrido")
    md.append(
        f"- Mejor transformer standalone en dev: `{transformer_best}`"
    )
    md.append(
        f"- Backbone ganador del híbrido en dev: `{backbone_best_model}`"
    )
    md.append(
        f"- Coinciden: `{reporte_json['resumen_decision_transformer_vs_backbone']['coinciden']}`"
    )
    md.append("")
    md.append("## Estado de fases pendientes")
    md.append(
        f"- Auditoría de test: `{auditoria_test_resumen.get('veredicto')}`"
    )
    md.append(
        f"- Test pendiente: `{reporte_json['estado_fase_final']['test_pendiente']}`"
    )
    md.append(
        f"- xAI pendiente: `{reporte_json['estado_fase_final']['xai_pendiente']}`"
    )
    md.append("")
    md.append("## Advertencias")
    if warnings:
        for w in warnings:
            md.append(f"- {w}")
    else:
        md.append("- No se detectaron advertencias de consistencia relevantes.")
    md.append("")
    md.append("## Archivos exportados")
    for name in [
        "dataset_resumen.csv",
        "dataset_resumen.md",
        "arquitectura_lexica_resumen.csv",
        "arquitectura_lexica_resumen.md",
        "baselines_dev_resumen.csv",
        "transformers_baseline_resumen.csv",
        "backbones_hibrido_resumen.csv",
        "transformer_vs_backbone_decision.csv",
        "hibridos_dev_resumen.csv",
        "modelo_final_dev_resumen.json",
        "auditoria_test_resumen.json",
        "error_analysis_modelo_final_resumen.csv",
        "error_analysis_modelo_final_resumen.md",
        "tabla_maestra_insumos_tesis.csv",
        "tabla_decisiones_metodologicas_clave.csv",
        "tabla_decisiones_metodologicas_clave.md",
        "reporte_consolidacion_insumos.json",
    ]:
        md.append(f"- `{out_dir / name}`")
    (out_dir / "reporte_consolidacion_insumos.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
