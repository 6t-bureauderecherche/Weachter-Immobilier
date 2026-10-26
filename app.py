"""Explorateur des indicateurs par maille du canton de Genève."""

from __future__ import annotations

import json
import re
from pathlib import Path

import folium
import geopandas as gpd
import streamlit as st
from streamlit_folium import st_folium


ROOT = Path(__file__).resolve().parent
GPKG_PATH = ROOT / "data" / "GridXAll_Indic_FZ26_10_26.gpkg"
LAYER = "gridxindicateurs_fz26_10_26"

FIELDS = {
    "Quali_Access_Grav": "Accessibilité Gravitaire",
    "Quali_Proxim_CD": "Proximité de courtes distances",
    "Quali_Ilot_Chal": "Ilots de chaleur",
    "Quali_Bruit": "Nuisances sonores",
    "Typo_SUM": "Performance globale",
}

# Palette discrète et lisible pour les classes de performance globale (0 à 12).
PALETTE = [
    "#8c2d04", "#b74608", "#d76513", "#e98628", "#f5aa45",
    "#f6c96b", "#e9d977", "#c6d96b", "#9dcc6c", "#70ba72",
    "#48a77c", "#328b80", "#216b78",
]

st.set_page_config(page_title="Indicateurs territoriaux | Genève", layout="wide")


@st.cache_resource(show_spinner="Préparation des géométries pour la carte…")
def load_geojson(path: str, mtime: float) -> tuple[dict, tuple[float, float], dict[int, dict]]:
    """Lit et reprojette une seule fois les géométries (EPSG:2056 vers WGS84)."""
    del mtime  # La date de modification fait partie de la clé du cache.
    frame = gpd.read_file(path, layer=LAYER, engine="pyogrio")
    frame = frame.to_crs("EPSG:4326")
    frame = frame[["fid", *FIELDS.keys(), "geometry"]]
    frame["fid"] = frame["fid"].astype(int)
    bounds = frame.total_bounds
    center = ((bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2)
    geojson = json.loads(frame.to_json(drop_id=True))
    by_id = {int(feature["properties"]["fid"]): feature["properties"] for feature in geojson["features"]}
    return geojson, center, by_id


def feature_style(feature: dict) -> dict:
    value = feature.get("properties", {}).get("Typo_SUM")
    try:
        color = PALETTE[max(0, min(12, int(value)))]
    except (TypeError, ValueError):
        color = "#9e9e9e"
    return {"color": "#45515b", "weight": 0.15, "fillColor": color, "fillOpacity": 0.68}


def selected_fid_from_popup(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"(?:fid|id)[^0-9]{0,24}(\d+)", value, re.IGNORECASE)
    return int(match.group(1)) if match else None


if not GPKG_PATH.exists():
    st.error(f"GeoPackage introuvable : `{GPKG_PATH}`")
    st.stop()

try:
    geojson, map_center, properties_by_id = load_geojson(
        str(GPKG_PATH), GPKG_PATH.stat().st_mtime
    )
except Exception as exc:
    st.error(f"Impossible de lire les données géographiques : {exc}")
    st.stop()

left, main, right = st.columns([1.15, 5.5, 2.0], gap="medium")

with left:
    st.markdown("## Waechter Immobilier")
    st.markdown("### Aide à la décision")
    st.markdown("---")
    st.markdown(
        "Cette carte présente les indicateurs territoriaux des mailles du canton "
        "de Genève. Cliquez sur une maille pour consulter ses résultats."
    )
    st.markdown("---")
    st.caption("Logo\n\n*Remplacez ce bloc par votre logo (par exemple `assets/logo.png`).*")
    st.markdown("\n")
    st.markdown("**Performance globale**")
    for i in range(13):
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:2px 0">'
            f'<span style="display:inline-block;width:16px;height:12px;'
            f'background:{PALETTE[i]};border:1px solid #777"></span>'
            f'<span style="font-size:0.85rem">Classe {i}</span></div>',
            unsafe_allow_html=True,
        )

with main:
    st.subheader("Carte des indicateurs")
    m = folium.Map(
        location=map_center,
        zoom_start=11,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        name="OpenStreetMap",
        max_zoom=19,
    ).add_to(m)
    folium.GeoJson(
        geojson,
        name="Mailles et indicateurs",
        style_function=feature_style,
        smooth_factor=1.5,
        popup=folium.GeoJsonPopup(
            fields=["fid", *FIELDS.keys()],
            aliases=["Identifiant", *FIELDS.values()],
            labels=True,
            localize=True,
            max_width=320,
        ),
    ).add_to(m)
    folium.LayerControl(collapsed=True).add_to(m)
    map_event = st_folium(
        m,
        key="geneva-indicators-map",
        height=720,
        use_container_width=True,
        returned_objects=["last_object_clicked_popup"],
    )

with right:
    st.subheader("Détail de la maille")
    selected_fid = selected_fid_from_popup(
        (map_event or {}).get("last_object_clicked_popup")
    )
    if selected_fid is None:
        st.info("Cliquez sur une maille de la carte pour afficher ses indicateurs.")
    else:
        selected = properties_by_id.get(selected_fid)
        if selected is None:
            st.warning("Les informations de cette maille ne sont pas disponibles.")
        else:
            st.caption(f"Identifiant de la maille : {selected_fid}")
            for field, label in FIELDS.items():
                value = selected.get(field)
                st.metric(label, "—" if value is None else str(value))

st.caption("Source : GridXAll_Indic_FZ26_10_26.gpkg · projection d’origine EPSG:2056")
