import streamlit as st
import requests
import numpy as np
import datetime
import math
import pandas as pd
import io

# CONFIGURACIÓN DE LA PÁGINA WEB
st.set_page_config(
    page_title="Calculadora Corrosividad ISO 9223",
    page_icon="🛡️",
    layout="wide"
)

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

# 3. INTERFAZ GRÁFICA STREAMLIT
st.title("🛡️ Estimación de Corrosividad de Zinc (ISO 9223:2012)")
st.markdown("Herramienta de ingeniería para la determinación automatizada de la tasa de corrosión atmosférica mediante datos satelitales globales.")

# BARRA LATERAL (ENTRADAS)
st.sidebar.header("📍 Coordenadas de la Ubicación")
latitud = st.sidebar.number_input("Latitud", value=-15.7171, format="%.4f")
longitud = st.sidebar.number_input("Longitud", value=28.1523, format="%.4f")

st.sidebar.header("🏭 Entorno Contaminante (ISO 9223 Anexo B)")

opciones_so2 = {
    "Industrial Pesado / Minería cercana (P3: 80 mg/m²·d)": 80.0,
    "Industrial Moderado (P2: 50 mg/m²·d)": 50.0,
    "Urbano / Industrial ligero (P1: 25 mg/m²·d)": 25.0,
    "Rural / Limpio (P0: ≤ 10 mg/m²·d)": 10.0,
    "Personalizado": -1.0
}
sel_so2 = st.sidebar.selectbox("Escenario SO2", list(opciones_so2.keys()))
P_D = st.sidebar.slider("SO2 manual (mg/m²·d)", 1.0, 200.0, 80.0) if opciones_so2[sel_so2] == -1.0 else opciones_so2[sel_so2]

opciones_cl = {
    "Interior lejano (> 20 km del mar) (S0: ≤ 3 mg/m²·d)": 3.0,
    "Interior moderado / Costa lejana (S1: 30 mg/m²·d)": 30.0,
    "Zona costera cercana (1 - 10 km) (S2: 150 mg/m²·d)": 150.0,
    "Frente marino / Playa (< 1 km) (S3: 300 mg/m²·d)": 300.0,
    "Personalizado": -1.0
}
sel_cl = st.sidebar.selectbox("Escenario Cl-", list(opciones_cl.keys()))
S_D = st.sidebar.slider("Cl- manual (mg/m²·d)", 1.0, 500.0, 3.0) if opciones_cl[sel_cl] == -1.0 else opciones_cl[sel_cl]

btn_calcular = st.sidebar.button("🚀 Consultar NASA y Calcular", type="primary")

# PANEL PRINCIPAL (RESULTADOS)
if btn_calcular:
    with st.spinner("Conectando con la API de NASA POWER y procesando 15 años de serie histórica..."):
        T, RH, a_inicio, a_fin, total_dias = obtener_clima_nasa_15anos(latitud, longitud, num_anos=15)
        
        if T is not None and RH is not None:
            r_corr, categoria = calcular_corrosividad_zn(T, RH, P_D, S_D)
            
            st.subheader("Resultados Principales")
            col1, col2 = st.columns(2)
            col1.metric("Tasa de Corrosión de Zinc", f"{r_corr} µm/año")
            col2.metric("Categoría ISO 9223", categoria)
            
            st.subheader("📋 Ficha Técnica del Proyecto")
            
            df_resumen = pd.DataFrame({
                "Parámetro Metrológico / Normativo": [
                    "Coordenadas Analizadas",
                    "Periodo Climático Procesado",
                    "Lecturas Diarias Válidas Analizadas",
                    "Temperatura Media Anual (T)",
                    "Humedad Relativa Media Anual (RH)",
                    "Tasa Deposición SO2 (P_D)",
                    "Tasa Deposición Cloruros (S_D)",
                    "Tasa de Pérdida de Espesor Calculada",
                    "Clasificación Corrosividad Atmosférica"
                ],
                "Valor Obtenido": [
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
            
            # EXPORTACIÓN A EXCEL
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_resumen.to_excel(writer, index=False, sheet_name="Informe ISO 9223")
            
            st.download_button(
                label="📥 Descargar Informe en Excel",
                data=buffer.getvalue(),
                file_name=f"Informe_Corrosividad_ISO9223_Lat{latitud}_Lon{longitud}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("❌ No se pudieron descargar datos para las coordenadas indicadas.")
