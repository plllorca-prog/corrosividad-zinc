import streamlit as st
import requests
import folium
import json
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Consulta ISO 9223 EDI - Mapa Público")

st.title("⚡ Consulta Directa de Corrosividad ISO 9223 (EDI Público)")
st.caption("Herramienta de consulta comparativa rápida usando los endpoints públicos de EDI.")

# IDs de las dos capas en EDI 
# (Atención: Si la versión pública usa IDs distintos en su Request URL, cámbialos aquí)
RASTER_LE_V4 = 436
RASTER_ZINC_ESTANDAR = 322

with st.sidebar:
    st.header("🔑 Autenticación EDI")
    st.info("Introduce el 'Session' y 'X-CSRFToken' obtenidos como invitado en el mapa público de EDI.")
    
    user_session = st.text_input("Cookie Session", type="password", help="Valor de la cookie 'session'").strip()
    user_csrftoken = st.text_input("X-CSRFToken", type="password", help="Valor del encabezado 'x-csrftoken'").strip()

if "lat" not in st.session_state:
    st.session_state.lat = 40.416700
if "lng" not in st.session_state:
    st.session_state.lng = -3.703700

col_inputs, col_mapa = st.columns([1.5, 2])

def consultar_raster(raster_id, lat, lng, session_cookie, csrf_token):
    # La URL de consulta a la API de EDI
    url = f"https://secure.engineeringdirector.com/api/aiq/parent_raster/{raster_id}/point_lookup"
    
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://secure.engineeringdirector.com",
        # REFERER ADAPTADO A LA VERSIÓN PÚBLICA PARA EVITAR EL BLOQUEO
        "referer": "https://secure.engineeringdirector.com/public/map/ISO9223_zinc_2020_2024_1km",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36",
        "x-csrftoken": csrf_token
    }
    cookies = {"session": session_cookie}
    payload = {"points": [{"latitude": float(lat), "longitude": float(lng)}]}
    
    try:
        response = requests.post(url, json=payload, headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 200:
            try:
                return response.json(), None
            except Exception:
                return None, f"Respuesta no válida del servidor: {response.text[:200]}"
        else:
            return None, f"Error HTTP {response.status_code}: Petición rechazada o tokens inválidos."
    except Exception as e:
        return None, str(e)

def extraer_datos_respuesta(res_data):
    if not res_data or "results" not in res_data or not res_data["results"]:
        return None, "N/A"
    first_res = res_data["results"][0]
    valor = first_res.get("value", None)
    categoria = "N/A"
    secondary = first_res.get("secondary_scoring", [])
    if secondary and isinstance(secondary, list):
        categoria = secondary[0].get("result", "N/A")
    return valor, f"C{categoria}" if categoria != "N/A" else "N/A"

with col_inputs:
    st.subheader("📍 Coordenadas Consulta")
    lat_input = st.number_input("Latitud", value=st.session_state.lat, format="%.6f", step=0.0001)
    lng_input = st.number_input("Longitud", value=st.session_state.lng, format="%.6f", step=0.0001)
    
    if st.button("🚀 Obtener Dato de Corrosión (Ambos Mapas)", type="primary", use_container_width=True):
        if not user_session or not user_csrftoken:
            st.error("⚠️ Debes ingresar tu 'Cookie Session' y 'X-CSRFToken' en la barra lateral.")
        else:
            st.session_state.lat = round(lat_input, 6)
            st.session_state.lng = round(lng_input, 6)
            
            with st.spinner("Consultando capas 436 y 322 en EDI..."):
                # Llamadas a la función consultar_raster con los parámetros correctos
                data_le, err_le = consultar_raster(
                    RASTER_LE_V4, st.session_state.lat, st.session_state.lng, user_session, user_csrftoken
                )
                data_std, err_std = consultar_raster(
                    RASTER_ZINC_ESTANDAR, st.session_state.lat, st.session_state.lng, user_session, user_csrftoken
                )
                
                st.session_state.resultado = {
                    "le_v4": data_le,
                    "err_le": err_le,
                    "estandar": data_std,
                    "err_std": err_std
                }

    st.divider()
    
    if "resultado" in st.session_state:
        st.subheader("📊 Resultados Comparativos")
        res_all = st.session_state.resultado
        
        val_le, cat_le = extraer_datos_respuesta(res_all.get("le_v4"))
        val_std, cat_std = extraer_datos_respuesta(res_all.get("estandar"))
        
        col_res1, col_res2 = st.columns(2)
        
        # --- COLUMNA 1: Local Emissions ---
        with col_res1:
            st.markdown("##### 🏬 Local Emissions (LE v4)")
            if val_le is not None:
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 12px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 10px;">
                        <span style="font-size: 13px; color: #555; font-weight: bold;">Tasa de Corrosión (r)</span><br>
                        <span style="font-size: 18px; font-weight: bold; color: #111;">{val_le:.3f} µm/año</span>
                    </div>
                    <div style="background-color: #f0f2f6; padding: 12px; border-radius: 8px; border-left: 5px solid #28a745;">
                        <span style="font-size: 13px; color: #555; font-weight: bold;">Categoría ISO 9223</span><br>
                        <span style="font-size: 18px; font-weight: bold; color: #111;">{cat_le}</span>
                    </div>
                    """, unsafe_allow_html=True
                )
            else:
                st.error(res_all.get("err_le", "Sin datos"))

        # --- COLUMNA 2: Zinc ISO Estándar ---
        with col_res2:
            st.markdown("##### 🌍 Zinc ISO Estándar")
            if val_std is not None:
                st.markdown(
                    f"""
                    <div style="background-color: #f0f2f6; padding: 12px; border-radius: 8px; border-left: 5px solid #0066cc; margin-bottom: 10px;">
                        <span style="font-size: 13px; color: #555; font-weight: bold;">Tasa de Corrosión (r)</span><br>
                        <span style="font-size: 18px; font-weight: bold; color: #111;">{val_std:.3f} µm/año</span>
                    </div>
                    <div style="background-color: #f0f2f6; padding: 12px; border-radius: 8px; border-left: 5px solid #28a745;">
                        <span style="font-size: 13px; color: #555; font-weight: bold;">Categoría ISO 9223</span><br>
                        <span style="font-size: 18px; font-weight: bold; color: #111;">{cat_std}</span>
                    </div>
                    """, unsafe_allow_html=True
                )
            else:
                st.error(res_all.get("err_std", "Sin datos"))

        st.write("")
        with st.expander("🔍 Ver respuestas JSON originales"):
            st.json(res_all)

with col_mapa:
    st.subheader("Ubicación Seleccionada")
    m = folium.Map(
        location=[st.session_state.lat, st.session_state.lng],
        zoom_start=11,
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Street Map"
    )
    folium.Marker([st.session_state.lat, st.session_state.lng], tooltip="Punto activo").add_to(m)
    map_data = st_folium(m, width="100%", height=400)

    if map_data and map_data.get("last_clicked"):
        click_lat = round(map_data["last_clicked"]["lat"], 6)
        click_lng = round(map_data["last_clicked"]["lng"], 6)
        if click_lat != st.session_state.lat or click_lng != st.session_state.lng:
            st.session_state.lat = click_lat
            st.session_state.lng = click_lng
            st.rerun()
