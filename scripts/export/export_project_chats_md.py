#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


TARGET_PROJECTS = {"TFM", "TFM-2", "Ajustes-TFM"}

PROJECT_KEY_HINTS = {
    "project", "project_name", "project_title", "workspace", "workspace_name",
    "folder", "folder_name", "collection", "collection_name"
}

FILE_REGEX = re.compile(
    r"\b([A-Za-z0-9_\- .()\[\]]+\.(?:pdf|docx|doc|xlsx|xls|csv|json|ipynb|txt|md|tex|bib|png|jpg|jpeg|webp|pptx|ppt))\b",
    re.IGNORECASE
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta a Markdown solo los chats pertenecientes a proyectos específicos."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        help="Uno o varios archivos JSON exportados por ChatGPT"
    )
    parser.add_argument(
        "-o", "--output",
        default="project_chats_md",
        help="Directorio de salida"
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        default=["TFM", "TFM-2", "Ajustes-TFM"],
        help="Lista de nombres de proyecto a exportar"
    )
    parser.add_argument(
        "--start",
        default=None,
        help="Fecha mínima inclusive YYYY-MM-DD (opcional)"
    )
    parser.add_argument(
        "--end",
        default=None,
        help="Fecha máxima inclusive YYYY-MM-DD (opcional)"
    )
    parser.add_argument(
        "--collapse-user-long-text",
        action="store_true",
        default=True,
        help="Colapsa bloques largos del usuario (default: activado)"
    )
    return parser.parse_args()


def normalize_text(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def slugify(text: str, max_words: int = 12, max_len: int = 90) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^\w\s-]", " ", text)
    words = [w for w in text.split() if w]
    words = words[:max_words]
    slug = "-".join(words)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug[:max_len] or "sin-titulo"


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            return None
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            pass

        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except Exception:
            return None

    return None


def dt_to_iso(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dt_to_filename(dt: Optional[datetime]) -> str:
    if not dt:
        return "unknown-timestamp"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def load_json_file(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]

    if isinstance(data, dict):
        for key in ("conversations", "items", "data"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]

        if "mapping" in data or "messages" in data:
            return [data]

    return []


def stringify_content(content: Any) -> str:
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(stringify_content(x) for x in content if stringify_content(x).strip())

    if isinstance(content, dict):
        if "parts" in content and isinstance(content["parts"], list):
            return "\n".join(
                p if isinstance(p, str) else stringify_content(p)
                for p in content["parts"]
            ).strip()

        if "text" in content:
            return stringify_content(content["text"])

        if "result" in content:
            return stringify_content(content["result"])

        if "value" in content:
            return stringify_content(content["value"])

        pieces = []
        for _, v in content.items():
            sv = stringify_content(v)
            if sv.strip():
                pieces.append(sv)
        return "\n".join(pieces).strip()

    return str(content)


def extract_role(message: Dict[str, Any]) -> str:
    author = message.get("author")
    if isinstance(author, dict):
        role = author.get("role")
        if role:
            return str(role).lower()
    if isinstance(author, str):
        return author.lower()
    return "unknown"


def extract_attachments(message: Dict[str, Any], text: str) -> List[str]:
    found = set()

    metadata = message.get("metadata", {})
    if isinstance(metadata, dict):
        for key in ("attachments", "files"):
            items = metadata.get(key, [])
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict):
                        name = item.get("name") or item.get("filename") or item.get("title")
                        if name:
                            found.add(str(name).strip())

    for match in FILE_REGEX.findall(text or ""):
        found.add(match.strip())

    return sorted(x for x in found if x)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_turn_text(message: Dict[str, Any]) -> str:
    return normalize_whitespace(stringify_content(message.get("content")))


def get_turns_from_mapping(conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
    mapping = conversation.get("mapping", {})
    if not isinstance(mapping, dict) or not mapping:
        return []

    nodes: Dict[str, Dict[str, Any]] = {
        node_id: node for node_id, node in mapping.items()
        if isinstance(node, dict)
    }

    leaves: List[Tuple[Optional[datetime], str]] = []
    for node_id, node in nodes.items():
        children = node.get("children", [])
        message = node.get("message")
        if not children and message:
            leaves.append((parse_timestamp(message.get("create_time")), node_id))

    if not leaves:
        for node_id, node in nodes.items():
            message = node.get("message")
            if message:
                leaves.append((parse_timestamp(message.get("create_time")), node_id))

    if not leaves:
        return []

    leaves.sort(key=lambda x: (x[0] is not None, x[0] or datetime(1970, 1, 1, tzinfo=timezone.utc)))
    current_id = leaves[-1][1]

    chain_ids = []
    seen = set()

    while current_id and current_id not in seen:
        seen.add(current_id)
        chain_ids.append(current_id)
        current_id = nodes.get(current_id, {}).get("parent")

    chain_ids.reverse()

    turns = []
    for node_id in chain_ids:
        message = nodes.get(node_id, {}).get("message")
        if not isinstance(message, dict):
            continue

        role = extract_role(message)
        if role in {"tool", "developer", "system"}:
            continue

        text = extract_turn_text(message)
        attachments = extract_attachments(message, text)
        created = parse_timestamp(message.get("create_time"))

        if not text and not attachments:
            continue

        turns.append({
            "role": role,
            "text": text,
            "attachments": attachments,
            "create_time": created
        })

    return turns


def get_turns_from_flat(conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = []
    for key in ("messages", "conversation", "items"):
        value = conversation.get(key)
        if isinstance(value, list):
            candidates = value
            break

    turns = []
    for item in candidates:
        if not isinstance(item, dict):
            continue

        message = item.get("message") if isinstance(item.get("message"), dict) else item
        role = extract_role(message)
        if role in {"tool", "developer", "system"}:
            continue

        text = extract_turn_text(message)
        attachments = extract_attachments(message, text)
        created = parse_timestamp(message.get("create_time") or item.get("create_time"))

        if not text and not attachments:
            continue

        turns.append({
            "role": role,
            "text": text,
            "attachments": attachments,
            "create_time": created
        })

    turns.sort(key=lambda x: x["create_time"] or datetime(1970, 1, 1, tzinfo=timezone.utc))
    return turns


def get_turns(conversation: Dict[str, Any]) -> List[Dict[str, Any]]:
    turns = get_turns_from_mapping(conversation)
    if turns:
        return turns
    return get_turns_from_flat(conversation)


def conversation_create_dt(conversation: Dict[str, Any], turns: List[Dict[str, Any]]) -> Optional[datetime]:
    direct = parse_timestamp(conversation.get("create_time"))
    if direct:
        return direct

    dts = [t["create_time"] for t in turns if t.get("create_time")]
    return min(dts) if dts else None


def conversation_update_dt(conversation: Dict[str, Any], turns: List[Dict[str, Any]]) -> Optional[datetime]:
    direct = parse_timestamp(conversation.get("update_time"))
    if direct:
        return direct

    dts = [t["create_time"] for t in turns if t.get("create_time")]
    return max(dts) if dts else None


def in_date_range(dt: Optional[datetime], start: Optional[str], end: Optional[str]) -> bool:
    if dt is None:
        return False

    d = dt.date()

    if start:
        start_d = datetime.strptime(start, "%Y-%m-%d").date()
        if d < start_d:
            return False

    if end:
        end_d = datetime.strptime(end, "%Y-%m-%d").date()
        if d > end_d:
            return False

    return True


def walk_project_candidates(obj: Any, parent_key: str = "") -> Iterable[str]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            k_norm = normalize_text(str(k))
            key_is_projectish = any(hint in k_norm for hint in PROJECT_KEY_HINTS)

            if key_is_projectish:
                if isinstance(v, str) and v.strip():
                    yield v.strip()
                elif isinstance(v, dict):
                    for inner_key in ("name", "title", "label", "slug", "id"):
                        inner_val = v.get(inner_key)
                        if isinstance(inner_val, str) and inner_val.strip():
                            yield inner_val.strip()

            yield from walk_project_candidates(v, k_norm)

    elif isinstance(obj, list):
        for item in obj:
            yield from walk_project_candidates(item, parent_key)


def detect_project(conversation: Dict[str, Any], target_projects: List[str]) -> Optional[str]:
    normalized_targets = {normalize_text(p): p for p in target_projects}
    candidates = list(walk_project_candidates(conversation))

    # Exact / normalized exact
    for cand in candidates:
        cand_norm = normalize_text(cand)
        if cand_norm in normalized_targets:
            return normalized_targets[cand_norm]

    # Containment fallback
    for cand in candidates:
        cand_norm = normalize_text(cand)
        for t_norm, original in normalized_targets.items():
            if t_norm in cand_norm or cand_norm in t_norm:
                return original

    return None


def guess_title(conversation: Dict[str, Any]) -> str:
    title = str(conversation.get("title", "")).strip()
    return title or "sin-titulo"


def classify_long_block(text: str) -> Optional[str]:
    stripped = text.strip()
    if not stripped:
        return None

    lines = stripped.splitlines()
    line_count = len(lines)
    char_count = len(stripped)

    fenced_blocks = re.findall(r"```([a-zA-Z0-9_+-]*)\n.*?```", stripped, flags=re.DOTALL)
    if fenced_blocks:
        lang = fenced_blocks[0].strip() or "sin lenguaje"
        return f"<bloque de código omitido: {lang}, {line_count} líneas>"

    latex_markers = [
        r"\documentclass", r"\begin{document}", r"\end{document}",
        r"\section{", r"\subsection{", r"\cite{", r"\ref{", r"\label{",
        r"\begin{table}", r"\begin{figure}", r"\begin{equation}",
        r"\usepackage{", r"\title{", r"\author{"
    ]
    latex_hits = sum(1 for pat in latex_markers if re.search(pat, stripped))
    if latex_hits >= 2 and (char_count > 700 or line_count > 18):
        return f"<bloque LaTeX omitido: {line_count} líneas>"

    code_like_signals = 0
    code_patterns = [
        r"^\s*def\s+\w+\(",
        r"^\s*class\s+\w+",
        r"^\s*import\s+\w+",
        r"^\s*from\s+\w+\s+import\s+",
        r"^\s*if\s+__name__\s*==\s*['\"]__main__['\"]",
        r"^\s*public\s+class\s+",
        r"^\s*private\s+",
        r"^\s*const\s+\w+",
        r"^\s*final\s+\w+",
        r"^\s*return\s+",
        r"^\s*for\s*\(",
        r"^\s*while\s*\(",
        r"^\s*SELECT\s+",
        r"^\s*INSERT\s+INTO\s+",
        r"^\s*UPDATE\s+\w+",
        r"^\s*CREATE\s+TABLE\s+"
    ]
    for line in lines[:80]:
        for pat in code_patterns:
            if re.search(pat, line, flags=re.IGNORECASE):
                code_like_signals += 1
                break

    if code_like_signals >= 5 and (char_count > 700 or line_count > 18):
        return f"<bloque de código omitido: {line_count} líneas>"

    # Texto muy largo pegado para revisión
    if char_count > 3500 or line_count > 60:
        return f"<texto largo omitido: {char_count} caracteres, {line_count} líneas>"

    return None


def collapse_large_user_message(text: str) -> str:
    original = text

    # 1) reemplazar bloques fenced individuales
    def replace_fenced(match: re.Match) -> str:
        lang = (match.group(1) or "").strip() or "sin lenguaje"
        body = match.group(2) or ""
        line_count = len(body.strip("\n").splitlines())
        if len(body) > 500 or line_count > 15:
            return f"\n<{ 'bloque de código omitido' }: {lang}, {line_count} líneas>\n"
        return match.group(0)

    text = re.sub(
        r"```([a-zA-Z0-9_+\-]*)\n(.*?)```",
        replace_fenced,
        text,
        flags=re.DOTALL
    )

    # 2) si todavía todo el mensaje es enorme, resumir completo
    placeholder = classify_long_block(text)
    if placeholder:
        preview = ""
        first_meaningful = ""
        for line in text.splitlines():
            line = line.strip()
            if line:
                first_meaningful = line[:160]
                break

        if first_meaningful and len(first_meaningful) > 12:
            preview = f"\nContexto inicial: {first_meaningful}"
        return f"{placeholder}{preview}"

    return original if text == original else text


def safe_code_fence(text: str) -> str:
    # Usamos tildes para evitar conflictos con backticks del contenido original.
    return f"~~~~text\n{text}\n~~~~"


def role_label(role: str) -> str:
    return {
        "user": "Usuario",
        "assistant": "Asistente",
        "unknown": "Desconocido"
    }.get(role, role.capitalize())


def build_markdown(
    conversation: Dict[str, Any],
    project_name: str,
    turns: List[Dict[str, Any]],
    created_at: Optional[datetime],
    updated_at: Optional[datetime]
) -> str:
    title = guess_title(conversation)
    conv_id = str(conversation.get("id", "")).strip()

    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"- **Proyecto:** {project_name}")
    lines.append(f"- **Fecha de creación:** {dt_to_iso(created_at) or 'No disponible'}")
    lines.append(f"- **Última actualización:** {dt_to_iso(updated_at) or 'No disponible'}")
    lines.append(f"- **Conversation ID:** {conv_id or 'No disponible'}")
    lines.append("")

    lines.append("---")
    lines.append("")

    for turn in turns:
        role = role_label(turn["role"])
        ts = dt_to_iso(turn.get("create_time")) or "Sin timestamp"
        text = turn.get("text", "")

        if turn["role"] == "user":
            text = collapse_large_user_message(text)

        lines.append(f"## {role} — {ts}")
        lines.append("")

        if turn.get("attachments"):
            lines.append("Adjuntos detectados:")
            for a in turn["attachments"]:
                lines.append(f"- {a}")
            lines.append("")

        if text.strip():
            lines.append(safe_code_fence(text))
        else:
            lines.append(safe_code_fence("<mensaje sin texto legible>"))
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def main() -> None:
    args = parse_args()

    target_projects = args.projects
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    total_loaded = 0
    exported = 0
    skipped_no_turns = 0
    skipped_no_project = 0
    skipped_date = 0

    for input_path_str in args.inputs:
        input_path = Path(input_path_str)
        if not input_path.exists():
            print(f"[WARN] No existe: {input_path}")
            continue

        conversations = load_json_file(input_path)
        total_loaded += len(conversations)

        for conv in conversations:
            project_name = detect_project(conv, target_projects)
            if not project_name:
                skipped_no_project += 1
                continue

            turns = get_turns(conv)
            if not turns:
                skipped_no_turns += 1
                continue

            created_at = conversation_create_dt(conv, turns)
            updated_at = conversation_update_dt(conv, turns)

            if args.start or args.end:
                if not in_date_range(created_at, args.start, args.end):
                    skipped_date += 1
                    continue

            title = guess_title(conv)
            filename = f"{dt_to_filename(created_at)}__{slugify(title)}.md"

            project_dir = output_dir / project_name
            project_dir.mkdir(parents=True, exist_ok=True)

            markdown = build_markdown(
                conversation=conv,
                project_name=project_name,
                turns=turns,
                created_at=created_at,
                updated_at=updated_at
            )

            out_file = project_dir / filename
            out_file.write_text(markdown, encoding="utf-8")
            exported += 1

    print("=" * 60)
    print(f"Conversaciones cargadas: {total_loaded}")
    print(f"Exportadas: {exported}")
    print(f"Saltadas por no pertenecer a proyectos objetivo: {skipped_no_project}")
    print(f"Saltadas por no tener turnos legibles: {skipped_no_turns}")
    print(f"Saltadas por fecha: {skipped_date}")
    print(f"Salida: {output_dir.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()