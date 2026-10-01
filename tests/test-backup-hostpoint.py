#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "scripts/backup-hostpoint-full.sh"
workflow = ROOT / ".github/workflows/backup-hostpoint.yml"
doc = ROOT / "docs/datensicherung-hostpoint.md"

for path in (script, workflow, doc):
    if not path.is_file():
        raise SystemExit(f"fehlt: {path}")

text = script.read_text(encoding="utf-8")
if "rsync_from" not in text or "hvwinterthur.ch" not in text:
    raise SystemExit("backup-hostpoint-full.sh unvollständig")

wf = workflow.read_text(encoding="utf-8")
if "workflow_dispatch" not in wf or "backup-hostpoint-full.sh" not in wf:
    raise SystemExit("backup-hostpoint.yml unvollständig")

print("backup-hostpoint ok")
