import streamlit as st
import requests
import numpy as np
import datetime
import math
import pandas as pd
import io

# CONFIGURACIÓN PÁGINA WEB PVH
st.set_page_config(
    page_title="PVH | ISO 9223 & Commercial Coating Selector",
    page_icon="☀️",
    layout="wide"
)

# ESTILOS CSS ESTILO PVH
st.markdown("""
    <style>
    .stButton>button {
        background-color: #E05A10 !important;
        color: white !important;
        border-radius: 6px !important;
        font-weight: bold !important;
        border: none !important;
        height: 3em !important;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #FF6A13 !important;
        box-shadow: 0 4px 12px rgba(224, 90, 16, 0.4) !important;
    }
    div[data-testid="stMetricValue"] {
        color: #FF5500 !important;
        font-weight: bold;
    }
    .pvh-header {
        font-size: 28px;
        font-weight: 800;
        color: #FFFFFF;
        margin-bottom: 2px;
    }
    .pvh-subtitle {
        font-size: 15px;
        color: #94A3B8;
        margin-bottom: 20px;
    }
    .pvh-badge {
        background-color: #E05A10;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        letter-spacing: 1px;
    }
    </style>
""", unsafe_allow_html=True)

# TABLAS DE REFERENCIA DE RECUBRIMIENTOS PVH
TABLA_PREGALVANIZADO = [
    {"Designacion": "Z100", "Espesor_um": 7.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z140", "Espesor_um": 10.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z180", "Espesor_um": 13.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z200", "Espesor_um": 14.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z225", "Espesor_um": 16.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z275 (G90)", "Espesor_um": 20.0, "Tipo": "Oferta Comun PVH"},
    {"Designacion": "Z350", "Espesor_um": 25.0, "Tipo": "Oferta Especial / Salto 35um"},
    {"Designacion": "Z450 (G140)", "Espesor_um": 32.0, "Tipo": "Oferta Especial"},
    {"Designacion": "Z600 (G185)", "Espesor_um": 42.0, "Tipo": "Oferta Especial"},
]

TABLA_MAGNELIS = [
    {"Designacion": "ZM70", "Espesor_um": 5.0, "Eq_Zinc_um": 15.0},
    {"Designacion": "ZM90", "Espesor_um": 7.0, "Eq_Zinc_um": 21.0},
    {"Designacion": "ZM120", "Espesor_um": 10.0, "Eq_Zinc_um": 30.0},
    {"Designacion": "ZM175", "Espesor_um": 14.0, "Eq_Zinc_um": 42.0},
    {"Designacion": "ZM200", "Espesor_um": 16.0, "Eq_Zinc_um": 48.0},
    {"Designacion": "ZM250", "Espesor_um": 20.0, "Eq_Zinc_um": 60.0},
    {"Designacion": "ZM310", "Espesor_um": 25.0, "Eq_Zinc_um": 75.0},  # Salto comercial 35um
    {"Designacion": "ZM430", "Espesor_um": 35.0, "Eq_Zinc_um": 105.0},
    {"Designacion": "ZM620", "Espesor_um": 50.0, "Eq_Zinc_um": 150.0},
]

# 1. CÁLCULO DE CORROSIVIDAD ISO 9223 & EXPONENCIAL PVH
def calcular_corrosividad_pvh(T, RH, P_D, S_D, t_anos):
    if T <= 10:
        f_Zn = 0.038 * (T - 10)
    else:
        f_Zn = -0.071 * (T - 10)
    
    term_so2 = 0.0129 * (P_D ** 0.44) * math.exp(0.046 * RH + f_Zn)
    term_cl = 0.0175 * (S_D ** 0.52) * math.exp(0.008 * RH + 0.038 * T)
    
    r_cz = term_so2 + term_cl

    # Categorización ISO
    if r_cz <= 0.10: categoria, cat_code = "C1 / C2 Low", "C1"
    elif r_cz <= 0.40: categoria, cat_code = "C2 Mean", "C2"
    elif r_cz <= 0.70: categoria, cat_code = "C2 High / C3 Low", "C2"
    elif r_cz <= 1.40: categoria, cat_code = "C3 Mean", "C3"
    elif r_cz <= 2.10: categoria, cat_code = "C3 High / C4 Low", "C3"
    elif r_cz <= 3.15: categoria, cat_code = "C4 Mean", "C4"
    elif r_cz <= 4.20: categoria, cat_code = "C4 High / C5 Low", "C4"
    elif r_cz <= 6.30: categoria, cat_code = "C5 Mean", "C5"
    else: categoria, cat_code = "C5 High / CX", "CX"

    # Ecuación exponencial de degradación acumulada a t años: d = r_cz * (t ^ b_zinc)
    b_zinc = 0.813
    d_acumulado_zn = r_cz * (t_anos ** b_zinc)

    return round(r_cz, 2), round(d_acumulado_zn, 2), categoria, cat_code

# 2. LÓGICA COMERCIAL DE SELECCIÓN PVH (ESPESORES 20 µm / 35 µm)
def seleccionar_oferta_pvh(cat_code, t_anos, d_acumulado_zn):
    if d_acumulado_zn <= 20.0:
        oferta_tipo = "Oferta Común (Estándar)"
        rec_recomendado = "Z275 (G90)"
        espesor_rec = "20.0 µm por cara"
        justificacion = f"Degradación acumulada ({d_acumulado_zn} µm) ≤ 20.0 µm. Apto Z275."
        
    elif d_acumulado_zn <= 35.0:
        oferta_tipo = "Oferta Común (Nivel 35 µm)"
        rec_recomendado = "Z350 / ZM310"
        espesor_rec = "25.0 µm ZM310 (Eq. 75 µm Zinc) ó 25.0 µm Z350"
        justificacion = f"Degradación acumulada ({d_acumulado_zn} µm) supera los 20 µm. Requiere salto a recubrimiento Z350 / ZM310."
        
    elif d_acumulado_zn <= 105.0:
        oferta_tipo = "Oferta Grande / Cliente Importante"
        rec_recomendado = "ZM430"
        espesor_rec = "35.0 µm por cara (Eq. 105 µm Zinc)"
        justificacion = f"Degradación acumulada ({d_acumulado_zn} µm) excede los 35 µm. Requiere ZM430."
        
    elif d_acumulado_zn <= 150.0:
        oferta_tipo = "Oferta Grande / Cliente Importante"
        rec_recomendado = "ZM620"
        espesor_rec = "50.0 µm por cara (Eq. 150 µm Zinc)"
        justificacion = "Degradación elevada. Requiere recubrimiento pesado ZM620."
        
    else:
        oferta_tipo = "Oferta Grande / Cliente Importante"
        rec_recomendado = "Galvanizado de Tubo (HDG) / Sistema Dúplex"
        espesor_rec = "> 85.0 µm"
        justificacion = "Ambiente de extrema agresividad (C5/CX)."

    return oferta_tipo, rec_recomendado, espesor_rec, justificacion

# 3. CONEXIÓN API NASA POWER
@st.cache_data(ttl=86400)
def obtener_clima_nasa_15anos(lat, lon, num_anos=15):
    ano_fin = datetime.datetime.now().year - 1
    ano_inicio = ano_fin - num_anos + 1
    
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        'parameters': 'T2M,RH2M',
        'community': 'AG',
        'longitude': lon,
        'latitude': lat,
        'start': f'{ano_inicio}0101',
        'end': f'{ano_fin}1231',
        'format': 'JSON'
    }
    
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code == 200:
            data = response.json()
            param_data = data['properties']['parameter']
            
            temp_vals = [v for v in param_data['T2M'].values() if v != -999]
            rh_vals = [v for v in param_data['RH2M'].values() if v != -999]
            
            if temp_vals and rh_vals:
                T_media = round(float(np.mean(temp_vals)), 2)
                RH_media = round(float(np.mean(rh_vals)), 2)
                return T_media, RH_media, ano_inicio, ano_fin, len(temp_vals)
            else:
                return None, None, ano_inicio, ano_fin, 0
        else:
            return None, None, ano_inicio, ano_fin, 0
    except Exception:
        return None, None, ano_inicio, ano_fin, 0

# CABECERA INSTITUCIONAL PVH
st.markdown('<span class="pvh-badge">PV HARDWARE (PVH) ENGINEERING TOOL</span>', unsafe_allow_html=True)
st.markdown('<div class="pvh-header">⚡ ISO 9223 Corrosivity & Commercial Coating Selector</div>', unsafe_allow_html=True)
st.markdown('<div class="pvh-subtitle">Cálculo de degradación exponencial b-zinc (0.813) y recomendación de catálogo comercial PVH (Z275 / Z350 / ZM310 / ZM430).</div>', unsafe_allow_html=True)

# BARRA LATERAL
st.sidebar.markdown("### ☀️ PVH Project Location")
latitud = st.sidebar.number_input("Latitud", value=10.0000, format="%.4f")
longitud = st.sidebar.number_input("Longitud", value=28.1700, format="%.4f")

st.sidebar.markdown("---")
st.sidebar.markdown("### ⏱️ Parámetros de Diseño PVH")
t_anos = st.sidebar.slider("Periodo de diseño t (años)", 10, 50, 30, step=5)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🏭 Contaminantes Ambientales (ISO 9223)")

opciones_so2 = {
    "Industrial Pesado / Minería (P3: 80 mg/m²·d)": 80.0,
    "Industrial Moderado (P2: 50 mg/m²·d)": 50.0,
    "Urbano / Industrial ligero (P1: 25 mg/m²·d)": 25.0,
    "Rural / Limpio (P0: ≤ 10 mg/m²·d)": 10.0,
    "Personalizado": -1.0
}
sel_so2 = st.sidebar.selectbox("Escenario SO2", list(opciones_so2.keys()))
P_D = st.sidebar.slider("SO2 manual (mg/m²·d)", 1.0, 200.0, 80.0) if opciones_so2[sel_so2] == -1.0 else opciones_so2[sel_so2]

opciones_cl = {
    "Interior lejano (> 20 km mar) (S0: ≤ 3 mg/m²·d)": 3.0,
    "Interior moderado / Costa (S1: 30 mg/m²·d)": 30.0,
    "Zona costera cercana (1-10 km) (S2: 150 mg/m²·d)": 150.0,
    "Frente marino / Playa (< 1 km) (S3: 300 mg/m²·d)": 300.0,
    "Personalizado": -1.0
}
sel_cl = st.sidebar.selectbox("Escenario Cl-", list(opciones_cl.keys()))
S_D = st.sidebar.slider("Cl- manual (mg/m²·d)", 1.0, 500.0, 3.0) if opciones_cl[sel_cl] == -1.0 else opciones_cl[sel_cl]

st.sidebar.markdown("---")
btn_calcular = st.sidebar.button("⚡ Consultar NASA & Calcular PVH", type="primary")

# PESTAÑAS
tab_calc, tab_tablas, tab_mapa = st.tabs(["📊 Análisis y Oferta PVH", "📋 Tablas de Referencia PVH", "🗺️ Emplazamiento Solar"])

with tab_mapa:
    st.subheader("Ubicación de la Planta Fotovoltaica")
    df_mapa = pd.DataFrame({"lat": [latitud], "lon": [longitud]})
    st.map(df_mapa, zoom=6)

with tab_tablas:
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.markdown("#### Pregalvanizado Convencional (Zinc)")
        st.dataframe(pd.DataFrame(TABLA_PREGALVANIZADO), width="stretch")
    with col_t2:
        st.markdown("#### Magnelis® (ZM - Zinc-Aluminio-Magnesio)")
        st.dataframe(pd.DataFrame(TABLA_MAGNELIS), width="stretch")

with tab_calc:
    if btn_calcular:
        with st.spinner("Procesando histórico climático de 15 años NASA POWER..."):
            T, RH, a_inicio, a_fin, total_dias = obtener_clima_nasa_15anos(latitud, longitud, num_anos=15)
            
            if T is not None and RH is not None:
                r_cz, d_acumulado_zn, categoria, cat_code = calcular_corrosividad_pvh(T, RH, P_D, S_D, t_anos)
                oferta_tipo, rec_recomendado, espesor_rec, justificacion = seleccionar_oferta_pvh(cat_code, t_anos, d_acumulado_zn)
                
                st.subheader("Resultados de Corrosividad Atmosférica")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    with st.container(border=True):
                        st.metric("Tasa Zinc r_cz", f"{r_cz} µm/año")
                with c2:
                    with st.container(border=True):
                        st.metric("Exponente b-zinc", "0.813")
                with c3:
                    with st.container(border=True):
                        st.metric(f"Degradación d({t_anos}a)", f"{d_acumulado_zn} µm")
                with c4:
                    with st.container(border=True):
                        st.metric("Categoría ISO", categoria)

                # CUADRO COMERCIAL PVH
                st.success(f"💼 **{oferta_tipo}:** **{rec_recomendado}** ({espesor_rec})\n\n_{justificacion}_")
                
                st.subheader("📋 Informe Técnico de Ingeniería PVH")
                
                df_resumen = pd.DataFrame({
                    "Parámetro Metrológico / Normativo": [
                        "Empresa / Solución",
                        "Coordenadas del Proyecto",
                        "Periodo Histórico Analizado",
                        "Temperatura Media Anual (T)",
                        "Humedad Relativa Media Anual (RH)",
                        "Categoría Corrosividad ISO 9223",
                        "Tasa Corrosión Zinc (r_cz)",
                        "Ecuación Aplicada (t > 20 años)",
                        "Periodo de Diseño (t)",
                        "Pérdida Espesor Acumulada d(µm)",
                        "Tipo de Oferta Comercial",
                        "Material Recomendado PVH",
                        "Espesor de Recubrimiento"
                    ],
                    "Valor Obtenido": [
                        "PV Hardware (PVH)",
                        f"Lat {latitud}, Lon {longitud}",
                        f"{a_inicio} - {a_fin} ({total_dias} días)",
                        f"{T} °C",
                        f"{RH} %",
                        categoria,
                        f"{r_cz} µm/año",
                        f"d = r_cz * (t ^ 0.813)",
                        f"{t_anos} años",
                        f"{d_acumulado_zn} µm (Eq. Zinc)",
                        oferta_tipo,
                        rec_recomendado,
                        espesor_rec
                    ]
                })
                
                st.table(df_resumen)
                
                # EXPORTACIÓN EXCEL
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_resumen.to_excel(writer, index=False, sheet_name="PVH Offer Report")
                
                st.download_button(
                    label="📥 Descargar Informe Comercial PVH en Excel",
                    data=buffer.getvalue(),
                    file_name=f"PVH_Offer_Report_{t_anos}yr_Lat{latitud}_Lon{longitud}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("❌ No se pudieron descargar datos satelitales para las coordenadas indicadas.")
                