#!/usr/bin/env python3
"""Convertit une couche GeoPackage en fichier GeoParquet."""

from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd


DEFAULT_GPKG = Path(__file__).with_name("GridXAll_Indic_FZ26_10_26.gpkg")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convertit une couche d'un GeoPackage au format GeoParquet."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_GPKG, help="GeoPackage source")
    parser.add_argument("--output", type=Path, help="Fichier Parquet créé (par défaut, même nom que la source)")
    parser.add_argument(
        "--layer",
        help="Nom de la couche à convertir (détection automatique si le fichier n'en contient qu'une)",
    )
    args = parser.parse_args()
    output = args.output or args.input.with_suffix(".parquet")

    if not args.input.is_file():
        parser.error(f"GeoPackage introuvable : {args.input}")

    layer = args.layer
    if layer is None:
        layers = gpd.list_layers(args.input)
        if len(layers) != 1:
            parser.error(
                f"Le GeoPackage contient {len(layers)} couches ; précisez-en une avec --layer."
            )
        layer = layers.iloc[0]["name"]

    print(f"Lecture de {args.input} (couche {layer})…")
    # Le fid du GeoPackage est sa clé primaire. Pyogrio l'expose comme index
    # lorsqu'on demande fid_as_index ; on le rétablit en colonne avant l'export.
    data = gpd.read_file(
        args.input,
        layer=layer,
        engine="pyogrio",
        fid_as_index=True,
    )
    if "fid" not in data.columns:
        data.index.name = "fid"
        data = data.reset_index()
    output.parent.mkdir(parents=True, exist_ok=True)
    data.to_parquet(output, index=False)
    print(f"Conversion terminée : {len(data):,} entités écrites dans {output}")
    print(f"Projection conservée : {data.crs}")


if __name__ == "__main__":
    main()
