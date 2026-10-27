#!/usr/bin/env python3
"""Construit les GeoJSON simplifiés et compressés servis à la carte Leaflet."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path

import geopandas as gpd
import shapely


ROOT = Path(__file__).resolve().parents[1]
LAYERS = {
    "TOT": ROOT / "data" / "Parcelles_classées_TOT.parquet",
    "PRIVE": ROOT / "data" / "Parcelles_classées_PRIVE.parquet",
}
OUTPUT_DIR = ROOT / "static"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    args = parser.parse_args()
    del args

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, source in LAYERS.items():
        if not source.is_file():
            parser.error(f"GeoParquet introuvable : {source}")
        print(f"Préparation de la couche {name} depuis {source.name}…")
        frame = gpd.read_parquet(source, columns=["fid", "Typo_SUM_majority", "geometry"])
        frame.geometry = shapely.force_2d(frame.geometry)
        frame.geometry = frame.geometry.simplify(0.25, preserve_topology=True)
        frame = frame.to_crs("EPSG:4326")
        frame["fid"] = frame["fid"].astype("int64")
        geojson = frame.to_json(drop_id=True).encode("utf-8")
        output = OUTPUT_DIR / f"parcels_{name}.geojson.gz"
        compressed = gzip.compress(geojson, mtime=0)
        output.write_bytes(compressed)
        print(
            f"{len(frame):,} parcelles écrites dans {output} "
            f"({len(compressed) / 1_000_000:.1f} MB compressés)"
        )


if __name__ == "__main__":
    main()
