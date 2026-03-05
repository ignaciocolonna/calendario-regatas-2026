import os
import re
import subprocess
from pathlib import Path

import pandas as pd
import requests
import pdfplumber

PDF_URL = "https://www.remoargentina.org/download/CalendarioRegatas2026v2%28d%29.pdf"

REPO_ROOT = Path(__file__).resolve().parent
OUTDIR = REPO_ROOT / "docs"        # <- GitHub Pages puede apuntar a /docs
PDF_PATH = OUTDIR / "CalendarioRegatas2026v2(d).pdf"
CSV_PATH = OUTDIR / "calendario_2026.csv"
HTML_PATH = OUTDIR / "index.html"

COLUMNS = ["Mes", "Fecha", "Regata", "Sede", "País/Pcia.", "Organiza", "Fiscaliza", "Observaciones"]


def run(cmd, cwd=None):
    print(">", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)


def download_pdf(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)


def parse_table_from_pdf(pdf_path: Path) -> pd.DataFrame:
    with pdfplumber.open(pdf_path) as pdf:
        lines = (pdf.pages[0].extract_text() or "").splitlines()

    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("Mes") and "Fecha" in line and "Regata" in line:
            header_idx = i
            break

    if header_idx is None:
        raise RuntimeError("No se encontró el encabezado de la tabla en el PDF.")

    eventos = []
    for line in lines[header_idx + 1:]:
        line = line.strip()
        if not line:
            continue
        eventos.append(line)

    return pd.DataFrame({"Evento": eventos})

def build_html(df: pd.DataFrame) -> str:
    table_html = df.to_html(index=False, escape=True, classes="display", table_id="cal")
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Calendario de Regatas 2026</title>
  <link rel="stylesheet" href="https://cdn.datatables.net/2.0.8/css/dataTables.dataTables.min.css">
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; }}
    h1 {{ margin: 0 0 8px 0; }}
    .sub {{ color: #555; margin: 0 0 18px 0; }}
    table.dataTable {{ width: 100% !important; }}
  </style>
</head>
<body>
  <h1>Calendario de Regatas 2026</h1>
  <p class="sub">Buscá por sede, mes, regata, etc.</p>

  {table_html}

  <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
  <script src="https://cdn.datatables.net/2.0.8/js/dataTables.min.js"></script>
  <script>
    new DataTable('#cal', {{
      pageLength: 50,
      order: [[0,'asc'], [1,'asc']]
    }});
  </script>
</body>
</html>
"""


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print("1) Descargando PDF…")
    download_pdf(PDF_URL, PDF_PATH)

    print("2) Extrayendo tabla…")
    df = parse_table_from_pdf(PDF_PATH)

    print("3) Escribiendo docs/index.html y docs/calendario_2026.csv…")
    df.to_csv(CSV_PATH, index=False, encoding="utf-8")
    HTML_PATH.write_text(build_html(df), encoding="utf-8")

    # 4) commit + push
    print("4) Commit + push…")
    run(["git", "add", "docs"])
    # si no hay cambios, git commit devuelve error; lo evitamos chequeando status
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=REPO_ROOT).decode("utf-8").strip()
    if not status:
        print("No hay cambios para commitear.")
        return

    run(["git", "commit", "-m", "Actualizar calendario (auto)"])
    run(["git", "push"])


if __name__ == "__main__":
    main()
