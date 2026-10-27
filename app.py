from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
import pyarrow.parquet as pq
import streamlit as st


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOGO_PATH = ROOT / "assets" / "2022-6t_identite_Logotype Horizontal - Couleur.png"
MAP_CENTER = (46.20, 6.14)
GEOJSON_URLS = {
    "TOT": "/app/static/parcels_TOT.geojson.gz",
    "PRIVE": "/app/static/parcels_PRIVE.geojson.gz",
}

LAYERS = {
    "TOT": DATA_DIR / "Parcelles_classées_TOT.parquet",
    "PRIVE": DATA_DIR / "Parcelles_classées_PRIVE.parquet",
}
FIELDS = {
    "Quali_Access_Grav_majority": "Accessibilité Gravitaire",
    "Quali_Proxim_CD_majority": "Proximité de courtes distances",
    "Quali_Ilot_Chal_majority": "Ilots de chaleur",
    "Quali_Bruit_majority": "Nuisances sonores",
    "Typo_SUM_majority": "Performance globale",
}
DETAIL_FIELDS = ("commune", "no_parcelle", "surface")
SPIDER_FIELDS = (
    ("Quali_Access_Grav_majority", "Accessibilité<br>gravitaire"),
    ("Quali_Proxim_CD_majority", "Proximité de<br>courtes distances"),
    ("Quali_Ilot_Chal_majority", "Ilots de<br>chaleur"),
    ("Quali_Bruit_majority", "Nuisances<br>sonores"),
)

# Les classes basses reprennent les accents corail, orange et or de 6t ; les
# classes hautes passent aux tons aqua, turquoise et bleu marine de la marque.
PALETTE = [
    "#D95664", "#F06470", "#FF717C", "#FF8061", "#FF893F",
    "#FF9433", "#F9A51C", "#F9B421", "#F8C14A", "#F5D58B",
    "#7FD3CF", "#2A9C8E", "#060D53",
]

st.set_page_config(page_title="Indicateurs territoriaux | Genève", layout="wide")


@st.cache_data(ttl="1h", max_entries=2)
def load_properties(path: str, mtime: float) -> dict[int, dict]:
    """Charge les seuls attributs nécessaires au panneau de détail."""
    del mtime
    available = set(pq.read_schema(path).names)
    columns = ["fid", *FIELDS, *DETAIL_FIELDS]
    missing = set(columns) - available
    if missing:
        raise ValueError(f"Champs manquants dans le GeoParquet : {', '.join(sorted(missing))}")
    table = pq.read_table(path, columns=columns)
    values = table.to_pydict()
    return {
        int(fid): {field: values[field][i] for field in (*FIELDS, *DETAIL_FIELDS)}
        for i, fid in enumerate(values["fid"])
    }


MAP_HTML = '<div id="leaflet-map" aria-label="Carte interactive des parcelles du canton de Genève"></div>'
MAP_CSS = "#leaflet-map { width: 100%; height: 720px; min-height: 500px; background: #EEECE1; }"
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
    leafletAssetsPromise = loadScript("https://unpkg.com/leaflet@1.9.4/dist/leaflet.js");
  }
  return leafletAssetsPromise;
}

function classColor(value, colors) {
  const index = Number(value);
  return Number.isInteger(index) && index >= 0 && index < colors.length ? colors[index] : "#EEECE1";
}

function addClassLegend(map, palette) {
  const legend = window.L.control({ position: "bottomright" });
  legend.onAdd = () => {
    const box = document.createElement("div");
    box.setAttribute("aria-label", "Légende de la performance globale");
    Object.assign(box.style, {
      background: "rgba(255, 255, 255, 0.96)",
      padding: "8px 10px",
      borderRadius: "4px",
      border: "1px solid #7FD3CF",
      boxShadow: "0 1px 5px rgba(6, 13, 83, 0.28)",
      maxHeight: "60vh",
      overflowY: "auto",
      fontSize: "12px",
      lineHeight: "17px",
    });
    const title = document.createElement("div");
    title.textContent = "Performance globale";
    title.style.fontWeight = "600";
    title.style.marginBottom = "4px";
    box.appendChild(title);

    palette.forEach((color, index) => {
      const row = document.createElement("div");
      Object.assign(row.style, { display: "flex", alignItems: "center", gap: "7px" });
      const swatch = document.createElement("span");
      Object.assign(swatch.style, {
        display: "inline-block",
        width: "16px",
        height: "12px",
        background: color,
        border: "1px solid #060D53",
        boxSizing: "border-box",
      });
      const label = document.createElement("span");
      label.textContent = `Classe ${index}`;
      row.append(swatch, label);
      box.appendChild(row);
    });
    return box;
  };
  legend.addTo(map);
}

function styleFor(feature, data) {
  const selected = Number(feature.properties.fid) === Number(data.selectedFid);
  return {
    color: selected ? "#6246D3" : "#060D53",
    weight: selected ? 2.5 : 0.5,
    opacity: 1,
    fillColor: selected ? "#6246D3" : classColor(feature.properties.Typo_SUM_majority, data.palette),
    fillOpacity: selected ? 0.42 : 0.76,
  };
}

async function installGeoJson(instance, data) {
  const layerKey = data.layerKey;
  instance.layerKey = layerKey;
  const response = await fetch(data.geojsonUrl);
  if (!response.ok) throw new Error(`GeoJSON indisponible (${response.status})`);
  const compressed = await response.arrayBuffer();
  const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream("gzip"));
  const geojson = await new Response(stream).json();
  if (instance.layerKey !== layerKey) return;
  if (instance.parcels) instance.map.removeLayer(instance.parcels);
  instance.parcels = window.L.geoJSON(geojson, {
    renderer: instance.renderer,
    style: feature => styleFor(feature, data),
    onEachFeature: (feature, layer) => layer.on("click", () => {
      const fid = Number(feature.properties.fid);
      if (!Number.isSafeInteger(fid)) return;
      instance.selectedFid = fid;
      instance.parcels.resetStyle();
      layer.setStyle(styleFor(feature, { ...data, selectedFid: fid }));
      instance.select(fid);
    }),
  }).addTo(instance.map);
  instance.selectedFid = data.selectedFid;
}

export default function (component) {
  const { data, parentElement, setTriggerValue } = component;
  const container = parentElement.querySelector("#leaflet-map");
  if (!container) return;

  let instance = instances.get(parentElement);
  if (instance) {
    instance.select = fid => setTriggerValue("parcel_clicked", fid);
    if (instance.map && instance.layerKey !== data.layerKey) {
      installGeoJson(instance, data).catch(error => console.error(error));
    }
    return () => { instance.map?.remove(); instances.delete(parentElement); };
  }
  instance = { select: fid => setTriggerValue("parcel_clicked", fid), selectedFid: null };
  instances.set(parentElement, instance);

  loadLeafletAssets(parentElement.getRootNode()).then(() => {
    if (!container.isConnected || instance.map) return;
    const L = window.L;
    const map = L.map(container, { preferCanvas: true, minZoom: 8, maxZoom: 19 })
      .setView(data.center, data.zoom);
    instance.map = map;
    instance.renderer = L.canvas({ padding: 0.5 });
    addClassLegend(map, data.palette);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);
    installGeoJson(instance, data).catch(error => {
      container.textContent = "Impossible de charger les parcelles. Vérifiez les fichiers GeoJSON dans static/.";
      console.error(error);
    });
  }).catch(error => {
    container.textContent = "Impossible de charger Leaflet. Vérifiez l’accès à unpkg.com.";
    console.error(error);
  });
  return () => { instance.map?.remove(); instances.delete(parentElement); };
}
"""
LEAFLET_MAP = st.components.v2.component(
    "geneva_parcel_map", html=MAP_HTML, css=MAP_CSS, js=MAP_JS
)


missing_parquets = [path for path in LAYERS.values() if not path.is_file()]
missing_geojson = [path for path in GEOJSON_URLS if not (ROOT / "static" / f"parcels_{path}.geojson.gz").is_file()]
if missing_parquets or missing_geojson:
    missing = [path.name for path in missing_parquets]
    missing.extend(f"parcels_{layer}.geojson.gz" for layer in missing_geojson)
    names = ", ".join(missing)
    st.error(f"Fichiers cartographiques introuvables : {names}. Consultez les commandes de préparation dans README.md.")
    st.stop()

st.title("Waechter Immobilier - Aide à la décision")

@st.fragment
def render_dashboard() -> None:
    left, main, right = st.columns([1.35, 5.2, 2.0], gap="medium")

    with left:
        st.image(LOGO_PATH, width=240, alt="Logo 6t")
        st.markdown(
            "Cette carte identifie les secteurs présentant de forts potentiels " \
            "d'attractivité pour un opération immobilière sur le Canton de Genève sur la base"
            " d'une analyse multicritère. " )
        st.markdown(
            "Une parcelle a un fort potentiel lorsqu'elle présente simultanément 4 qualités " \
            "importantes: " )
        st.markdown(
            "1)	Une excellente proximité des équipements, commerces et services du quotidien" )
        st.markdown(
            "2)	Une bonne accessibilité en transports public " )
        st.markdown(
            "3)	Une faible exposition au bruit routier de jour " )
        st.markdown(
            "4)	Une localisation en dehors des îlots de chaleur urbains" )
        st.markdown(
            "La carte exclu les parcelles appartenant au domaine public. Les parcelles les " \
            " plus attractives sont colorées en bleu."
        )
    with main:
        st.subheader("Carte des indicateurs")
        selected_layer = st.segmented_control(
            "Type de propriété", ["TOT", "PRIVE"], default="TOT", key="parcel_layer"
        )
        if selected_layer is None:
            selected_layer = "TOT"
        if st.session_state.get("_previous_parcel_layer", "TOT") != selected_layer:
            st.session_state.pop("selected_parcel_fid", None)
            st.session_state["_previous_parcel_layer"] = selected_layer

        parquet_path = LAYERS[selected_layer]
        try:
            properties_by_id = load_properties(str(parquet_path), parquet_path.stat().st_mtime)
        except Exception as exc:
            st.error(f"Impossible de préparer les données de la couche {selected_layer} : {exc}")
            return

        map_result = LEAFLET_MAP(
            key="geneva-parcel-map",
            data={
                "geojsonUrl": GEOJSON_URLS[selected_layer],
                "layerKey": selected_layer,
                "center": MAP_CENTER,
                "palette": PALETTE,
                "selectedFid": st.session_state.get("selected_parcel_fid"),
                "zoom": 14,
            },
            on_parcel_clicked_change=lambda: None,
        )
        clicked_fid = getattr(map_result, "parcel_clicked", None)
        if clicked_fid is not None:
            try:
                st.session_state["selected_parcel_fid"] = int(clicked_fid)
            except (TypeError, ValueError):
                st.session_state.pop("selected_parcel_fid", None)

    with right:
        st.subheader("Détail de la parcelle")
        selected_fid = st.session_state.get("selected_parcel_fid")
        selected = properties_by_id.get(int(selected_fid)) if selected_fid is not None else None
        if selected is None:
            st.info("Cliquez sur une parcelle pour lire son analyse multicritère.")
        else:
            performance = selected.get("Typo_SUM_majority")
            st.metric(
                "Performance globale",
                "—" if performance is None else f"Classe {int(performance)}",
            )
            st.caption(f"Commune : {selected.get('commune') or '—'}")
            st.caption(f"N° de parcelle : {selected.get('no_parcelle') or '—'}")
            surface = selected.get("surface")
            st.caption(f"Surface : {surface:,.0f} m²".replace(",", "'") if surface is not None else "Surface : —")

            chart_labels = [label for _, label in SPIDER_FIELDS]
            chart_values = [selected.get(field) for field, _ in SPIDER_FIELDS]
            radar = go.Figure(
                go.Scatterpolar(
                    r=chart_values + chart_values[:1],
                    theta=chart_labels + chart_labels[:1],
                    mode="lines+markers",
                    fill="toself",
                    fillcolor="rgba(42, 156, 142, 0.22)",
                    line={"color": "#2A9C8E", "width": 2},
                    marker={"size": 6, "color": "#2A9C8E"},
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
                config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
                alt="Distribution des quatre indicateurs, sur une échelle de 0 à 3",
                key=f"parcel-indicators-radar-{selected_fid}",
            )

    st.caption("Parcelles cadastrales selon le Code Civil Suisse · SITG · OpenStreetMap · EPSG:2056")


render_dashboard()
