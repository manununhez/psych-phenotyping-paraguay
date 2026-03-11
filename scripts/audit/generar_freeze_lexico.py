#!/usr/bin/env python3
"""
Genera un freeze versionado de la capa lexica y de reglas clinicas.

Salida:
  data/outputs/freeze_lexico_<timestamp>/
    - freeze_lexico_resumen.md
    - freeze_lexico_resumen.json
    - freeze_lexico_tabla.csv
    - checksums_sha256.csv
    - freeze_lexico_diff_resumen.csv
    - freeze_lexico_diff_terminos.csv
    - snapshot/

Uso basico:
  python scripts/audit/generar_freeze_lexico.py

Opcional:
  python scripts/audit/generar_freeze_lexico.py --freeze-id freeze_lexico_20260311_101500
  python scripts/audit/generar_freeze_lexico.py --comparar-con data/outputs/freeze_lexico_20260310_231534
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Recurso:
    nombre: str
    tipo: str
    ruta_relativa: str
    snapshot: bool
    observaciones: str


def ahora_ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def sha256_archivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def iter_archivos(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
    elif path.is_dir():
        for p in sorted(path.rglob("*")):
            if p.is_file():
                yield p


def hash_agregado(repo_root: Path, files: list[Path]) -> str:
    lineas = []
    for p in files:
        rel = p.relative_to(repo_root).as_posix()
        lineas.append(f"{rel},{sha256_archivo(p)}")
    payload = "\n".join(sorted(lineas)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git_meta(repo_root: Path) -> dict:
    meta = {
        "git_commit": "",
        "git_commit_short": "",
        "git_branch": "",
        "git_dirty": None,
    }
    try:
        meta["git_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, text=True
        ).strip()
        meta["git_commit_short"] = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, text=True
        ).strip()
        meta["git_branch"] = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_root, text=True
        ).strip()
        status = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo_root, text=True)
        meta["git_dirty"] = bool(status.strip())
    except Exception:
        pass
    return meta


def detectar_freeze_previo(output_root: Path, freeze_actual: Path) -> Path | None:
    candidatos = sorted(output_root.glob("freeze_lexico_*"))
    candidatos = [p for p in candidatos if p.is_dir() and p.resolve() != freeze_actual.resolve()]
    if not candidatos:
        return None
    return candidatos[-1]


def extraer_literales_json(path_json: Path) -> set[str]:
    literales: set[str] = set()

    try:
        data = json.loads(path_json.read_text(encoding="utf-8"))
    except Exception:
        return literales

    def rec(obj):
        if isinstance(obj, dict):
            literal = obj.get("literal")
            if isinstance(literal, str):
                lit = literal.strip()
                if lit:
                    literales.add(lit)
            for v in obj.values():
                rec(v)
        elif isinstance(obj, list):
            for x in obj:
                rec(x)

    rec(data)
    return literales


def cargar_literales_layer(layer_dir: Path) -> dict[tuple[str, str], set[str]]:
    """
    Devuelve {(layer, archivo_rel): {literales}}.
    """
    out: dict[tuple[str, str], set[str]] = {}
    if not layer_dir.exists():
        return out

    layer = layer_dir.name
    for p in sorted(layer_dir.rglob("*.json")):
        rel = p.relative_to(layer_dir).as_posix()
        lits = {x.casefold() for x in extraer_literales_json(p)}
        out[(layer, rel)] = lits
    return out


def diff_terminos_json(prev_snap: Path, curr_snap: Path) -> tuple[list[dict], dict]:
    base = Path("Spanish_Psych_Phenotyping_PY/escribe/patterns")
    layers = ["Concept_PY", "Concept_PY_Lexicon"]

    prev_map: dict[tuple[str, str], set[str]] = {}
    curr_map: dict[tuple[str, str], set[str]] = {}

    for layer in layers:
        prev_map.update(cargar_literales_layer(prev_snap / base / layer))
        curr_map.update(cargar_literales_layer(curr_snap / base / layer))

    filas: list[dict] = []
    archivos_modificados = 0

    claves = sorted(set(prev_map) | set(curr_map))
    for key in claves:
        prev_lits = prev_map.get(key, set())
        curr_lits = curr_map.get(key, set())

        agregados = sorted(curr_lits - prev_lits)
        eliminados = sorted(prev_lits - curr_lits)

        if agregados or eliminados:
            archivos_modificados += 1

        for t in agregados:
            filas.append(
                {
                    "origen": "json_rules",
                    "tipo_cambio": "termino_agregado",
                    "layer": key[0],
                    "archivo": key[1],
                    "termino": t,
                }
            )
        for t in eliminados:
            filas.append(
                {
                    "origen": "json_rules",
                    "tipo_cambio": "termino_eliminado",
                    "layer": key[0],
                    "archivo": key[1],
                    "termino": t,
                }
            )

    resumen = {
        "archivos_json_con_cambios_de_terminos": archivos_modificados,
        "terminos_agregados_json": sum(1 for r in filas if r["tipo_cambio"] == "termino_agregado"),
        "terminos_eliminados_json": sum(1 for r in filas if r["tipo_cambio"] == "termino_eliminado"),
    }
    return filas, resumen


def cargar_manifest(path_csv: Path) -> set[tuple[str, str, str, str, str]]:
    out: set[tuple[str, str, str, str, str]] = set()
    if not path_csv.exists():
        return out
    with path_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out.add(
                (
                    (row.get("term_original") or "").strip().casefold(),
                    (row.get("variant") or "").strip().casefold(),
                    (row.get("fenotipo_canonico") or "").strip().casefold(),
                    (row.get("categoria_core") or "").strip().casefold(),
                    (row.get("carpeta") or "").strip().casefold(),
                )
            )
    return out


def diff_manifest(prev_snap: Path, curr_snap: Path) -> tuple[list[dict], dict]:
    rel_manifest = Path(
        "Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY_Lexicon/lexicon_manifest.csv"
    )
    prev_m = cargar_manifest(prev_snap / rel_manifest)
    curr_m = cargar_manifest(curr_snap / rel_manifest)

    filas: list[dict] = []
    for item in sorted(curr_m - prev_m):
        filas.append(
            {
                "origen": "manifest",
                "tipo_cambio": "termino_agregado",
                "layer": "Concept_PY_Lexicon",
                "archivo": "lexicon_manifest.csv",
                "termino": item[1],
                "term_original": item[0],
                "fenotipo_canonico": item[2],
                "categoria_core": item[3],
                "carpeta": item[4],
            }
        )
    for item in sorted(prev_m - curr_m):
        filas.append(
            {
                "origen": "manifest",
                "tipo_cambio": "termino_eliminado",
                "layer": "Concept_PY_Lexicon",
                "archivo": "lexicon_manifest.csv",
                "termino": item[1],
                "term_original": item[0],
                "fenotipo_canonico": item[2],
                "categoria_core": item[3],
                "carpeta": item[4],
            }
        )

    resumen = {
        "terminos_agregados_manifest": sum(1 for r in filas if r["tipo_cambio"] == "termino_agregado"),
        "terminos_eliminados_manifest": sum(1 for r in filas if r["tipo_cambio"] == "termino_eliminado"),
    }
    return filas, resumen


def escribir_csv(path: Path, filas: list[dict], columnas: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas)
        w.writeheader()
        if filas:
            w.writerows(filas)


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera freeze lexico de Core/PY con trazabilidad completa.")
    parser.add_argument("--repo-root", default=".", help="Ruta del repositorio")
    parser.add_argument("--output-root", default="data/outputs", help="Directorio de salida")
    parser.add_argument("--freeze-id", default="", help="ID fijo de freeze. Si vacio: freeze_lexico_<timestamp>")
    parser.add_argument("--comparar-con", default="", help="Ruta de freeze previo para diff. Si vacio: autodetecta")
    parser.add_argument(
        "--ips-excel",
        default="data/IPS_validacion.xlsx",
        help="Ruta del Excel de validacion IPS",
    )
    parser.add_argument(
        "--incluir-ips-excel",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Incluir snapshot del Excel IPS si existe",
    )
    parser.add_argument(
        "--snapshot-notebooks",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Si se activa, copia notebooks de referencia en snapshot",
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Imprime detalles adicionales"
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_root = (repo_root / args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    freeze_id = args.freeze_id.strip() or f"freeze_lexico_{ahora_ts()}"
    freeze_dir = output_root / freeze_id
    snapshot_dir = freeze_dir / "snapshot"
    freeze_dir.mkdir(parents=True, exist_ok=True)
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    meta_git = git_meta(repo_root)
    git_short = meta_git.get("git_commit_short") or "sin_git"

    recursos: list[Recurso] = [
        Recurso(
            nombre="Concept_CO",
            tipo="reglas_lexico_baseline_historico",
            ruta_relativa="Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_CO",
            snapshot=True,
            observaciones="Baseline historico de reglas, congelado para trazabilidad.",
        ),
        Recurso(
            nombre="Concept_PY_Core",
            tipo="reglas_lexico_core",
            ruta_relativa="Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY",
            snapshot=True,
            observaciones="Nucleo clinico depurado validado para el pipeline final.",
        ),
        Recurso(
            nombre="Concept_PY_Lexicon",
            tipo="reglas_lexico_adaptacion_regional",
            ruta_relativa="Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY_Lexicon",
            snapshot=True,
            observaciones="Capa regional paraguaya congelada para evaluacion final.",
        ),
        Recurso(
            nombre="lexicon_manifest",
            tipo="manifiesto_lexico",
            ruta_relativa="Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY_Lexicon/lexicon_manifest.csv",
            snapshot=True,
            observaciones="Manifiesto de variantes y mapeo canonico de PY_Lexicon.",
        ),
        Recurso(
            nombre="ConText_ES",
            tipo="reglas_contexto",
            ruta_relativa="Spanish_Psych_Phenotyping_PY/escribe/patterns/ConText_ES.json",
            snapshot=True,
            observaciones="Reglas de contexto clinico para extraccion.",
        ),
        Recurso(
            nombre="RuSH_ES",
            tipo="segmentacion",
            ruta_relativa="Spanish_Psych_Phenotyping_PY/escribe/patterns/RuSH_ES.tsv",
            snapshot=True,
            observaciones="Reglas de segmentacion de texto clinico.",
        ),
        Recurso(
            nombre="core_config",
            tipo="configuracion_capa_core",
            ruta_relativa="Spanish_Psych_Phenotyping_PY/configs/core_config.yml",
            snapshot=True,
            observaciones="Configuracion activa de carga de Concept layers.",
        ),
        Recurso(
            nombre="script_audit_core",
            tipo="script_auditoria",
            ruta_relativa="scripts/audit/audit_core.py",
            snapshot=True,
            observaciones="Auditoria de brecha entre CO/Core/Lexicon.",
        ),
        Recurso(
            nombre="script_freeze_core_desde_excel",
            tipo="script_transformacion_reglas",
            ruta_relativa="scripts/audit/freeze_core_from_excel.py",
            snapshot=True,
            observaciones="Consolidacion de reglas desde Excel IPS (no ejecutado automaticamente).",
        ),
        Recurso(
            nombre="script_diff_medicacion_excel_repo",
            tipo="script_auditoria_medicacion",
            ruta_relativa="scripts/audit/diff_meds_excel_repo.py",
            snapshot=True,
            observaciones="Comparacion de medicacion entre planilla y repo.",
        ),
        Recurso(
            nombre="script_llm_extraccion",
            tipo="script_soporte_llm",
            ruta_relativa="scripts/llm/run_gemini_constrained.py",
            snapshot=True,
            observaciones="Soporte LLM para normalizacion semantica y auditoria lexico-semantica.",
        ),
        Recurso(
            nombre="notebook_brecha_lexica",
            tipo="notebook_metodologico",
            ruta_relativa="notebooks/analysis/05_brecha_lexica_co_core_py.ipynb",
            snapshot=bool(args.snapshot_notebooks),
            observaciones="Referencia metodologica del cierre lexico.",
        ),
        Recurso(
            nombre="notebook_denoising_reglas",
            tipo="notebook_pipeline",
            ruta_relativa="notebooks/pipeline/03_denoising_reglas_core.ipynb",
            snapshot=bool(args.snapshot_notebooks),
            observaciones="Consumidor de reglas Core + PY_Lexicon en pipeline.",
        ),
        Recurso(
            nombre="notebook_features_hibridas",
            tipo="notebook_pipeline",
            ruta_relativa="notebooks/pipeline/06_ingenieria_features_hibridas.ipynb",
            snapshot=bool(args.snapshot_notebooks),
            observaciones="Generador de features finales que usan reglas congeladas.",
        ),
    ]

    if args.incluir_ips_excel:
        recursos.append(
            Recurso(
                nombre="planilla_ips_validacion",
                tipo="insumo_externo_validacion",
                ruta_relativa=args.ips_excel,
                snapshot=True,
                observaciones="Planilla IPS usada como insumo de validacion lexical.",
            )
        )

    tabla_filas: list[dict] = []
    checksum_filas: list[dict] = []

    for r in recursos:
        src = (repo_root / r.ruta_relativa).resolve()
        existe = src.exists()
        estado = "OK" if existe else "FALTANTE"

        archivos = list(iter_archivos(src)) if existe else []
        fecha_mod = ""
        h_agg = ""

        if existe and r.snapshot:
            dst = snapshot_dir / r.ruta_relativa
            dst.parent.mkdir(parents=True, exist_ok=True)
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)

        if archivos:
            fecha_mod = max(
                datetime.fromtimestamp(p.stat().st_mtime) for p in archivos
            ).isoformat(timespec="seconds")
            h_agg = hash_agregado(repo_root, archivos)

            if existe and r.snapshot:
                for p in archivos:
                    rel_src = p.relative_to(repo_root).as_posix()
                    rel_snap = (snapshot_dir / rel_src).relative_to(freeze_dir).as_posix()
                    checksum_filas.append(
                        {
                            "recurso": r.nombre,
                            "ruta_fuente": rel_src,
                            "ruta_snapshot": rel_snap,
                            "sha256": sha256_archivo(p),
                            "size_bytes": p.stat().st_size,
                            "fecha_modificacion": datetime.fromtimestamp(
                                p.stat().st_mtime
                            ).isoformat(timespec="seconds"),
                        }
                    )

        tabla_filas.append(
            {
                "nombre_recurso": r.nombre,
                "tipo": r.tipo,
                "estado": estado,
                "ruta_fuente": r.ruta_relativa,
                "fecha_modificacion": fecha_mod,
                "version": f"git:{git_short}",
                "archivos_detectados": len(archivos),
                "snapshot_incluido": "si" if (existe and r.snapshot) else "no",
                "hash_agregado_sha256": h_agg,
                "observaciones": r.observaciones,
            }
        )

    tabla_csv = freeze_dir / "freeze_lexico_tabla.csv"
    escribir_csv(
        tabla_csv,
        tabla_filas,
        [
            "nombre_recurso",
            "tipo",
            "estado",
            "ruta_fuente",
            "fecha_modificacion",
            "version",
            "archivos_detectados",
            "snapshot_incluido",
            "hash_agregado_sha256",
            "observaciones",
        ],
    )

    checksums_csv = freeze_dir / "checksums_sha256.csv"
    escribir_csv(
        checksums_csv,
        checksum_filas,
        [
            "recurso",
            "ruta_fuente",
            "ruta_snapshot",
            "sha256",
            "size_bytes",
            "fecha_modificacion",
        ],
    )

    # Diff: archivos JSON + terminos
    if args.comparar_con.strip():
        freeze_previo = (repo_root / args.comparar_con).resolve()
    else:
        freeze_previo = detectar_freeze_previo(output_root, freeze_dir)

    diff_filas: list[dict] = []
    diff_terminos_filas: list[dict] = []
    diff_resumen = {
        "comparado_con": freeze_previo.name if freeze_previo else None,
        "estado": "sin_freeze_previo",
        "archivos_json_agregados": 0,
        "archivos_json_eliminados": 0,
        "archivos_json_modificados": 0,
        "archivos_json_con_cambios_de_terminos": 0,
        "terminos_agregados_json": 0,
        "terminos_eliminados_json": 0,
        "terminos_agregados_manifest": 0,
        "terminos_eliminados_manifest": 0,
    }

    if freeze_previo and freeze_previo.exists():
        prev_snap = freeze_previo / "snapshot"
        curr_snap = snapshot_dir

        base_patterns = Path("Spanish_Psych_Phenotyping_PY/escribe/patterns")
        prev_map: dict[str, str] = {}
        curr_map: dict[str, str] = {}
        for layer in ["Concept_PY", "Concept_PY_Lexicon"]:
            pdir = prev_snap / base_patterns / layer
            cdir = curr_snap / base_patterns / layer
            if pdir.exists():
                for p in pdir.rglob("*.json"):
                    rel = p.relative_to(prev_snap).as_posix()
                    prev_map[rel] = sha256_archivo(p)
            if cdir.exists():
                for p in cdir.rglob("*.json"):
                    rel = p.relative_to(curr_snap).as_posix()
                    curr_map[rel] = sha256_archivo(p)

        for rel in sorted(set(prev_map) | set(curr_map)):
            if rel not in prev_map:
                diff_filas.append({"tipo_cambio": "agregado", "archivo": rel})
            elif rel not in curr_map:
                diff_filas.append({"tipo_cambio": "eliminado", "archivo": rel})
            elif prev_map[rel] != curr_map[rel]:
                diff_filas.append({"tipo_cambio": "modificado", "archivo": rel})

        term_json_filas, term_json_resumen = diff_terminos_json(prev_snap, curr_snap)
        manifest_filas, manifest_resumen = diff_manifest(prev_snap, curr_snap)
        diff_terminos_filas = term_json_filas + manifest_filas

        diff_resumen["estado"] = "comparado"
        diff_resumen["archivos_json_agregados"] = sum(
            1 for r in diff_filas if r["tipo_cambio"] == "agregado"
        )
        diff_resumen["archivos_json_eliminados"] = sum(
            1 for r in diff_filas if r["tipo_cambio"] == "eliminado"
        )
        diff_resumen["archivos_json_modificados"] = sum(
            1 for r in diff_filas if r["tipo_cambio"] == "modificado"
        )
        diff_resumen.update(term_json_resumen)
        diff_resumen.update(manifest_resumen)

    diff_csv = freeze_dir / "freeze_lexico_diff_resumen.csv"
    escribir_csv(diff_csv, diff_filas, ["tipo_cambio", "archivo"])

    diff_terminos_csv = freeze_dir / "freeze_lexico_diff_terminos.csv"
    escribir_csv(
        diff_terminos_csv,
        diff_terminos_filas,
        [
            "origen",
            "tipo_cambio",
            "layer",
            "archivo",
            "termino",
            "term_original",
            "fenotipo_canonico",
            "categoria_core",
            "carpeta",
        ],
    )

    recursos_congelados = [
        r for r in tabla_filas if r["estado"] == "OK" and r["snapshot_incluido"] == "si"
    ]
    recursos_faltantes = [r for r in tabla_filas if r["estado"] == "FALTANTE"]

    resumen_json = {
        "freeze_id": freeze_id,
        "fecha_freeze": datetime.now().isoformat(timespec="seconds"),
        "repositorio": {
            "ruta": str(repo_root),
            **meta_git,
        },
        "versiones_congeladas": {
            "Concept_PY_Core": {
                "ruta": "Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY",
                "version": f"{freeze_id}::{git_short}",
            },
            "Concept_PY_Lexicon": {
                "ruta": "Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY_Lexicon",
                "version": f"{freeze_id}::{git_short}",
            },
            "Concept_CO": {
                "ruta": "Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_CO",
                "version": f"{freeze_id}::{git_short}",
            },
        },
        "pipeline_final_usa_archivos": [
            "Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY/**",
            "Spanish_Psych_Phenotyping_PY/escribe/patterns/Concept_PY_Lexicon/**",
            "Spanish_Psych_Phenotyping_PY/configs/core_config.yml",
            "Spanish_Psych_Phenotyping_PY/escribe/patterns/ConText_ES.json",
            "Spanish_Psych_Phenotyping_PY/escribe/patterns/RuSH_ES.tsv",
        ],
        "recursos_congelados": recursos_congelados,
        "recursos_faltantes": recursos_faltantes,
        "comparacion_version_previa": diff_resumen,
        "regla_de_cierre": "A partir de este freeze no se deben modificar reglas ni lexicos antes de la evaluacion final en test.",
        "artefactos_generados": [
            "freeze_lexico_resumen.md",
            "freeze_lexico_resumen.json",
            "freeze_lexico_tabla.csv",
            "checksums_sha256.csv",
            "freeze_lexico_diff_resumen.csv",
            "freeze_lexico_diff_terminos.csv",
            "snapshot/",
        ],
    }

    resumen_json_path = freeze_dir / "freeze_lexico_resumen.json"
    resumen_json_path.write_text(
        json.dumps(resumen_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = []
    md.append(f"# Freeze lexico y reglas clinicas: {freeze_id}")
    md.append("")
    md.append("## Estado del freeze")
    md.append(f"- Fecha: {resumen_json['fecha_freeze']}")
    md.append(
        f"- Commit: `{meta_git.get('git_commit_short', '')}` ({meta_git.get('git_branch', '')})"
    )
    md.append(f"- Repositorio con cambios sin commit: `{meta_git.get('git_dirty')}`")
    md.append("")
    md.append("## Versiones congeladas")
    md.append(
        f"- Core congelado: `Concept_PY` version `{resumen_json['versiones_congeladas']['Concept_PY_Core']['version']}`"
    )
    md.append(
        f"- PY congelado: `Concept_PY_Lexicon` version `{resumen_json['versiones_congeladas']['Concept_PY_Lexicon']['version']}`"
    )
    md.append(
        f"- Baseline historico congelado: `Concept_CO` version `{resumen_json['versiones_congeladas']['Concept_CO']['version']}`"
    )
    md.append("")
    md.append("## Alcance de archivos que alimentan el pipeline final")
    for item in resumen_json["pipeline_final_usa_archivos"]:
        md.append(f"- `{item}`")
    md.append("")
    md.append("## Regla metodologica de cierre")
    md.append(
        "- A partir de este freeze no se deben modificar reglas ni lexicos antes de la evaluacion final en test."
    )
    md.append("")
    md.append("## Cambios vs version previa")
    if diff_resumen["estado"] == "comparado":
        md.append(f"- Freeze previo comparado: `{diff_resumen['comparado_con']}`")
        md.append(f"- Archivos JSON agregados: {diff_resumen['archivos_json_agregados']}")
        md.append(f"- Archivos JSON eliminados: {diff_resumen['archivos_json_eliminados']}")
        md.append(f"- Archivos JSON modificados: {diff_resumen['archivos_json_modificados']}")
        md.append(
            f"- Terminos agregados (JSON): {diff_resumen['terminos_agregados_json']} | eliminados: {diff_resumen['terminos_eliminados_json']}"
        )
        md.append(
            f"- Terminos agregados (manifest): {diff_resumen['terminos_agregados_manifest']} | eliminados: {diff_resumen['terminos_eliminados_manifest']}"
        )
        md.append("- Detalle por archivo: `freeze_lexico_diff_resumen.csv`")
        md.append("- Detalle por termino: `freeze_lexico_diff_terminos.csv`")
    else:
        md.append(
            "- No hay freeze_lexico previo detectado para calcular diff historico de terminos."
        )
    md.append("")
    md.append("## Recursos faltantes o externos")
    if recursos_faltantes:
        for r in recursos_faltantes:
            md.append(f"- `{r['ruta_fuente']}`: {r['observaciones']}")
    else:
        md.append("- No se detectaron faltantes en los recursos declarados.")
    md.append("")
    md.append("## Artefactos generados")
    for name in resumen_json["artefactos_generados"]:
        md.append(f"- `{name}`")

    resumen_md_path = freeze_dir / "freeze_lexico_resumen.md"
    resumen_md_path.write_text("\n".join(md) + "\n", encoding="utf-8")

    (freeze_dir / "freeze_id.txt").write_text(freeze_id + "\n", encoding="utf-8")

    if args.verbose:
        print(f"[freeze] recursos_congelados={len(recursos_congelados)}")
        print(f"[freeze] recursos_faltantes={len(recursos_faltantes)}")

    print(str(freeze_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
