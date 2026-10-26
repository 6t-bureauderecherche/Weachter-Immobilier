#!/usr/bin/env python3
"""Construit des tuiles vectorielles Leaflet depuis le GeoParquet du projet.

Prérequis : les dépendances de requirements.txt et la commande tippecanoe.
    Les tuiles non compressées sont nécessaires au serveur statique de Streamlit,
qui ne transmet pas d'en-tête Content-Encoding gzip pour les fichiers .pbf.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

import geopandas as gpd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "GridXAll_Indic_FZ26_10_26.parquet"
DEFAULT_OUTPUT = ROOT / "static" / "tiles"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="GeoParquet source")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Dossier de tuiles créé")
    parser.add_argument("--min-zoom", type=int, default=8)
    parser.add_argument("--max-zoom", type=int, default=16)
    args = parser.parse_args()

    tippecanoe = shutil.which("tippecanoe")
    if tippecanoe is None:
        parser.error("tippecanoe est requis (macOS : brew install tippecanoe).")
    if not args.input.is_file():
        parser.error(f"GeoParquet introuvable : {args.input}")
    if args.output.exists():
        parser.error(
            f"Le dossier existe déjà : {args.output}. Renommez-le avant de reconstruire les tuiles."
        )
    if args.min_zoom < 0 or args.max_zoom > 22 or args.min_zoom > args.max_zoom:
        parser.error("Indiquez des niveaux de zoom valides entre 0 et 22.")

    print(f"Lecture de {args.input}…")
    frame = gpd.read_parquet(args.input)
    if "fid" not in frame.columns:
        # Compatibilité avec le GeoParquet plus ancien qui n'avait pas fid.
        frame.insert(0, "fid", frame.index + 1)
    required = {"fid", "Typo_SUM", frame.geometry.name}
    missing = required - set(frame.columns)
    if missing:
        parser.error(f"Champs manquants dans le GeoParquet : {', '.join(sorted(missing))}")

    frame = frame[["fid", "Typo_SUM", frame.geometry.name]].to_crs("EPSG:4326")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="geneva-vector-tiles-") as temporary:
        flatgeobuf = Path(temporary) / "hectares.fgb"
        frame.to_file(flatgeobuf, driver="FlatGeobuf", engine="pyogrio", index=False)
        command = [
            tippecanoe,
            "--output-to-directory",
            str(args.output),
            "--layer=hectares",
            f"--minimum-zoom={args.min_zoom}",
            f"--maximum-zoom={args.max_zoom}",
            "--drop-densest-as-needed",
            "--no-tile-compression",
            "--quiet",
            "--include=fid",
            "--include=Typo_SUM",
            str(flatgeobuf),
        ]
        print(f"Génération des tuiles z{args.min_zoom}–z{args.max_zoom}…")
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError:
            # Garde le dossier du projet propre en cas d'échec de génération.
            if args.output.exists() and not any(args.output.iterdir()):
                args.output.rmdir()
            raise

    print(f"{len(frame):,} mailles converties en tuiles dans {args.output}")
    print("Les tuiles sont non compressées pour être lues par le serveur statique Streamlit.")


if __name__ == "__main__":
    main()
