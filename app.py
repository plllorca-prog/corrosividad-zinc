import streamlit as st
import requests
import numpy as np
import datetime
import math
import pandas as pd
import io
import pypdf
from google import genai

# CONFIGURACIÓN PÁGINA WEB PVH
st.set_page_config(
    page_title="PVH | ISO 9223 & Commercial Coating Selector",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ESTILOS CSS ESTILO PVH DE ALTO IMPACTO VISUAL
st.markdown("""
st.markdown("""
    
""", unsafe_allow_html=True)

# TABLAS DE REFERENCIA DE RECUBRIMIENTOS PVH
TABLA_PREGALVANIZADO = [
    {"Designacion": "Z100", "Espesor_um": 7.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z140", "Espesor_um": 10.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z180", "Espesor_um": 13.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z200", "Espesor_um": 14.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z225", "Espesor_um": 16.0, "Tipo": "Standard Pregalvanized"},
    {"Designacion": "Z275 (G90)", "Espesor_um": 20.0, "Tipo": "Oferta Comun PVH (hasta 25µm)"},
    {"Designacion": "Z350", "Espesor_um": 25.0, "Tipo": "Oferta Especial / Salto >25µm"},
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
    {"Designacion": "ZM310", "Espesor_um": 25.0, "Eq_Zinc_um": 75.0},
    {"Designacion": "ZM430", "Espesor_um": 35.0, "Eq_Zinc_um": 105.0},
    {"Designacion": "ZM620", "Espesor_um": 50.0, "Eq_Zinc_um": 150.0},
]

# CÁLCULOS PVH
def calcular_corrosividad_pvh(T, RH, P_D, S_D, t_anos):
    if T <= 10:
        f_Zn = 0.038 * (T - 10)
    else:
        f_Zn = -0.071 * (T - 10)
    
    term_so2 = 0.0129 * (P_D ** 0.44) * math.exp(0.046 * RH + f_Zn)
    term_cl = 0.0175 * (S_D ** 0.52) * math.exp(0.008 * RH + 0.038 * T)
    
    r_cz = term_so2 + term_cl

    if r_cz <= 0.10: categoria, cat_code = "C1 / C2 Low", "C1"
    elif r_cz <= 0.40: categoria, cat_code = "C2 Mean", "C2"
    elif r_cz <= 0.70: categoria, cat_code = "C2 High / C3 Low", "C2"
    elif r_cz <= 1.40: categoria, cat_code = "C3 Mean", "C3"
    elif r_cz <= 2.10: categoria, cat_code = "C3 High / C4 Low", "C3"
    elif r_cz <= 3.15: categoria, cat_code = "C4 Mean", "C4"
    elif r_cz <= 4.20: categoria, cat_code = "C4 High / C5 Low", "C4"
    elif r_cz <= 6.30: categoria, cat_code = "C5 Mean", "C5"
    else: categoria, cat_code = "C5 High / CX", "CX"

    b_zinc = 0.813
    d_acumulado_zn = r_cz * (t_anos ** b_zinc)

    return round(r_cz, 2), round(d_acumulado_zn, 2), categoria, cat_code

def seleccionar_oferta_pvh(cat_code, t_anos, d_acumulado_zn):
    if d_acumulado_zn <= 25.0:
        oferta_tipo = "Oferta Común (Estándar)"
        rec_recomendado = "Z275 (G90)"
        espesor_rec = "20.0 µm por cara (Válido comercialmente hasta 25.0 µm)"
        justificacion = f"Degradación acumulada ({d_acumulado_zn} µm) ≤ 25.0 µm. Cubierto por la oferta estándar Z275."
    elif d_acumulado_zn <= 35.0:
        oferta_tipo = "Oferta Común (Nivel 35 µm)"
        rec_recomendado = "Z350 / ZM310"
        espesor_rec = "25.0 µm ZM310 (Eq. 75 µm Zinc) ó 25.0 µm Z350"
        justificacion = f"Degradación acumulada ({d_acumulado_zn} µm) supera los 25.0 µm. Requiere salto a recubrimiento Z350 / ZM310."
    elif d_acumulado_zn <= 105.0:
        oferta_tipo = "Oferta Grande / Cliente Importante"
        rec_recomendado = "ZM430"
        espesor_rec = "35.0 µm por cara (Eq. 105 µm Zinc)"
        justificacion = f"Degradación acumulada ({d_acumulado_zn} µm) excede los 35.0 µm. Requiere ZM430."
    elif d_acumulado_zn <= 150.0:
        oferta_tipo = "Oferta Grande / Cliente Importante"
        rec_recomendado = "ZM620"
        espesor_rec = "50.0 µm por cara (Eq. 150 µm Zinc)"
        justificacion = "Degradación elevada. Requiere recubrimiento pesado ZM620."
    else:
        oferta_tipo = "Oferta Grande / Cliente Importante"
        rec_recomendado = "Galvanizado HDG / Dúplex"
        espesor_rec = "> 85.0 µm"
        justificacion = "Ambiente de extrema agresividad (C5/CX)."

    return oferta_tipo, rec_recomendado, espesor_rec, justificacion
    # EXTRACCIÓN Y LECTURA DE PDF
def extraer_texto_pdf(pdf_file):
    reader = pypdf.PdfReader(pdf_file)
    texto = ""
    for page in reader.pages[:40]:
        texto += page.extract_text() or ""
    return texto

def analizar_informe_pvh_gemini(texto_pdf, api_key_input=""):
    api_key = api_key_input or st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("No se encontró una API Key de Gemini válida.")
        
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Eres un experto en corrosión y estructuras solares de PV Hardware (PVH).
    Analiza el siguiente informe técnico y devuelve un VISOR TÉCNICO ESTRUCTURADO en Markdown.
    NO tomes decisiones automáticas, solo extrae los datos con claridad para que el usuario pueda revisarlos:

    ### 🏭 1. PARÁMETROS ATMOSFÉRICOS (ISO 9223)
    - **SO2:** (Valores o nivel industrial).
    - **Cloruros / Costa:** (Distancia al mar o Cl-).
    - **Sugerencia:** (Indica el escenario P0-P3 o S0-S3 recomendado para revisar).

    ### 🪨 2. CORROSIVIDAD EN SUELO (GEOTÉCNICO)
    - **Resistividad:** (Ohm.m), **pH**, **Sulfatos/Cloruros** y **Tasa Zinc en suelo** (µm/año).

    ### ⚠️ 3. ALERTAS Y RECOMENDACIONES
    - (Resumen breve sobre recubrimientos o hincas).

    Texto:
    {texto_pdf[:30000]}
    """
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )
    return response.text

@st.cache_data(ttl=86400)
def obtener_clima_nasa_15anos(lat, lon, num_anos=15):
    ano_fin = datetime.datetime.now().year - 1
    ano_inicio = ano_fin - num_anos + 1
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    params = {
        'parameters': 'T2M,RH2M', 'community': 'AG',
        'longitude': lon, 'latitude': lat,
        'start': f'{ano_inicio}0101', 'end': f'{ano_fin}1231', 'format': 'JSON'
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        if response.status_code == 200:
            data = response.json()
            param_data = data['properties']['parameter']
            temp_vals = [v for v in param_data['T2M'].values() if v != -999]
            rh_vals = [v for v in param_data['RH2M'].values() if v != -999]
            if temp_vals and rh_vals:
                return round(float(np.mean(temp_vals)), 2), round(float(np.mean(rh_vals)), 2), ano_inicio, ano_fin, len(temp_vals)
    except Exception:
        pass
    return None, None, ano_inicio, ano_fin, 0
    # INTERFAZ DE USUARIO SPLIT-SCREEN
st.markdown('PV HARDWARE (PVH) ENGINEERING TOOL', unsafe_allow_html=True)
st.markdown('
', unsafe_allow_html=True)
st.markdown('

Análisis integrado: Escaneo de informe geotécnico (Gemini AI) y cálculo automático de recubrimientos solares.

', unsafe_allow_html=True)
st.sidebar.markdown("### ☀️ Ubicación del Proyecto")
latitud = st.sidebar.number_input("Latitud", value=39.4700, format="%.4f")
longitud = st.sidebar.number_input("Longitud", value=-0.3764, format="%.4f")
st.sidebar.markdown("---")
st.sidebar.markdown("### ⏱️ Diseño de Estructura")
t_anos = st.sidebar.slider("Periodo de diseño t (años)", 10, 50, 30, step=5)
col_izq, col_der = st.columns([0.45, 0.55], gap="medium")
with col_izq:
st.subheader("📄 Visor de Extracción de PDF (Gemini AI)")
uploaded_pdf = st.file_uploader("Cargar estudio geotécnico / ambiental", type=["pdf"])
if "resultado_pdf_pvh" not in st.session_state:
    st.session_state.resultado_pdf_pvh = None

if uploaded_pdf is not None:
    if st.button("🔍 Escanear PDF con Gemini IA"):
        with st.spinner("Escaneando informe técnico..."):
            try:
                texto_doc = extraer_texto_pdf(uploaded_pdf)
                st.session_state.resultado_pdf_pvh = analizar_informe_pvh_gemini(texto_doc)
                st.success("✅ Datos extraídos correctamente.")
            except Exception as e:
                st.error(f"❌ Error al procesar: {str(e)}")

if st.session_state.resultado_pdf_pvh is not None:
    with st.container(border=True):
        st.markdown(st.session_state.resultado_pdf_pvh)
else:
    st.info("💡 Sube un PDF para visualizar los parámetros de SO2, cloruros, resistividad y pH mientras usas la calculadora a la derecha.")
    # COLUMNA DERECHA: CALCULADORA Y RESULTADOS
with col_der:
    st.subheader("📊 Calculadora de Corrosividad Atmosférica")
    
    c_so2, c_cl = st.columns(2)
    with c_so2:
        opciones_so2 = {
            "Industrial Pesado (P3: 80 mg/m²·d)": 80.0,
            "Industrial Moderado (P2: 50 mg/m²·d)": 50.0,
            "Urbano / Ligero (P1: 25 mg/m²·d)": 25.0,
            "Rural / Limpio (P0: ≤ 10 mg/m²·d)": 10.0,
            "Personalizado": -1.0
        }
        sel_so2 = st.selectbox("Escenario SO2", list(opciones_so2.keys()))
        P_D = st.slider("SO2 manual (mg/m²·d)", 1.0, 200.0, 50.0) if opciones_so2[sel_so2] == -1.0 else opciones_so2[sel_so2]

    with c_cl:
        opciones_cl = {
            "Interior lejano (> 20 km) (S0: ≤ 3 mg/m²·d)": 3.0,
            "Interior / Costa (S1: 30 mg/m²·d)": 30.0,
            "Costera cercana (1-10 km) (S2: 150 mg/m²·d)": 150.0,
            "Frente marino (< 1 km) (S3: 300 mg/m²·d)": 300.0,
            "Personalizado": -1.0
        }
        sel_cl = st.selectbox("Escenario Cl-", list(opciones_cl.keys()))
        S_D = st.slider("Cl- manual (mg/m²·d)", 1.0, 500.0, 3.0) if opciones_cl[sel_cl] == -1.0 else opciones_cl[sel_cl]

    btn_calcular = st.button("⚡ Consultar NASA & Calcular Oferta PVH", type="primary")

    if btn_calcular:
        with st.spinner("Procesando datos climáticos satelitales NASA POWER..."):
            T, RH, a_inicio, a_fin, total_dias = obtener_clima_nasa_15anos(latitud, longitud)
            
            if T is not None and RH is not None:
                r_cz, d_acumulado_zn, categoria, cat_code = calcular_corrosividad_pvh(T, RH, P_D, S_D, t_anos)
                oferta_tipo, rec_recomendado, espesor_rec, justificacion = seleccionar_oferta_pvh(cat_code, t_anos, d_acumulado_zn)
                
                st.markdown("---")
                col_h1, col_h2 = st.columns(2)
                with col_h1:
                    card_html1 = f'
                    {categoria}

Tasa degradación: {r_cz} µm/año

'
st.markdown(card_html1, unsafe_allow_html=True)
with col_h2:
card_html2 = f'

💼 RECUBRIMIENTO PVH ({t_anos} AÑOS)

{rec_recomendado}

{espesor_rec}

'
st.markdown(card_html2, unsafe_allow_html=True)
st.markdown("
", unsafe_allow_html=True)
m1, m2, m3 = st.columns(3)
            with m1:
                m_html1 = f'

PÉRDIDA ACUMULADA

{d_acumulado_zn} µm

'
st.markdown(m_html1, unsafe_allow_html=True)
with m2:
m_html2 = '

EXPONENTE B-ZINC

0.813

'
st.markdown(m_html2, unsafe_allow_html=True)
with m3:
m_html3 = f'

OFERTA PVH

{oferta_tipo}

'
st.markdown(m_html3, unsafe_allow_html=True)
st.info(f"💡 **Justificación Comercial:** _{justificacion}_")

            with st.expander("📋 Ver Informe Técnico Completo y Descargar Excel"):
                df_resumen = pd.DataFrame({
                    "Parámetro Metrológico / Normativo": [
                        "Empresa", "Coordenadas", "Periodo Histórico", "Temp. Media (T)", "Humedad (RH)",
                        "Categoría ISO 9223", "Tasa Zinc (r_cz)", "Periodo Diseño", "Pérdida Acumulada", "Material Recomendado"
                    ],
                    "Valor Obtenido": [
                        "PV Hardware (PVH)", f"Lat {latitud}, Lon {longitud}", f"{a_inicio}-{a_fin} ({total_dias} días)",
                        f"{T} °C", f"{RH} %", categoria, f"{r_cz} µm/año", f"{t_anos} años", f"{d_acumulado_zn} µm", rec_recomendado
                    ]
                })
                st.table(df_resumen)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_resumen.to_excel(writer, index=False, sheet_name="PVH Offer Report")
                
                st.download_button(
                    label="📥 Descargar Informe en Excel",
                    data=buffer.getvalue(),
                    file_name=f"PVH_Report_{t_anos}yr_Lat{latitud}_Lon{longitud}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with st.expander("📚 Consultar Tablas de Referencia Comercial PVH"):
                t1, t2 = st.columns(2)
                with t1:
                    st.markdown("**Pregalvanizado (Z)**")
                    st.dataframe(pd.DataFrame(TABLA_PREGALVANIZADO), height=200)
                with t2:
                    st.markdown("**Magnelis® (ZM)**")
                    st.dataframe(pd.DataFrame(TABLA_MAGNELIS), height=200)

            with st.expander("🗺️ Ver Mapa de la Planta"):
                st.map(pd.DataFrame({"lat": [latitud], "lon": [longitud]}), zoom=6)
        else:
            st.error("❌ No se pudieron obtener los datos satelitales de la NASA para las coordenadas indicadas.")
