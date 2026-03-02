#!/usr/bin/env python3
from __future__ import annotations

import glob
import hashlib
import os
from typing import Any, Dict, List, Tuple

import yaml


STATUS_TO_EMOJI = {
    "supported": "✔️",  # "supported"/"yes"
    "unsupported": "❌",  # "unsupported"/"no"
    "partial": "⚠️",
    "unknown": "❔",
}


def load_yaml(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def footnote_id(note_text: str) -> str:
    h = hashlib.sha1(note_text.strip().encode("utf-8")).hexdigest()[:10]
    return f"n{h}"


def render_cell(value: Dict[str, Any] | None) -> str:
    if not value:
        return STATUS_TO_EMOJI["unknown"]

    status = value.get("status", "unknown")
    if isinstance(status, bool):
        status = "supported" if status else "unsupported"
    status = str(status).strip().lower()

    emoji = STATUS_TO_EMOJI.get(status, STATUS_TO_EMOJI["unknown"])

    notes = value.get("notes") or []
    # notes can be a string or list
    if isinstance(notes, str):
        notes = [notes]

    fns = []
    for n in notes:
        t = str(n).strip()
        if not t:
            continue
        fid = footnote_id(t)
        fns.append(f"footnote:{fid}[{t}]")

    return emoji + ("" if not fns else "".join(fns))


def main() -> None:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    criteria_path = os.path.join(repo_root, "criteria.yml")
    services_dir = os.path.join(repo_root, "services")
    out_path = os.path.join(repo_root, "README.adoc")
    notice_path = os.path.join(repo_root, "NOTICE")

    criteria_doc = load_yaml(criteria_path)
    sections = criteria_doc.get("sections") or []
    if not sections:
        raise SystemExit("criteria.yml: missing 'sections'")

    all_service_paths = glob.glob(os.path.join(services_dir, "*.yml"))
    service_paths = sorted(
        sp for sp in all_service_paths if not os.path.basename(sp).startswith("_")
    )
    if not service_paths:
        raise SystemExit("No service YAML files found in services/")

    services: List[Dict[str, Any]] = []
    for sp in service_paths:
        svc = load_yaml(sp) or {}
        if "id" not in svc or "name" not in svc:
            raise SystemExit(f"{sp}: must contain 'id' and 'name'")
        svc_id = str(svc.get("id", "")).strip().lower()
        svc_name = str(svc.get("name", "")).strip().lower()
        if svc_id == "example" or svc_name == "example":
            continue
        svc["__path"] = sp
        services.append(svc)

    lines: List[str] = []
    lines.append(
        """
ifdef::env-github[]
:tip-caption: :bulb:
:note-caption: :information_source:
:important-caption: :heavy_exclamation_mark:
:caution-caption: :fire:
:warning-caption: :warning:
endif::[]
"""
    )
    lines.append("= Discord Alternatives Comparison")
    lines.append("")
    if os.path.isfile(notice_path):
        with open(notice_path, "r", encoding="utf-8") as nf:
            notice_text = nf.read().rstrip()
        if notice_text:
            lines.append("[IMPORTANT]")
            lines.append("====")
            lines.append(notice_text)
            lines.append("====")
            lines.append("")
    lines.append("[NOTE]")
    lines.append("====")
    lines.append("✔️ supported · ❌ not supported · ⚠️ partial/conditional · ❔ unclear")
    lines.append("====")
    lines.append("")

    for sec in sections:
        sec_title = sec.get("title", "").strip()
        sec_id = sec.get("id", "").strip()
        crit_list = sec.get("criteria") or []
        if not sec_title or not sec_id or not crit_list:
            continue

        lines.append(f"== {sec_title}")
        lines.append("")
        cols = 1 + len(services)
        lines.append(f'[cols="{cols}*", options="header"]')
        lines.append("|===")

        header_cells = ["Criteria"] + [s["name"] for s in services]
        lines.append("| " + " | ".join(header_cells))

        for c in crit_list:
            cid = str(c.get("id", "")).strip()
            label = str(c.get("label", cid)).strip()
            if not cid:
                continue

            row = [label]
            for s in services:
                s_criteria = s.get("criteria") or {}
                cell_val = s_criteria.get(cid)
                row.append(render_cell(cell_val))
            lines.append("| " + " | ".join(row))

        lines.append("|===")
        lines.append("")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")


if __name__ == "__main__":
    main()
