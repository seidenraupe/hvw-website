#!/usr/bin/env python
"""
Eventfrog → Programm.pdf (Agenda-Download)
==========================================

Eigener Hostpoint-Cron — hält dokumente/Programm.pdf und programm/Programm.json
aktuell (alle HVW-Org-IDs, ohne Attraktionen/Öffnungszeiten).

Hostpoint-Cron (täglich, z.B. 03:15, nach Titelseite):
    cd /home/zozuhosa/cronjobs && /usr/local/bin/python eventfrog_to_programm_pdf.py >/dev/null 2>&1
"""

from __future__ import print_function

import importlib.util
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from eventfrog_to_coucou import resolve_httpdocs_dir, resolve_org_ids  # noqa: E402

GENERATOR_BASENAME = "generate-programm-pdf.py"


def load_generator():
    path = os.path.join(SCRIPT_DIR, GENERATOR_BASENAME)
    if not os.path.isfile(path):
        return None, path
    spec = importlib.util.spec_from_file_location("hvw_generate_programm_pdf", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, path


def main():
    httpdocs_dir = resolve_httpdocs_dir()
    os.environ["HVW_HTTPDOCS_DIR"] = httpdocs_dir

    pdf_path = os.path.join(httpdocs_dir, "dokumente", "Programm.pdf")
    logo_path = os.path.join(httpdocs_dir, "images", "hvw-logo.png")
    missing_assets = []
    for path in (logo_path,):
        if not os.path.isfile(path):
            missing_assets.append(path)
    for rel in (
        "images/museen/museum-schaffen.jpg",
        "images/museen/museum-lindengut.jpg",
        "images/museen/schloss-moersburg.jpg",
    ):
        full = os.path.join(httpdocs_dir, rel)
        if not os.path.isfile(full):
            missing_assets.append(full)
    if missing_assets:
        print(
            "Fehler: Bilddateien fehlen im Webroot ({0}):\n  {1}".format(
                httpdocs_dir, "\n  ".join(missing_assets)
            )
        )
        print("Bitte zuerst Soft-Launch-Deploy ausführen (images/, dokumente/).")
        return 1

    generator, gen_path = load_generator()
    if generator is None:
        print(
            "Fehler: {0} fehlt in ~/cronjobs — Action «Deploy cronjobs to Hostpoint» ausführen.".format(
                GENERATOR_BASENAME
            )
        )
        return 1

    org_ids = ",".join(resolve_org_ids())
    print("Programm-PDF → {0} (Org-IDs: {1})".format(pdf_path, org_ids))
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    os.makedirs(os.path.join(httpdocs_dir, "programm"), exist_ok=True)

    exit_code = generator.main(
        [
            "-o",
            pdf_path,
            "--org-ids",
            org_ids,
            "--logo",
            logo_path,
        ]
    )
    if exit_code:
        return exit_code

    meta_path = os.path.join(httpdocs_dir, "programm", "Programm.json")
    if not os.path.isfile(meta_path):
        print("Warnung: Meta-Datei fehlt: {0}".format(meta_path))
        return 1
    if not os.path.isfile(pdf_path):
        print("Fehler: PDF wurde nicht geschrieben: {0}".format(pdf_path))
        return 1
    print(
        "Fertig: {0} ({1} Bytes), Meta: {2}".format(
            pdf_path, os.path.getsize(pdf_path), meta_path
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
