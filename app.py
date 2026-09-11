import streamlit as st
import requests
import numpy as np
import datetime
import math
import pandas as pd
import io

# CONFIGURACIÓN DE LA PÁGINA WEB - ESTILO PVH
st.set_page_config(
    page_title="PVH | ISO 9223 Corrosion Assessment Tool",
    page_icon="☀️",
    layout="wide"
)

# ESTILOS CSS PERSONALIZADOS (PALETA DE COLORES PVH)
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

# 1. MOTOR DE CÁLCULO ISO 9223 (ZINC)
def calcular_corrosividad_zn(T, RH, P_D, S_D):
    if T <= 10:
        f_Zn = 0.038 * (T - 10)
    else:
        f_Zn = -0.071 * (T - 10)
    
    term_so2 = 0.0129 * (P_D ** 0.44) * math.exp(0.046 * RH + f_Zn)
    term_cl = 0.0175 * (S_D ** 0.52) * math.exp(0.008 * RH + 0.038 * T)
    
    r_corr = term_so2 + term_cl

    if r_corr <= 0.05: categoria = "C1.0 (Muy baja)"
    elif r_corr <= 0.10: categoria = "C1.5 (Muy baja - límite)"
    elif r_corr <= 0.40: categoria = "C2.0 (Baja)"
    elif r_corr <= 0.70: categoria = "C2.5 (Baja - alto)"
    elif r_corr <= 1.40: categoria = "C3.0 (Moderada)"
    elif r_corr <= 2.10: categoria = "C3.5 (Moderada - severo)"
    elif r_corr <= 3.15: categoria = "C4.0 (Alta)"
    elif r_corr <= 4.20: categoria = "C4.5 (Alta - severo)"
    elif r_corr <= 6.30: categoria = "C5.0 (Muy alta)"
    elif r_corr <= 8.40: categoria = "C5.5 (Muy alta - crítico)"
    else: categoria = "CX (Extrema)"

    return round(r_corr, 2), categoria

# 2. CONEXIÓN API NASA POWER (15 AÑOS DE HISTÓRICO)
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

# 3. CABECERA INSTITUCIONAL PVH
st.markdown('<span class="pvh-badge">PV HARDWARE (PVH) ENGINEERING TOOL</span>', unsafe_allow_html=True)
st.markdown('<div class="pvh-header">⚡ ISO 9223 Atmospheric Corrosivity Estimator</div>', unsafe_allow_html=True)
st.markdown('<div class="pvh-subtitle">Evaluación de corrosividad ambiental para seguidores solares y estructuras fotovoltaicas de PVH mediante datos satelitales NASA POWER.</div>', unsafe_allow_html=True)

# BARRA LATERAL
st.sidebar.markdown("### ☀️ PVH Project Location")
latitud = st.sidebar.number_input("Latitud", value=10.0000, format="%.4f")
longitud = st.sidebar.number_input("Longitud", value=28.1700, format="%.4f")

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

# PESTAÑAS PRINCIPALES
tab_calc, tab_mapa, tab_pvh = st.tabs(["📊 Análisis y Corrosividad", "🗺️ Emplazamiento Solar", "ℹ️ Sobre PVH & ISO 9223"])

with tab_mapa:
    st.subheader("Ubicación de la Planta Fotovoltaica")
    df_mapa = pd.DataFrame({"lat": [latitud], "lon": [longitud]})
    st.map(df_mapa, zoom=6)

with tab_pvh:
    st.markdown(r"""
    ### PV Hardware (PVH)
    **PVH** es uno de los líderes mundiales en fabricación de seguidores solares (*trackers*), estructuras fijas y sistemas de control SCADA para plantas fotovoltaicas a gran escala.
    
    #### Evaluación según ISO 9223:2012
    La tasa de pérdida de masa/espesor del Zinc ($g/m^2 \cdot \text{año}$ o $\mu m/\text{año}$) determina la vida útil proyectada del recubrimiento protector en estructuras de acero galvanizado y seguidores solares en condiciones atmosféricas reales.
    """)

with tab_calc:
    if btn_calcular:
        with st.spinner("Procesando histórico climático de 15 años de NASA POWER para el proyecto PVH..."):
            T, RH, a_inicio, a_fin, total_dias = obtener_clima_nasa_15anos(latitud, longitud, num_anos=15)
            
            if T is not None and RH is not None:
                r_corr, categoria = calcular_corrosividad_zn(T, RH, P_D, S_D)
                
                st.subheader("Resultados Principales de Corrosión")
                
                col1, col2 = st.columns(2)
                with col1:
                    with st.container(border=True):
                        st.metric("Tasa Pérdida de Espesor (Zinc)", f"{r_corr} µm/año")
                with col2:
                    with st.container(border=True):
                        st.metric("Categoría Corrosividad ISO 9223", categoria)
                
                st.subheader("📋 Informe Técnico del Emplazamiento (PVH Engineering)")
                
                df_resumen = pd.DataFrame({
                    "Parámetro Metrológico / Normativo": [
                        "Empresa / Solución",
                        "Coordenadas del Proyecto",
                        "Periodo Histórico Procesado",
                        "Registros Diarios Analizados",
                        "Temperatura Media Anual (T)",
                        "Humedad Relativa Media Anual (RH)",
                        "Tasa Deposición SO2 (P_D)",
                        "Tasa Deposición Cloruros (S_D)",
                        "Tasa Corrosión Calibrada (Zinc)",
                        "Clasificación Corrosividad Atmosférica"
                    ],
                    "Valor Obtenido": [
                        "PV Hardware (PVH)",
                        f"Lat {latitud}, Lon {longitud}",
                        f"{a_inicio} - {a_fin} (15 años)",
                        f"{total_dias} días",
                        f"{T} °C",
                        f"{RH} %",
                        f"{P_D} mg/m²·día",
                        f"{S_D} mg/m²·día",
                        f"{r_corr} µm/año",
                        categoria
                    ]
                })
                
                st.table(df_resumen)
                
                # EXPORTACIÓN EXCEL
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_resumen.to_excel(writer, index=False, sheet_name="Informe PVH ISO 9223")
                
                st.download_button(
                    label="📥 Descargar Informe Técnico PVH en Excel",
                    data=buffer.getvalue(),
                    file_name=f"PVH_Corrosion_Report_ISO9223_Lat{latitud}_Lon{longitud}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("❌ No se pudieron descargar datos satelitales para las coordenadas indicadas.")