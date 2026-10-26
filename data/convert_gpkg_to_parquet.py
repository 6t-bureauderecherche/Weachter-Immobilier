#!/usr/bin/env python3
"""Convertit une couche GeoPackage en fichier GeoParquet."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd


DEFAULT_GPKG = Path(__file__).with_name("GridXAll_Indic_FZ26_10_26.gpkg")
DEFAULT_OUTPUT = DEFAULT_GPKG.with_suffix(".parquet")
DEFAULT_LAYER = "gridxindicateurs_fz26_10_26"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convertit une couche d'un GeoPackage au format GeoParquet."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_GPKG, help="GeoPackage source")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Fichier Parquet créé")
    parser.add_argument("--layer", default=DEFAULT_LAYER, help="Nom de la couche à convertir")
    args = parser.parse_args()

    if not args.input.is_file():
        parser.error(f"GeoPackage introuvable : {args.input}")

    print(f"Lecture de {args.input} (couche {args.layer})…")
    # Le fid du GeoPackage est sa clé primaire. Pyogrio l'expose comme index
    # lorsqu'on demande fid_as_index ; on le rétablit en colonne avant l'export.
    data = gpd.read_file(
        args.input,
        layer=args.layer,
        engine="pyogrio",
        fid_as_index=True,
    )
    if "fid" not in data.columns:
        data.index.name = "fid"
        data = data.reset_index()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(args.output, index=False)
    print(f"Conversion terminée : {len(data):,} entités écrites dans {args.output}")
    print(f"Projection conservée : {data.crs}")


if __name__ == "__main__":
    main()
