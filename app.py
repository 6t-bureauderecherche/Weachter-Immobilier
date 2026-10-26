"""Explorateur des indicateurs par maille du canton de Genève."""

from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq
import plotly.graph_objects as go
import streamlit as st


ROOT = Path(__file__).resolve().parent
PARQUET_PATH = ROOT / "data" / "GridXAll_Indic_FZ26_10_26.parquet"
LOGO_PATH = ROOT / "assets" / "2022-6t_identite_Logotype Horizontal - Couleur.png"
TILE_URL = "/app/static/tiles/{z}/{x}/{y}.pbf"
MAP_CENTER = (46.20, 6.14)
COMPONENT_KEY = "geneva-vector-tile-map"

FIELDS = {
    "Quali_Access_Grav": "Accessibilité Gravitaire",
    "Quali_Proxim_CD": "Proximité de courtes distances",
    "Quali_Ilot_Chal": "Ilots de chaleur",
    "Quali_Bruit": "Nuisances sonores",
    "Typo_SUM": "Performance globale",
}
SPIDER_FIELDS = (
    ("Quali_Access_Grav", "Accessibilité<br>gravitaire"),
    ("Quali_Proxim_CD", "Proximité de<br>courtes distances"),
    ("Quali_Ilot_Chal", "Ilots de<br>chaleur"),
    ("Quali_Bruit", "Nuisances<br>sonores"),
)

# Classes 0–9 progressent du rouge vers le jaune ; les classes 10–12 passent
# à une gamme bleu-vert pour rendre la rupture entre les deux groupes évidente.
PALETTE = [
    "#7f0000", "#b30000", "#d7301f", "#ef6548", "#fc8d59",
    "#fdbb84", "#fdd49e", "#fee8c8", "#fff2a6", "#f4d03f",
    "#29a3a3", "#167a8a", "#0b3c5d",
]

st.set_page_config(page_title="Indicateurs territoriaux | Genève", layout="wide")


@st.cache_resource(show_spinner="Préparation des indicateurs…")
def load_properties(path: str, mtime: float) -> dict[int, dict]:
    """Charge les attributs seulement ; les géométries sont servies en tuiles."""
    del mtime  # La date de modification fait partie de la clé du cache.
    available = set(pq.read_schema(path).names)
    missing = set(FIELDS) - available
    if missing:
        raise ValueError(f"Champs manquants dans le Parquet : {', '.join(sorted(missing))}")
    columns_to_read = (["fid"] if "fid" in available else []) + list(FIELDS)
    table = pq.read_table(path, columns=columns_to_read)
    columns = table.select(list(FIELDS)).to_pydict()
    ids = table.column("fid").to_pylist() if "fid" in available else range(1, table.num_rows + 1)
    return {
        int(fid): {field: columns[field][i] for field in FIELDS}
        for i, fid in enumerate(ids)
    }


MAP_HTML = '<div id="leaflet-map" aria-label="Carte interactive des mailles du canton de Genève"></div>'
MAP_CSS = "#leaflet-map { width: 100%; height: 720px; min-height: 500px; background: #eef1f3; }"
MAP_JS = r"""
let leafletAssetsPromise;
const instances = new WeakMap();

function loadStyle(url, styleRoot) {
  if (styleRoot.querySelector(`link[data-geneva-map="${url}"]`)) return;
  const link = document.createElement("link");
  link.rel = "stylesheet";
  link.href = url;
  link.dataset.genevaMap = url;
  styleRoot.appendChild(link);
}

function loadScript(url) {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[data-geneva-map="${url}"]`);
    if (existing) {
      if (existing.dataset.loaded === "true") return resolve();
      existing.addEventListener("load", resolve, { once: true });
      existing.addEventListener("error", reject, { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = url;
    script.dataset.genevaMap = url;
    script.onload = () => { script.dataset.loaded = "true"; resolve(); };
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function loadLeafletAssets(styleRoot) {
  if (!leafletAssetsPromise) {
    loadStyle("https://unpkg.com/leaflet@1.9.4/dist/leaflet.css", styleRoot);
    leafletAssetsPromise = loadScript("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js")
      .then(() => loadScript("https://unpkg.com/leaflet.vectorgrid@1.3.0/dist/Leaflet.VectorGrid.bundled.js"));
  }
  return leafletAssetsPromise;
}

function classColor(value, colors) {
  const index = Number(value);
  return Number.isInteger(index) && index >= 0 && index < colors.length ? colors[index] : "#9e9e9e";
}

function featureProperties(event) {
  // VectorGrid exposes the hit feature through `layer` on some Leaflet
  // versions and through `sourceTarget` on others.
  const candidates = [event.layer, event.sourceTarget, event.propagatedFrom];
  for (const candidate of candidates) {
    const properties = candidate?.properties ?? candidate?.feature?.properties;
    if (properties) return properties;
  }
  return {};
}

function highlightFeature(instance, fid) {
  if (!instance.vectorLayer || fid == null) return;
  if (instance.selectedFid != null && instance.selectedFid !== fid) {
    instance.vectorLayer.resetFeatureStyle(instance.selectedFid);
  }
  instance.vectorLayer.setFeatureStyle(fid, {
    color: "#ff00ff",
    weight: 3,
    opacity: 1,
    fillColor: "#ff00ff",
    fillOpacity: 0.35,
  });
  instance.selectedFid = fid;
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const container = parentElement.querySelector("#leaflet-map");
  if (!container) return;

  let instance = instances.get(parentElement);
  if (instance) {
    instance.select = fid => setTriggerValue("maille_clicked", fid);
    return () => {
      instance.map?.remove();
      instances.delete(parentElement);
    };
  }
  instance = { select: fid => setTriggerValue("maille_clicked", fid), selectedFid: null };
  instances.set(parentElement, instance);

  loadLeafletAssets(parentElement.getRootNode()).then(() => {
    if (!container.isConnected || instance.map) return;
    const L = window.L;
    const map = L.map(container, { preferCanvas: true, minZoom: 8, maxZoom: 18 })
      .setView(data.center, data.zoom);
    instance.map = map;
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    const vectorLayer = L.vectorGrid.protobuf(data.tileUrl, {
      // SVG paths have native pointer hit-testing. The canvas tile renderer
      // was drawing cells but frequently missing clicks on small polygons.
      rendererFactory: L.svg.tile,
      interactive: true,
      bubblingMouseEvents: true,
      getFeatureId: feature => feature.properties.fid,
      vectorTileLayerStyles: {
        hectares: properties => ({
          color: "#45515b", weight: 0.25, fill: true,
          fillColor: classColor(properties.Typo_SUM, data.palette), fillOpacity: 0.72,
        }),
      },
    }).addTo(map);
    instance.vectorLayer = vectorLayer;
    if (data.selectedFid != null) highlightFeature(instance, Number(data.selectedFid));
    vectorLayer.on("click", event => {
      const properties = featureProperties(event);
      const fid = Number(properties.fid);
      if (!Number.isSafeInteger(fid)) {
        console.warn("Clic VectorGrid reçu sans fid exploitable", event, properties);
        return;
      }
      highlightFeature(instance, fid);
      instance.select(fid);
    });
  }).catch(error => {
    container.textContent = "Impossible de charger Leaflet. Vérifiez l’accès à unpkg.com.";
    console.error(error);
  });
  return () => {
    instance.map?.remove();
    instances.delete(parentElement);
  };
}
"""
LEAFLET_MAP = st.components.v2.component(
    "geneva_vector_tile_map", html=MAP_HTML, css=MAP_CSS, js=MAP_JS
)


if not PARQUET_PATH.exists():
    st.error(
        "Fichier GeoParquet introuvable. Générez-le avec "
        "`python data/convert_gpkg_to_parquet.py`."
    )
    st.stop()

try:
    properties_by_id = load_properties(
        str(PARQUET_PATH), PARQUET_PATH.stat().st_mtime
    )
except Exception as exc:
    st.error(f"Impossible de lire les attributs du GeoParquet : {exc}")
    st.stop()

if not (ROOT / "static" / "tiles").is_dir():
    st.error(
        "Tuiles vectorielles introuvables. Générez-les avec "
        "`python data/build_vector_tiles.py`."
    )
    st.stop()

st.title("Waechter Immobilier - Aide à la décision")

@st.fragment
def render_dashboard() -> None:
    """Isole le rendu interactif : un clic ne rejoue pas toute la page."""
    left, main, right = st.columns([1.15, 5.5, 2.0], gap="medium")

    with left:
        # st.markdown("## Waechter Immobilier")
        # st.markdown("### Aide à la décision")
        # st.markdown("---")
        st.image(LOGO_PATH, width=240, alt="Logo 6t")
        st.markdown(
            "Cette carte présente les indicateurs territoriaux des mailles du canton "
            "de Genève. Cliquez sur une maille pour consulter ses résultats ; zoomez "
            "pour voir davantage de mailles."
        )
        st.markdown("---")

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
        map_result = LEAFLET_MAP(
            key="geneva-vector-tile-map",
            data={
                "tileUrl": TILE_URL,
                "center": MAP_CENTER,
                "palette": PALETTE,
                "selectedFid": st.session_state.get("selected_cell_fid"),
                # Low zoom tiles omit many features to stay small. Start where
                # the vector tiles contain enough individual cells to select.
                "zoom": 14,
            },
            on_maille_clicked_change=lambda: None,
        )

        # Trigger values are returned on ComponentResult; they are not stored
        # in the component's persistent Session State entry.
        clicked_fid = getattr(map_result, "maille_clicked", None)
        if clicked_fid is not None:
            try:
                st.session_state["selected_cell_fid"] = int(clicked_fid)
            except (TypeError, ValueError):
                st.session_state.pop("selected_cell_fid", None)

    with right:
        st.subheader("Détail de la maille")
        selected_fid = st.session_state.get("selected_cell_fid")
        if selected_fid is not None:
            try:
                selected_fid = int(selected_fid)
            except (TypeError, ValueError):
                selected_fid = None
        if selected_fid is None:
            st.info("Cliquez sur une maille pour analyser sa performance.")
        else:
            selected = properties_by_id.get(selected_fid)
            if selected is None:
                st.warning("Les informations de cette maille ne sont pas disponibles.")
            else:
                performance = selected.get("Typo_SUM")
                st.metric(
                    "Performance globale",
                    "—" if performance is None else f"Classe {performance} / 12",
                )
                st.caption(f"Identifiant de la maille : {selected_fid}")
                chart_labels = [label for _, label in SPIDER_FIELDS]
                chart_values = [selected.get(field) for field, _ in SPIDER_FIELDS]
                radar = go.Figure(
                    go.Scatterpolar(
                        r=chart_values + chart_values[:1],
                        theta=chart_labels + chart_labels[:1],
                        mode="lines+markers",
                        fill="toself",
                        fillcolor="rgba(41, 163, 163, 0.22)",
                        line={"color": "#167a8a", "width": 2},
                        marker={"size": 6, "color": "#167a8a"},
                        hovertemplate="%{theta}<br>Classe : %{r} / 3<extra></extra>",
                    )
                )
                radar.update_layout(
                    height=340,
                    margin={"l": 30, "r": 50, "t": 30, "b": 32},
                    showlegend=False,
                    dragmode=False,
                    hovermode="closest",
                    polar={
                        "radialaxis": {
                            "range": [0, 3],
                            "tickmode": "array",
                            "tickvals": [0, 1, 2, 3],
                            "tickfont": {"size": 10},
                        },
                        "angularaxis": {"tickfont": {"size": 10}},
                    },
                )
                st.plotly_chart(
                    radar,
                    width="stretch",
                    config={
                        "displayModeBar": False,
                        "scrollZoom": False,
                        "doubleClick": False,
                    },
                    alt="Distribution des quatre indicateurs, sur une échelle de 0 à 3",
                    key=f"indicators-radar-{selected_fid}",
                )

    st.caption("Source : GeoParquet · tuiles vectorielles locales · projection EPSG:2056")


render_dashboard()
