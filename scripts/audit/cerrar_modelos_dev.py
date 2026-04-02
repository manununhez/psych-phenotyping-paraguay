#!/usr/bin/env python3
"""
Cierra formalmente la selección de modelos en dev y genera artefactos de decisión.

Salida:
  data/outputs/cierre_modelos_dev_<timestamp>/
    - ranking_modelos_dev.csv
    - rubrica_seleccion_modelos.csv
    - decision_modelo_final.md
    - decision_modelo_final.json
    - lista_modelos_para_test.json
    - riesgos_y_limitaciones_dev.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

BACKBONE_TO_MODEL = {
    "beto": "BETO",
    "roberta_clinical": "ROBERTA_CLINICAL",
    "roberta_biomedical": "ROBERTA_BIOMEDICAL",
}

VALID_TRANSFORMER_MODELS = set(BACKBONE_TO_MODEL.values())


def _find_latest_dir(base: Path, prefix: str) -> Path | None:
    pattern = f"{prefix}_*" if prefix else "*"
    candidates = [p for p in base.glob(pattern) if p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _safe_json(path: Path) -> tuple[dict | None, str | None]:
    try:
        if not path.exists():
            return None, "no_existe"
        if path.stat().st_size == 0:
            return None, "vacio"
        return json.loads(path.read_text(encoding="utf-8")), None
    except Exception as e:
        return None, f"json_invalido: {e}"


def _freeze_version(freeze_info: dict, *keys: str) -> str | None:
    versiones = (freeze_info or {}).get("versiones_congeladas", {}) or {}
    for key in keys:
        version = ((versiones.get(key) or {}).get("version"))
        if version:
            return version
    return None


def _normalizar_modelo_transformer(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s_up = s.upper()
    if s_up in VALID_TRANSFORMER_MODELS:
        return s_up
    s_low = s.lower()
    return BACKBONE_TO_MODEL.get(s_low)


def _resolver_seleccion_transformer(outputs_dir: Path) -> dict:
    manifest_latest = outputs_dir / "backbone_artifacts_manifest_latest.json"
    latest_sel = outputs_dir / "transformer_baseline_selection_latest.json"
    candidatos: list[tuple[str, Path]] = []

    manifest_payload, _ = _safe_json(manifest_latest)
    if manifest_payload:
        sel = manifest_payload.get("latest_valid_selection", {}) or {}
        p = sel.get("ruta")
        if p:
            candidatos.append(("manifest", Path(p)))

    if latest_sel.exists():
        candidatos.append(("latest", latest_sel))

    for p in sorted(outputs_dir.glob("transformer_baseline_selection_*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.name == "transformer_baseline_selection_latest.json":
            continue
        candidatos.append(("scan", p))

    vistos = set()
    for fuente, path in candidatos:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in vistos:
            continue
        vistos.add(key)

        payload, err = _safe_json(path)
        if payload is None:
            continue
        modelo = _normalizar_modelo_transformer(
            ((payload.get("mejor_transformer_baseline", {}) or {}).get("modelo"))
        )
        if not modelo:
            continue
        return {
            "valido": True,
            "fuente": fuente,
            "path": str(path),
            "modelo": modelo,
            "payload": payload,
            "error": None,
        }

    return {
        "valido": False,
        "fuente": None,
        "path": None,
        "modelo": None,
        "payload": {},
        "error": "sin_artefacto_valido",
    }


def _resolver_comparacion_backbones(outputs_dir: Path) -> dict:
    manifest_latest = outputs_dir / "backbone_artifacts_manifest_latest.json"
    pointer_latest = outputs_dir / "comparacion_backbones_hibrido_latest.json"

    candidatos: list[tuple[str, Path]] = []

    manifest_payload, _ = _safe_json(manifest_latest)
    if manifest_payload:
        cmp_info = manifest_payload.get("latest_valid_backbone_comparison", {}) or {}
        p = cmp_info.get("ruta")
        if p:
            candidatos.append(("manifest", Path(p)))

    pointer_payload, _ = _safe_json(pointer_latest)
    if pointer_payload:
        cmp_info = pointer_payload.get("latest_valid_backbone_comparison", {}) or {}
        p = cmp_info.get("ruta")
        if p:
            candidatos.append(("pointer", Path(p)))

    for p in sorted(outputs_dir.glob("comparacion_backbones_hibrido_*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_dir():
            candidatos.append(("scan", p))

    vistos = set()
    for fuente, run_dir in candidatos:
        if not run_dir.exists() or not run_dir.is_dir():
            continue
        key = str(run_dir.resolve())
        if key in vistos:
            continue
        vistos.add(key)

        csv_path = run_dir / "comparacion_backbones_hibrido.csv"
        json_path = run_dir / "comparacion_backbones_hibrido.json"
        if not csv_path.exists() or not json_path.exists():
            continue

        try:
            df = pd.read_csv(csv_path)
        except Exception:
            continue
        if df.empty or not {"backbone", "macro_f1"}.issubset(df.columns):
            continue

        dff = df.copy()
        dff["backbone"] = dff["backbone"].astype(str).str.lower()
        dff["macro_f1"] = pd.to_numeric(dff["macro_f1"], errors="coerce")
        dff = dff[dff["backbone"].isin(set(BACKBONE_TO_MODEL.keys()))]
        dff = dff.dropna(subset=["macro_f1"])
        if dff.empty:
            continue

        top = dff.sort_values("macro_f1", ascending=False).iloc[0]
        best_backbone = str(top["backbone"])
        best_model = BACKBONE_TO_MODEL.get(best_backbone)
        best_macro = float(top["macro_f1"])
        delta_vs_beto = None
        if (dff["backbone"] == "beto").any():
            beto_macro = float(dff.loc[dff["backbone"] == "beto", "macro_f1"].iloc[0])
            delta_vs_beto = best_macro - beto_macro

        return {
            "valido": True,
            "fuente": fuente,
            "run_dir": str(run_dir),
            "csv_path": str(csv_path),
            "json_path": str(json_path),
            "best_backbone": best_backbone,
            "best_backbone_modelo": best_model,
            "best_macro_f1": best_macro,
            "delta_vs_beto": delta_vs_beto,
        }

    return {
        "valido": False,
        "fuente": None,
        "run_dir": None,
        "csv_path": None,
        "json_path": None,
        "best_backbone": None,
        "best_backbone_modelo": None,
        "best_macro_f1": None,
        "delta_vs_beto": None,
    }


def _minmax(series: pd.Series) -> pd.Series:
    s = series.astype(float)
    mn, mx = s.min(), s.max()
    if np.isclose(mx, mn):
        return pd.Series(np.ones(len(s)), index=s.index)
    return (s - mn) / (mx - mn)


def _build_pool(master: pd.DataFrame, rank_df: pd.DataFrame) -> pd.DataFrame:
    df = master.copy()
    if "base_variante_c" in rank_df.columns:
        c_map = (
            rank_df[["nombre_variante", "base_variante_c"]]
            .dropna(subset=["base_variante_c"])
            .drop_duplicates("nombre_variante")
        )
        df = df.merge(c_map, on="nombre_variante", how="left")
    else:
        df["base_variante_c"] = np.nan

    df["source"] = df["source"].astype(str)
    df["fase"] = df["fase"].astype(str)
    df["seed"] = pd.to_numeric(df["seed"], errors="coerce")
    df["model_key"] = df["nombre_variante"]

    mask_c = (
        (df["source"] == "barrido")
        & (df["fase"] == "C")
        & df["base_variante_c"].notna()
    )
    df.loc[mask_c, "model_key"] = df.loc[mask_c, "base_variante_c"]

    fase_priority = {"C": 3, "B": 2, "A": 1}
    df["fase_prio"] = df["fase"].map(fase_priority).fillna(0)
    df["seed_norm"] = df["seed"].fillna(-1)
    df = df.sort_values(
        ["model_key", "seed_norm", "fase_prio"], ascending=[True, True, False]
    )
    return df.drop_duplicates(subset=["model_key", "seed_norm"], keep="first").copy()


def _aggregate_models(pool: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "macro_f1",
        "balanced_accuracy",
        "precision_macro",
        "recall_macro",
        "f1_ansiedad",
        "f1_depresion",
        "n_features",
        "n_train",
        "n_eval",
    ]
    for col in metric_cols:
        pool[col] = pd.to_numeric(pool[col], errors="coerce")

    rows = []
    for key, group in pool.groupby("model_key", dropna=False):
        rep = group.sort_values(["fase_prio", "seed_norm"], ascending=[False, True]).iloc[
            0
        ]
        rows.append(
            {
                "modelo_variante": key,
                "source": rep["source"],
                "nombre_variante_representativo": rep["nombre_variante"],
                "split": "dev",
                "perfil": rep.get("perfil", np.nan),
                "modelo": rep.get("modelo", np.nan),
                "text_backbone": rep.get("text_backbone", np.nan),
                "context_prefixes": rep.get("context_prefixes", np.nan),
                "run_id_features": rep.get("run_id_features", np.nan),
                "run_id_train_referencia": rep.get("run_id_train", np.nan),
                "fase_referencia": rep.get("fase", np.nan),
                "llm_activo": pd.to_numeric(
                    rep.get("llm_activo", np.nan), errors="coerce"
                ),
                "sentimiento_activo": pd.to_numeric(
                    rep.get("sentimiento_activo", np.nan), errors="coerce"
                ),
                "beto_activo": pd.to_numeric(
                    rep.get("beto_activo", np.nan), errors="coerce"
                ),
                "template_activo": pd.to_numeric(
                    rep.get("template_activo", np.nan), errors="coerce"
                ),
                "feat_activo": pd.to_numeric(
                    rep.get("feat_activo", np.nan), errors="coerce"
                ),
                "reglas_activas": pd.to_numeric(
                    rep.get("reglas_activas", np.nan), errors="coerce"
                ),
                "medicacion_activa": pd.to_numeric(
                    rep.get("medicacion_activa", np.nan), errors="coerce"
                ),
                "n_features": (
                    float(group["n_features"].dropna().median())
                    if group["n_features"].notna().any()
                    else np.nan
                ),
                "n_train": (
                    float(group["n_train"].dropna().median())
                    if group["n_train"].notna().any()
                    else np.nan
                ),
                "n_eval": (
                    float(group["n_eval"].dropna().median())
                    if group["n_eval"].notna().any()
                    else np.nan
                ),
                "macro_f1_mean": group["macro_f1"].mean(),
                "macro_f1_std": group["macro_f1"].std(ddof=0) if len(group) > 1 else 0.0,
                "balanced_accuracy_mean": group["balanced_accuracy"].mean(),
                "balanced_accuracy_std": (
                    group["balanced_accuracy"].std(ddof=0) if len(group) > 1 else 0.0
                ),
                "f1_ansiedad_mean": group["f1_ansiedad"].mean(),
                "f1_depresion_mean": group["f1_depresion"].mean(),
                "precision_macro_mean": group["precision_macro"].mean(),
                "recall_macro_mean": group["recall_macro"].mean(),
                "n_seeds": (
                    int(group["seed"].dropna().nunique())
                    if group["seed"].notna().any()
                    else 1
                ),
                "seeds": (
                    ",".join(str(int(s)) for s in sorted(group["seed"].dropna().unique()))
                    if group["seed"].notna().any()
                    else ""
                ),
            }
        )
    return pd.DataFrame(rows)


def _apply_rubric(rank_df: pd.DataFrame, top_barrido: int) -> tuple[pd.DataFrame, str, float]:
    barrido_all = rank_df[rank_df["source"] == "barrido"].copy()
    keep_barrido = pd.concat(
        [
            barrido_all.sort_values("macro_f1_mean", ascending=False).head(top_barrido),
            barrido_all[barrido_all["n_seeds"] >= 3],
        ]
    ).drop_duplicates("modelo_variante")

    rank_df = pd.concat(
        [
            rank_df[rank_df["source"].isin(["baseline_texto", "hibrido_referencia"])],
            keep_barrido,
        ]
    ).drop_duplicates("modelo_variante")
    rank_df = rank_df.reset_index(drop=True)

    textual = rank_df[rank_df["source"] == "baseline_texto"].copy()
    if textual.empty:
        raise ValueError(
            "No se encontraron baselines textuales en la tabla maestra para construir cierre."
        )
    best_textual_row = textual.sort_values("macro_f1_mean", ascending=False).iloc[0]
    best_textual_name = str(best_textual_row["modelo_variante"])
    best_textual_macro = float(best_textual_row["macro_f1_mean"])

    rank_df["min_f1_clase"] = rank_df[["f1_ansiedad_mean", "f1_depresion_mean"]].min(
        axis=1, skipna=True
    )
    rank_df["min_f1_clase"] = rank_df["min_f1_clase"].fillna(rank_df["macro_f1_mean"] * 0.9)

    rank_df["score_macro"] = _minmax(rank_df["macro_f1_mean"])
    rank_df["score_bacc"] = _minmax(
        rank_df["balanced_accuracy_mean"].fillna(rank_df["macro_f1_mean"])
    )
    rank_df["score_minf1"] = _minmax(rank_df["min_f1_clase"])
    rank_df["score_stability"] = np.where(
        rank_df["n_seeds"] >= 3,
        (1 - (rank_df["macro_f1_std"] / 0.03)).clip(lower=0, upper=1),
        0.55,
    )
    rank_df["gap_vs_best_textual"] = best_textual_macro - rank_df["macro_f1_mean"]
    rank_df["score_gap_textual"] = (
        1 - (rank_df["gap_vs_best_textual"].clip(lower=0) / 0.15)
    ).clip(lower=0, upper=1)

    rank_df["score_cuantitativo"] = (
        0.40 * rank_df["score_macro"]
        + 0.20 * rank_df["score_bacc"]
        + 0.15 * rank_df["score_minf1"]
        + 0.15 * rank_df["score_stability"]
        + 0.10 * rank_df["score_gap_textual"]
    )

    hy_mask = rank_df["source"].isin(["barrido", "hibrido_referencia"])
    if rank_df.loc[hy_mask, "n_features"].notna().any():
        hy_min = rank_df.loc[hy_mask, "n_features"].min()
        hy_max = rank_df.loc[hy_mask, "n_features"].max()
        rank_df["parsimonia"] = np.where(
            hy_mask,
            1 - ((rank_df["n_features"] - hy_min) / (hy_max - hy_min + 1e-9)),
            np.nan,
        )
    else:
        rank_df["parsimonia"] = np.nan

    rank_df.loc[rank_df["source"] == "baseline_texto", "parsimonia"] = (
        rank_df.loc[rank_df["source"] == "baseline_texto", "modelo_variante"]
        .map(
            {
                "DUMMY": 1.0,
                "TF-IDF": 0.90,
                "BETO": 0.72,
                "ROBERTA_BIOMEDICAL": 0.62,
                "ROBERTA_CLINICAL": 0.62,
            }
        )
        .fillna(0.60)
    )
    rank_df["parsimonia"] = rank_df["parsimonia"].clip(lower=0, upper=1).fillna(0.50)

    rank_df["auditabilidad_clinica"] = 0.40
    is_barrido = rank_df["source"] == "barrido"
    rank_df.loc[is_barrido, "auditabilidad_clinica"] = (
        0.55
        + 0.15 * rank_df.loc[is_barrido, "reglas_activas"].fillna(0)
        + 0.10 * rank_df.loc[is_barrido, "feat_activo"].fillna(0)
        + 0.05 * (rank_df.loc[is_barrido, "perfil"].astype(str).eq("py")).astype(float)
        - 0.10 * rank_df.loc[is_barrido, "template_activo"].fillna(0)
        - 0.10 * rank_df.loc[is_barrido, "medicacion_activa"].fillna(0)
        - 0.07 * rank_df.loc[is_barrido, "llm_activo"].fillna(0)
    ).clip(lower=0, upper=1)
    rank_df.loc[rank_df["source"] == "hibrido_referencia", "auditabilidad_clinica"] = 0.58
    rank_df.loc[rank_df["source"] == "baseline_texto", "auditabilidad_clinica"] = (
        rank_df.loc[rank_df["source"] == "baseline_texto", "modelo_variante"]
        .map(
            {
                "DUMMY": 0.20,
                "TF-IDF": 0.34,
                "BETO": 0.36,
                "ROBERTA_BIOMEDICAL": 0.30,
                "ROBERTA_CLINICAL": 0.30,
            }
        )
        .fillna(0.30)
    )

    rank_df["interpretabilidad_aporte"] = 0.40
    rank_df.loc[is_barrido, "interpretabilidad_aporte"] = (
        0.45
        + 0.20 * rank_df.loc[is_barrido, "reglas_activas"].fillna(0)
        + 0.10 * rank_df.loc[is_barrido, "feat_activo"].fillna(0)
        + 0.05 * (rank_df.loc[is_barrido, "perfil"].astype(str).eq("py")).astype(float)
        - 0.05 * rank_df.loc[is_barrido, "llm_activo"].fillna(0)
    ).clip(lower=0, upper=1)

    contexto_activo = rank_df.get("contexto_activo", rank_df["beto_activo"]).fillna(
        rank_df["beto_activo"].fillna(0)
    )
    only_context = (
        is_barrido
        & (contexto_activo == 1)
        & (rank_df["reglas_activas"].fillna(0) == 0)
        & (rank_df["feat_activo"].fillna(0) == 0)
    )
    rank_df.loc[only_context, "interpretabilidad_aporte"] -= 0.10

    rank_df.loc[rank_df["source"] == "baseline_texto", "interpretabilidad_aporte"] = (
        rank_df.loc[rank_df["source"] == "baseline_texto", "modelo_variante"]
        .map(
            {
                "DUMMY": 0.20,
                "TF-IDF": 0.45,
                "BETO": 0.40,
                "ROBERTA_BIOMEDICAL": 0.36,
                "ROBERTA_CLINICAL": 0.36,
            }
        )
        .fillna(0.35)
    )
    rank_df["interpretabilidad_aporte"] = rank_df["interpretabilidad_aporte"].clip(
        lower=0, upper=1
    )

    rank_df["penalizacion_riesgo"] = 0.0
    rank_df.loc[is_barrido, "penalizacion_riesgo"] = (
        0.08 * rank_df.loc[is_barrido, "template_activo"].fillna(0)
        + 0.06 * rank_df.loc[is_barrido, "medicacion_activa"].fillna(0)
        + 0.04 * rank_df.loc[is_barrido, "llm_activo"].fillna(0)
    )
    rank_df.loc[only_context, "penalizacion_riesgo"] += 0.05

    rank_df["score_metodologico"] = 0.5 * rank_df["parsimonia"] + 0.5 * rank_df[
        "auditabilidad_clinica"
    ]
    rank_df["score_final_seleccion"] = (
        0.60 * rank_df["score_cuantitativo"]
        + 0.25 * rank_df["score_metodologico"]
        + 0.15 * rank_df["interpretabilidad_aporte"]
        - rank_df["penalizacion_riesgo"]
    ).clip(lower=0, upper=1)

    tags = []
    for _, row in rank_df.iterrows():
        t = []
        if row["source"] == "barrido":
            if (row.get("template_activo", 0) or 0) >= 1:
                t.append("dependencia_template")
            if (row.get("medicacion_activa", 0) or 0) >= 1:
                t.append("medicacion_como_proxy")
            if (row.get("llm_activo", 0) or 0) >= 1:
                t.append("llm_sin_ganancia_robusta")
            if (
                (row.get("contexto_activo", row.get("beto_activo", 0)) or 0) >= 1
                and (row.get("reglas_activas", 0) or 0) == 0
                and (row.get("feat_activo", 0) or 0) == 0
            ):
                t.append("casi_solo_contexto")
        elif row["source"] == "baseline_texto":
            if "ROBERTA" in str(row["modelo_variante"]) or "BETO" in str(
                row["modelo_variante"]
            ):
                t.append("baja_auditabilidad_clinica")
            if str(row["modelo_variante"]) == "DUMMY":
                t.append("baseline_de_control")
        else:
            t.append("referencia_historica_hibrida")
        tags.append("|".join(t))
    rank_df["riesgos_metodologicos"] = tags

    rank_df = rank_df.sort_values(
        ["score_final_seleccion", "macro_f1_mean", "balanced_accuracy_mean"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    rank_df["posicion_final"] = np.arange(1, len(rank_df) + 1)

    return rank_df, best_textual_name, best_textual_macro


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cierra formalmente la comparación de modelos en dev."
    )
    parser.add_argument(
        "--barrido-dir",
        default="",
        help="Directorio barrido_hibridos/<timestamp>. Si se omite, usa el más reciente.",
    )
    parser.add_argument(
        "--freeze-dir",
        default="",
        help="Directorio freeze_lexico_<timestamp>. Si se omite, usa el más reciente.",
    )
    parser.add_argument(
        "--out-root", default="data/outputs", help="Directorio base de salidas."
    )
    parser.add_argument(
        "--top-barrido",
        type=int,
        default=30,
        help="Cantidad de variantes barrido no multiseed a considerar en ranking final.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe archivos, solo imprime resumen.",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[2]
    outputs_dir = repo / args.out_root
    barridos_root = outputs_dir / "barridos_hibridos"

    barrido_dir = (
        (repo / args.barrido_dir).resolve()
        if args.barrido_dir
        else _find_latest_dir(barridos_root, "")
    )
    if barrido_dir is None or not barrido_dir.exists():
        raise SystemExit("No se encontró directorio de barrido para cierre de modelos.")

    if args.freeze_dir:
        freeze_dir = (repo / args.freeze_dir).resolve()
    else:
        freeze_dir = _find_latest_dir(outputs_dir, "freeze_lexico")
    if freeze_dir is None or not freeze_dir.exists():
        raise SystemExit("No se encontró freeze léxico para registrar en el cierre.")

    master_csv = barrido_dir / "tabla_maestra_comparativa.csv"
    rank_csv = barrido_dir / "ranking_variantes.csv"
    freeze_json = freeze_dir / "freeze_lexico_resumen.json"

    if not master_csv.exists():
        raise SystemExit(f"No existe {master_csv}")
    if not rank_csv.exists():
        raise SystemExit(f"No existe {rank_csv}")

    master = pd.read_csv(master_csv)
    if not master["eval_split"].fillna("").eq("dev").all():
        raise SystemExit("La tabla maestra contiene filas fuera de dev.")
    rank_in = pd.read_csv(rank_csv)

    pool = _build_pool(master, rank_in)
    rank_df = _aggregate_models(pool)
    rank_df, best_textual_name, best_textual_macro = _apply_rubric(
        rank_df, args.top_barrido
    )

    hy_pool = rank_df[rank_df["source"] == "barrido"]
    hy_pool_pref = hy_pool[hy_pool["n_seeds"] >= 3]
    if hy_pool_pref.empty:
        hy_pool_pref = hy_pool
    if hy_pool_pref.empty:
        raise SystemExit("No hay variantes híbridas para seleccionar modelo final.")
    hy_final = hy_pool_pref.sort_values(
        ["score_final_seleccion", "macro_f1_mean", "balanced_accuracy_mean"],
        ascending=[False, False, False],
    ).iloc[0]
    hy_final_key = str(hy_final["modelo_variante"])

    transformer_candidates = rank_df[
        (rank_df["source"] == "baseline_texto")
        & rank_df["modelo_variante"].astype(str).isin(
            ["BETO", "ROBERTA_CLINICAL", "ROBERTA_BIOMEDICAL"]
        )
    ].copy()
    best_transformer_name = None
    if not transformer_candidates.empty:
        best_transformer_name = str(
            transformer_candidates.sort_values("macro_f1_mean", ascending=False).iloc[0][
                "modelo_variante"
            ]
        )

    selection_04c = _resolver_seleccion_transformer(outputs_dir)
    selected_transformer_04c = selection_04c.get("modelo")
    selection_04c_path = Path(selection_04c["path"]) if selection_04c.get("path") else None

    backbone_cmp = _resolver_comparacion_backbones(outputs_dir)
    selected_transformer_backbone_cmp = backbone_cmp.get("best_backbone_modelo")

    selected_transformer_final = None
    selected_transformer_source = None
    for model, source in [
        (selected_transformer_backbone_cmp, "comparacion_backbones_hibrido"),
        (selected_transformer_04c, "seleccion_transformer_04c"),
        (best_transformer_name, "mejor_transformer_en_tabla"),
    ]:
        if not model:
            continue
        if (rank_df["modelo_variante"].astype(str) == model).any():
            selected_transformer_final = model
            selected_transformer_source = source
            break

    shortlist = []
    for model in [hy_final_key, "TF-IDF", selected_transformer_final, best_textual_name]:
        if not model:
            continue
        if model not in shortlist and (rank_df["modelo_variante"] == model).any():
            shortlist.append(model)
    shortlist = shortlist[:4]

    rank_df["recomendacion"] = "NO_PASA"
    rank_df.loc[rank_df["modelo_variante"].isin(shortlist), "recomendacion"] = "PASA_A_TEST"

    reserve = []
    reserve += (
        rank_df[
            (rank_df["source"] == "barrido")
            & (~rank_df["modelo_variante"].isin(shortlist))
        ]
        .head(5)["modelo_variante"]
        .tolist()
    )
    reserve += (
        rank_df[
            (rank_df["source"] == "baseline_texto")
            & (~rank_df["modelo_variante"].isin(shortlist))
        ]
        .head(1)["modelo_variante"]
        .tolist()
    )
    rank_df.loc[
        rank_df["modelo_variante"].isin(reserve)
        & (rank_df["recomendacion"] != "PASA_A_TEST"),
        "recomendacion",
    ] = "RESERVA"

    freeze_info = (
        json.loads(freeze_json.read_text(encoding="utf-8")) if freeze_json.exists() else {}
    )

    now = datetime.now()
    out_dir = outputs_dir / f"cierre_modelos_dev_{now.strftime('%Y%m%d_%H%M%S')}"

    if args.dry_run:
        print("[dry-run] Directorio barrido:", barrido_dir)
        print("[dry-run] Freeze:", freeze_dir)
        print("[dry-run] Híbrido final:", hy_final_key)
        print(
            "[dry-run] Transformer seleccionado:",
            selected_transformer_final,
            "| fuente:",
            selected_transformer_source,
        )
        if backbone_cmp.get("valido"):
            print(
                "[dry-run] Comparación backbone válida:",
                backbone_cmp.get("run_dir"),
                "| best:",
                backbone_cmp.get("best_backbone"),
            )
        print("[dry-run] Lista corta:", ", ".join(shortlist))
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    export_cols = [
        "posicion_final",
        "recomendacion",
        "modelo_variante",
        "source",
        "split",
        "perfil",
        "modelo",
        "text_backbone",
        "context_prefixes",
        "macro_f1_mean",
        "balanced_accuracy_mean",
        "f1_ansiedad_mean",
        "f1_depresion_mean",
        "precision_macro_mean",
        "recall_macro_mean",
        "macro_f1_std",
        "n_seeds",
        "seeds",
        "gap_vs_best_textual",
        "n_features",
        "n_train",
        "n_eval",
        "llm_activo",
        "sentimiento_activo",
        "beto_activo",
        "template_activo",
        "feat_activo",
        "reglas_activas",
        "medicacion_activa",
        "parsimonia",
        "auditabilidad_clinica",
        "interpretabilidad_aporte",
        "penalizacion_riesgo",
        "score_cuantitativo",
        "score_metodologico",
        "score_final_seleccion",
        "riesgos_metodologicos",
        "run_id_features",
        "run_id_train_referencia",
        "fase_referencia",
        "nombre_variante_representativo",
    ]
    rank_export = rank_df[export_cols].copy()
    rank_export.to_csv(out_dir / "ranking_modelos_dev.csv", index=False)

    rubrica = pd.DataFrame(
        [
            {
                "componente": "Cuantitativo",
                "criterio": "macro_f1 (normalizado)",
                "peso": 0.40,
                "regla": "Mayor es mejor; criterio principal",
            },
            {
                "componente": "Cuantitativo",
                "criterio": "balanced_accuracy (normalizado)",
                "peso": 0.20,
                "regla": "Desempate por equilibrio de clases",
            },
            {
                "componente": "Cuantitativo",
                "criterio": "min(f1_ansiedad,f1_depresion)",
                "peso": 0.15,
                "regla": "Penaliza desbalance por clase",
            },
            {
                "componente": "Cuantitativo",
                "criterio": "estabilidad por seeds",
                "peso": 0.15,
                "regla": "1-std/0.03; sin multiseed => 0.55",
            },
            {
                "componente": "Cuantitativo",
                "criterio": "brecha vs mejor baseline textual",
                "peso": 0.10,
                "regla": "1-gap/0.15 truncado [0,1]",
            },
            {
                "componente": "Metodológico",
                "criterio": "parsimonia",
                "peso": 0.50,
                "regla": "Favorece menor complejidad y menor n_features",
            },
            {
                "componente": "Metodológico",
                "criterio": "auditabilidad clínica",
                "peso": 0.50,
                "regla": "Favorece trazabilidad clínica y penaliza template/medicación/LLM",
            },
            {
                "componente": "Interpretabilidad",
                "criterio": "aporte explicable",
                "peso": 1.00,
                "regla": "Favorece señal clínica interpretable para tesis/paper",
            },
            {
                "componente": "Penalización",
                "criterio": "riesgos metodológicos",
                "peso": 1.00,
                "regla": "template +0.08; medicación +0.06; LLM +0.04; casi solo contexto +0.05",
            },
        ]
    )
    rubrica.to_csv(out_dir / "rubrica_seleccion_modelos.csv", index=False)

    shortlist_rows = rank_export[rank_export["modelo_variante"].isin(shortlist)].sort_values(
        "posicion_final"
    )
    hy_row = rank_export[rank_export["modelo_variante"] == hy_final_key].iloc[0]
    hy_final_backbone = (
        str(hy_row.get("text_backbone"))
        if pd.notna(hy_row.get("text_backbone"))
        else "no_reportado"
    )

    modelos_test = []
    for _, model_row in shortlist_rows.iterrows():
        if model_row["modelo_variante"] == hy_final_key:
            just = "Híbrido final seleccionado por rúbrica multicriterio"
        elif model_row["modelo_variante"] == best_textual_name:
            just = "Mejor baseline textual por macro_f1 en dev"
        elif model_row["modelo_variante"] == "TF-IDF":
            just = "Baseline léxico-estadístico fuerte y parsimonioso"
        elif model_row["modelo_variante"] == selected_transformer_final:
            just = (
                "Transformer baseline seleccionado para shortlist "
                f"(fuente: {selected_transformer_source})"
            )
        else:
            just = "Modelo incluido por criterio metodológico de control"

        modelos_test.append(
            {
                "modelo_variante": model_row["modelo_variante"],
                "source": model_row["source"],
                "perfil": model_row["perfil"],
                "modelo": model_row["modelo"],
                "macro_f1_dev": (
                    float(model_row["macro_f1_mean"])
                    if pd.notna(model_row["macro_f1_mean"])
                    else None
                ),
                "balanced_accuracy_dev": (
                    float(model_row["balanced_accuracy_mean"])
                    if pd.notna(model_row["balanced_accuracy_mean"])
                    else None
                ),
                "score_final_seleccion": (
                    float(model_row["score_final_seleccion"])
                    if pd.notna(model_row["score_final_seleccion"])
                    else None
                ),
                "justificacion_corta": just,
            }
        )

    decision = {
        "fecha_decision": now.isoformat(timespec="seconds"),
        "split_decision": "dev",
        "run_barrido": str(barrido_dir),
        "tabla_fuente": str(master_csv),
        "freeze_lexico": {
            "freeze_id": freeze_info.get("freeze_id", freeze_dir.name),
            "ruta": str(freeze_dir),
            "commit": freeze_info.get("repositorio", {}).get("git_commit_short"),
            "version_core": _freeze_version(freeze_info, "Concept_Core"),
            "version_py": _freeze_version(freeze_info, "Concept_PY"),
        },
        "regla_decision": {
            "principal": "score_final_seleccion (rúbrica multicriterio); macro_f1 es criterio principal dentro del bloque cuantitativo",
            "desempates": [
                "balanced_accuracy",
                "estabilidad por seeds",
                "parsimonia",
                "auditabilidad clínica",
            ],
            "penalizaciones": [
                "template",
                "medicación como proxy diagnóstica",
                "LLM sin evidencia robusta",
                "configuraciones casi solo contexto",
            ],
        },
        "modelo_hibrido_final": {
            "modelo_variante": hy_final_key,
            "source": hy_row["source"],
            "perfil": hy_row["perfil"],
            "modelo": hy_row["modelo"],
            "macro_f1_dev": float(hy_row["macro_f1_mean"]),
            "balanced_accuracy_dev": float(hy_row["balanced_accuracy_mean"]),
            "f1_ansiedad_dev": (
                float(hy_row["f1_ansiedad_mean"])
                if pd.notna(hy_row["f1_ansiedad_mean"])
                else None
            ),
            "f1_depresion_dev": (
                float(hy_row["f1_depresion_mean"])
                if pd.notna(hy_row["f1_depresion_mean"])
                else None
            ),
            "n_seeds": int(hy_row["n_seeds"]),
            "macro_f1_std": float(hy_row["macro_f1_std"]),
            "score_final_seleccion": float(hy_row["score_final_seleccion"]),
            "riesgos_metodologicos": hy_row["riesgos_metodologicos"],
        },
        "mejor_baseline_textual_dev": {
            "modelo_variante": best_textual_name,
            "macro_f1_dev": best_textual_macro,
            "balanced_accuracy_dev": float(
                rank_export[rank_export["modelo_variante"] == best_textual_name][
                    "balanced_accuracy_mean"
                ].iloc[0]
            ),
            "brecha_hibrido_vs_mejor_textual": float(
                hy_row["macro_f1_mean"] - best_textual_macro
            ),
        },
        "mejor_transformer_baseline_dev": (
            {
                "modelo_variante": best_transformer_name,
                "macro_f1_dev": float(
                    rank_export[rank_export["modelo_variante"] == best_transformer_name][
                        "macro_f1_mean"
                    ].iloc[0]
                )
                if best_transformer_name
                else None,
            }
            if best_transformer_name
            else None
        ),
        "seleccion_transformer_04c": {
            "path": str(selection_04c_path) if selection_04c_path else None,
            "fuente": selection_04c.get("fuente"),
            "modelo_seleccionado_04c": selected_transformer_04c,
            "valido": bool(selection_04c.get("valido")),
            "error": selection_04c.get("error"),
        },
        "comparacion_controlada_backbones_hibrido": {
            "valido": bool(backbone_cmp.get("valido")),
            "fuente": backbone_cmp.get("fuente"),
            "run_dir": backbone_cmp.get("run_dir"),
            "csv_path": backbone_cmp.get("csv_path"),
            "json_path": backbone_cmp.get("json_path"),
            "backbone_ganador": backbone_cmp.get("best_backbone"),
            "modelo_transformer_ganador": backbone_cmp.get("best_backbone_modelo"),
            "macro_f1_ganador": backbone_cmp.get("best_macro_f1"),
            "delta_vs_beto": backbone_cmp.get("delta_vs_beto"),
        },
        "criterio_transformer_para_shortlist": {
            "modelo_transformer_usado_en_shortlist": selected_transformer_final,
            "fuente": selected_transformer_source,
        },
        "modelos_que_pasan_a_test": modelos_test,
        "nota_freeze": "A partir de esta decisión no se deben cambiar reglas, features ni configuración en función de resultados de test.",
    }

    (out_dir / "decision_modelo_final.json").write_text(
        json.dumps(decision, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "lista_modelos_para_test.json").write_text(
        json.dumps({"split": "test", "modelos": modelos_test}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = []
    md.append("# Decisión formal de cierre de modelos en dev")
    md.append("")
    md.append(f"- Fecha de decisión: {decision['fecha_decision']}")
    md.append("- Split usado para decidir: `dev` (sin uso de `test`)")
    md.append(f"- Corrida de resultados consolidada: `{barrido_dir.name}`")
    md.append(f"- Freeze léxico/reglas: `{decision['freeze_lexico']['freeze_id']}`")
    md.append(f"- Versión Core congelada: `{decision['freeze_lexico']['version_core']}`")
    md.append(
        f"- Versión PY congelada: `{decision['freeze_lexico']['version_py']}`"
    )
    md.append("")
    md.append("## Regla de decisión aplicada")
    md.append("- Métrica principal dentro de la rúbrica: `macro_f1` en `dev`.")
    md.append(
        "- Desempates cuantitativos: `balanced_accuracy`, `min(f1_ansiedad, f1_depresion)`, estabilidad por seeds."
    )
    md.append(
        "- Criterios metodológicos: parsimonia, auditabilidad clínica y trazabilidad de señales."
    )
    md.append(
        "- Penalizaciones explícitas: dependencia de template, medicación como proxy diagnóstica, LLM sin evidencia robusta y configuraciones casi solo contexto."
    )
    md.append("")
    md.append("## Modelo híbrido final congelado")
    md.append(f"- Variante: `{hy_final_key}`")
    md.append(f"- Backbone contextual reportado en la variante: `{hy_final_backbone}`")
    md.append(
        f"- Desempeño en dev: macro_f1={hy_row['macro_f1_mean']:.6f}, balanced_accuracy={hy_row['balanced_accuracy_mean']:.6f}"
    )
    md.append(
        f"- F1 por clase: ansiedad={hy_row['f1_ansiedad_mean']:.6f}, depresion={hy_row['f1_depresion_mean']:.6f}"
    )
    md.append(
        f"- Estabilidad: seeds={hy_row['seeds']} | std_macro_f1={hy_row['macro_f1_std']:.6f}"
    )
    md.append(
        "- Motivos a favor: mejor score multicriterio entre híbridos evaluados, configuración parsimoniosa y menor exposición a señales metodológicamente problemáticas."
    )
    md.append("")
    md.append("## Comparación con baseline textual")
    md.append(
        f"- Mejor baseline textual en dev por macro_f1: `{best_textual_name}` (macro_f1={best_textual_macro:.6f})."
    )
    md.append(
        f"- Brecha del híbrido final respecto al mejor textual: {hy_row['macro_f1_mean'] - best_textual_macro:.6f} (macro_f1)."
    )
    md.append(
        "- Interpretación: el híbrido final no se presenta como ganador absoluto en métrica pura; se selecciona por equilibrio entre desempeño, trazabilidad clínica y control de riesgos metodológicos."
    )
    md.append("")
    md.append("## Evidencia de selección de backbone contextual")
    if selection_04c.get("valido"):
        md.append(
            f"- Selección 04c válida: `{selected_transformer_04c}` (fuente: `{selection_04c.get('fuente')}`; path: `{selection_04c.get('path')}`)."
        )
    else:
        md.append("- No se detectó artefacto válido de selección 04c; se aplicó fallback por tabla consolidada.")

    if backbone_cmp.get("valido"):
        md.append(
            f"- Comparación controlada de backbones válida: `{backbone_cmp.get('best_backbone')}` "
            f"(modelo: `{backbone_cmp.get('best_backbone_modelo')}`, delta vs BETO: `{backbone_cmp.get('delta_vs_beto')}`)."
        )
    else:
        md.append("- No se detectó comparación controlada de backbones válida para consumo automático.")

    md.append(
        f"- Transformer usado en shortlist: `{selected_transformer_final}` (criterio: `{selected_transformer_source}`)."
    )
    md.append("")
    md.append("## Modelos que pasan a test (lista corta)")
    for model in modelos_test:
        md.append(f"- `{model['modelo_variante']}`: {model['justificacion_corta']}.")
    md.append("")
    md.append("## Riesgos metodológicos remanentes")
    if backbone_cmp.get("valido") and backbone_cmp.get("best_backbone") != "beto":
        md.append(
            "- Existe evidencia en comparación controlada de que un backbone distinto de BETO puede ser competitivo; verificar consistencia en rerun final de dev antes de congelar test."
        )
    else:
        md.append("- Persiste dependencia relevante del backbone contextual en variantes híbridas competitivas.")
    md.append(
        "- El aporte de LLM no muestra mejora robusta y estable en esta fase de desarrollo."
    )
    md.append(
        "- El valor clínico del híbrido debe argumentarse por trazabilidad y diseño metodológico, no solo por métrica agregada."
    )
    md.append("")
    md.append("## Nota de freeze")
    md.append(
        "- A partir de esta decisión no se deben cambiar reglas, features ni configuración en función de resultados de test."
    )
    (out_dir / "decision_modelo_final.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    risk_md = []
    risk_md.append("# Riesgos y limitaciones del cierre en dev")
    risk_md.append("")
    risk_md.append("## Riesgos metodológicos principales")
    risk_md.append(
        "- El mejor desempeño absoluto en dev permanece en baselines textuales fuertes, por lo que la narrativa del híbrido debe evitar sobreafirmaciones."
    )
    risk_md.append(
        "- En varias variantes híbridas, activar template o medicación tiende a aumentar riesgo de atajos no clínicos."
    )
    risk_md.append(
        "- Las variantes con LLM activo no muestran ventaja consistente frente a alternativas equivalentes sin LLM."
    )
    if backbone_cmp.get("valido"):
        risk_md.append(
            f"- La comparación controlada de backbones sugiere `{backbone_cmp.get('best_backbone')}` como mejor opción local; este hallazgo debe mantenerse trazable en la decisión final."
        )
    else:
        risk_md.append(
            "- No hubo comparación controlada de backbones válida; la decisión de backbone queda condicionada a la evidencia de 04c y barrido."
        )
    risk_md.append("")
    risk_md.append("## Implicación para test")
    risk_md.append(
        "- La evaluación en test debe limitarse a la lista corta congelada en este cierre."
    )
    risk_md.append(
        "- Cualquier ajuste posterior invalidaría la condición de evaluación final limpia."
    )
    (out_dir / "riesgos_y_limitaciones_dev.md").write_text(
        "\n".join(risk_md) + "\n", encoding="utf-8"
    )

    (out_dir / "resumen_cierre.txt").write_text(
        f"out_dir={out_dir}\n"
        f"n_modelos_rankeados={len(rank_export)}\n"
        f"hibrido_final={hy_final_key}\n"
        f"mejor_textual_macro={best_textual_name}\n"
        f"split=dev\n"
        f"freeze={decision['freeze_lexico']['freeze_id']}\n",
        encoding="utf-8",
    )

    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
