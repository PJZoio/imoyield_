
import streamlit as st
import pandas as pd
import numpy as np
import json
import pydeck as pdk
from pathlib import Path

st.set_page_config(page_title="ImoYield – Mapa de Rentabilidade", page_icon="assets/favicon.png", layout="wide")

DATA_DIR = Path(__file__).parent / "data"

# --- Loaders ---
@st.cache_data
def load_listings():
    df = pd.read_csv(DATA_DIR / "sample_listings.csv")
    num_cols = ["preco_venda","area_m2","renda_mensal","consumo_eletricidade_kwh_ano","consumo_gas_kwh_ano","consumo_outros_kwh_ano","vetor_eletricidade_%","vetor_gas_%","vetor_outros_%","lat","lon"]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

@st.cache_data
def load_geojson():
    with open(DATA_DIR / "freguesias_sample.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

@st.cache_data
def load_epbd_costs():
    return pd.read_csv(DATA_DIR / "epbd_upgrade_costs.csv")

df = load_listings()
epbd = load_epbd_costs()
gj = load_geojson()

# --- Sidebar / Branding ---
st.sidebar.image("assets/logo.png", use_container_width=True)
st.sidebar.markdown("**ImoYield** · Mapa de rentabilidade por freguesia e tipologia.")

st.sidebar.header("Assunções (cálculo)")
vacancia = st.sidebar.slider("Vacância anual (%)", 0.0, 15.0, 5.0, 0.5)
imi = st.sidebar.number_input("IMI (% VPT/preço)", min_value=0.0, max_value=2.0, value=0.35, step=0.05)
condo = st.sidebar.number_input("Condomínio (€/mês)", min_value=0.0, max_value=500.0, value=15.0, step=5.0)
seguro = st.sidebar.number_input("Seguro (€/ano)", min_value=0.0, max_value=500.0, value=30.0, step=5.0)
manut = st.sidebar.number_input("Manutenção (% preço/ano)", min_value=0.0, max_value=2.0, value=0.30, step=0.05)
irs = st.sidebar.number_input("IRS efetivo sobre o NOI (%)", min_value=0.0, max_value=50.0, value=25.0, step=1.0)

st.sidebar.header("EPBD – alvo")
target_class = st.sidebar.selectbox("Classe alvo", ["Sem alvo","C","B","A"])

st.sidebar.caption("**Cores**: azul-escuro (finanças) · teal (energia) · laranja (destaques)")

# --- Metrics calc ---
def compute_metrics(row):
    price = row["preco_venda"]; rent = row["renda_mensal"]
    if pd.isna(price) or price<=0 or pd.isna(rent) or rent<=0:
        return pd.Series([np.nan]*8, index=["gross_yield","egi","op_ex","noi","net_yield","upgrade_cost","legend","cap_rate"])
    gross_year = rent*12.0
    egi = gross_year*(1 - vacancia/100.0)
    op_ex = (condo*12.0) + seguro + (price*(imi/100.0)) + (price*(manut/100.0))
    noi = egi - op_ex
    net = noi*(1 - irs/100.0)
    net_yield = (net/price)*100.0
    cap_rate = (noi/price)*100.0

    # EPBD cost per typology & class
    if target_class != "Sem alvo":
        m = epbd[(epbd["tipologia"]==row["tipologia"]) & (epbd["classe_alvo"]==target_class)]
        cost_per_m2 = float(m["custo_eur_m2"].iloc[0]) if len(m)>0 else 0.0
    else:
        cost_per_m2 = 0.0
    upg_cost = cost_per_m2 * (row.get("area_m2") or 0)

    gy = (gross_year/price)*100.0 if price>0 else np.nan
    legend = f"Bruta: {gy:.1f}% | Líquida: {net_yield:.1f}%"
    return pd.Series([gy, egi, op_ex, noi, net_yield, upg_cost, legend, cap_rate],
                     index=["gross_yield","egi","op_ex","noi","net_yield","upgrade_cost","legend","cap_rate"])

metrics = df.apply(compute_metrics, axis=1)
df = pd.concat([df, metrics], axis=1)

# --- Filters ---
c1, c2, c3 = st.columns(3)
with c1:
    conc = st.selectbox("Concelho", ["(Todos)"] + sorted(df["concelho"].dropna().unique().tolist()))
with c2:
    tip = st.selectbox("Tipologia", ["(Todos)"] + sorted(df["tipologia"].dropna().unique().tolist()))
with c3:
    min_gross = st.slider("Yield bruta mínima (%)", 0.0, 15.0, 0.0, 0.5)

mask = (True)
if conc != "(Todos)":
    mask = mask & (df["concelho"]==conc)
if tip != "(Todos)":
    mask = mask & (df["tipologia"]==tip)
mask = mask & (df["gross_yield"].fillna(0) >= min_gross)
fdf = df[mask].copy()

# --- Choropleth (median yield by freguesia) ---
agg = fdf.groupby("freguesia")["gross_yield"].median().reset_index().rename(columns={"gross_yield":"gy_med"})
gy_min, gy_max = (float(agg["gy_med"].min()) if len(agg)>0 else 0.0,
                  float(agg["gy_med"].max()) if len(agg)>0 else 0.0)

# Brand color ramp: blue_dark -> teal -> orange
def color_for(value, vmin=0.0, vmax=10.0):
    if np.isnan(value):
        return [210,210,210,80]
    if vmax<=vmin: vmax = vmin+1e-6
    t = (value - vmin)/(vmax - vmin)  # 0..1
    # interpolate in two segments
    if t < 0.5:
        t2 = t*2
        # blue_dark (15,23,42) to teal (20,184,166)
        r = int(15 + (20-15)*t2)
        g = int(23 + (184-23)*t2)
        b = int(42 + (166-42)*t2)
    else:
        t2 = (t-0.5)*2
        # teal to orange (249,115,22)
        r = int(20 + (249-20)*t2)
        g = int(184 + (115-184)*t2)
        b = int(166 + (22-166)*t2)
    return [r,g,b,150]

for feat in gj["features"]:
    freg = feat["properties"].get("freguesia","")
    row = agg[agg["freguesia"]==freg]
    gy = float(row["gy_med"].iloc[0]) if len(row)>0 else np.nan
    feat["properties"]["gy_med"] = None if np.isnan(gy) else round(gy,1)
    feat["properties"]["fill_color"] = color_for(gy, vmin=gy_min, vmax=gy_max)

layer_poly = pdk.Layer(
    "GeoJsonLayer", gj, pickable=True, stroked=True, filled=True,
    get_fill_color="properties.fill_color",
    get_line_color=[255,255,255,120], line_width_min_pixels=1, auto_highlight=True
)

view = pdk.ViewState(latitude=fdf["lat"].mean() if len(fdf)>0 else 38.72,
                     longitude=fdf["lon"].mean() if len(fdf)>0 else -9.14,
                     zoom=11)

tooltip_poly = {"text": "{freguesia}\nYield bruta mediana: {gy_med}%"}

st.subheader("ImoYield · Yield bruta por freguesia (mediana)")
st.pydeck_chart(pdk.Deck(layers=[layer_poly], initial_view_state=view, tooltip=tooltip_poly))

# Points layer
if len(fdf)>0:
    radius = 300 + 900 * (fdf["gross_yield"].fillna(0) / max(1e-6, fdf["gross_yield"].fillna(0).max()))
    layer_pts = pdk.Layer(
        "ScatterplotLayer",
        data=fdf.assign(radius=radius),
        get_position='[lon, lat]',
        get_radius='radius',
        pickable=True,
    )
    st.pydeck_chart(pdk.Deck(layers=[layer_poly, layer_pts], initial_view_state=view,
                             tooltip={"text":"{titulo}\n{freguesia}, {concelho}\nBruta: {gross_yield}% | Líquida: {net_yield}%"}))

st.markdown("---")
st.subheader("Fichas de investimento")
cols = ["titulo","tipologia","freguesia","concelho","preco_venda","renda_mensal","gross_yield","cap_rate","net_yield","upgrade_cost","area_m2","classe_energetica","fonte_url"]
st.dataframe(fdf[cols])

ids = ["(Selecione)"] + fdf["id"].tolist()
sel = st.selectbox("Imóvel", ids)
if sel != "(Selecione)":
    r = fdf.set_index("id").loc[sel]
    st.markdown(f"### {r['titulo']}")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.metric("Preço", f"{r['preco_venda']:,.0f} €")
        st.metric("Renda", f"{r['renda_mensal']:,.0f} €/mês")
    with c2:
        st.metric("Yield bruta", f"{r['gross_yield']:.1f}%")
        st.metric("Cap rate (NOI/Preço)", f"{r['cap_rate']:.1f}%")
    with c3:
        st.metric("Yield líquida", f"{r['net_yield']:.1f}%")
        st.metric("Custo EPBD (alvo)", f"{r['upgrade_cost']:,.0f} €")
    st.write("**Freguesia/Concelho:**", r["freguesia"], "/", r["concelho"])
    st.write("**Classe energética:**", r.get("classe_energetica","(por preencher)"))
    st.write("**Fonte:**", r.get("fonte_url","—"))
    st.info("CE/consumos ausentes → estimar por zona climática SCE e marcar como 'estimado'. Na produção, captar do CE do anúncio (quando disponível).")

st.caption("Polígonos de freguesia são de demonstração. Em produção, usar CAOP (DGT) com códigos INE.")
