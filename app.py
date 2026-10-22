import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Consulta ISO 9223 EDI - 100% Automática")

st.title("⚡ Consulta Directa de Corrosividad ISO 9223")
st.caption("Conexión automatizada a la versión pública de EDI. No requiere credenciales.")

# URLs e IDs de los mapas
URL_PUBLICA = "https://secure.engineeringdirector.com/public/map/ISO9223_zinc_2020_2024_1km"
RASTER_LE_V4 = 436
RASTER_ZINC_ESTANDAR = 322

if "lat" not in st.session_state:
    st.session_state.lat = 40.416700
if "lng" not in st.session_state:
    st.session_state.lng = -3.703700

def consultar_ambas_capas_automatico(lat, lng):
    sesion = requests.Session()
    headers_get = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # 1. Extraer tokens frescos automáticamente haciendo una petición a la web pública
    try:
        res_get = sesion.get(URL_PUBLICA, headers=headers_get, timeout=10)
        cookie_session = sesion.cookies.get("session")
        html = res_get.text
        # Cortamos el texto del HTML para aislar el csrf-token
        csrf_token = html.split('name="csrf-token"')[1].split('content="')[1].split('"')[0]
    except Exception as e:
        return None, f"Fallo al conectar con EDI (Tokens): {str(e)}"

    if not cookie_session or not csrf_token:
        return None, "No se pudo generar el token de invitado. El servidor de EDI no responde."

    # 2. Hacer las consultas a los mapas con los tokens recién robados
    headers_post = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://secure.engineeringdirector.com",
        "referer": URL_PUBLICA,
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "x-csrftoken": csrf_token
    }
    payload = {"points": [{"latitude": float(lat), "longitude": float(lng)}]}
    
    resultados = {}
    
    # Capa Local Emissions
    try:
        url_le = f"https://secure.engineeringdirector.com/api/aiq/parent_raster/{RASTER_LE_V4}/point_lookup"
        r_le = sesion.post(url_le, json=payload, headers=headers_post, timeout=10)
        if r_le.status_code == 200:
            resultados["le_v4"] = r_le.json()
        else:
            resultados["err_le"] = f"Error {r_le.status_code}: Token caducado o ID inválido."
    except Exception as e:
        resultados["err_le"] = str(e)

    # Capa Zinc ISO Estándar
    try:
        url_std = f"https://secure.engineeringdirector.com/api/aiq/parent_raster/{RASTER_ZINC_ESTANDAR}/point_lookup"
        r_std = sesion.post(url_std, json=payload, headers=headers_post, timeout=10)
        if r_std.status_code == 200:
            resultados["estandar"] = r_std.json()
        else:
            resultados["err_std"] = f"Error {r_std.status_code}: Token caducado o ID inválido."
    except Exception as e:
        resultados["err_std"] = str(e)
        
    return resultados, None

def extraer_datos_respuesta(res_data):
    if not res_data or not isinstance(res_data, dict) or "results" not in res_data or not res_data["results"]:
        return None, "N/A"
    first_res = res_data["results"][0]
    valor = first_res.get("value", None)
    categoria = "N/A"
    secondary = first_res.get("secondary_scoring", [])
    if secondary and isinstance(secondary, list):
        categoria = secondary[0].get("result", "N/A")
    return valor, f"C{categoria}" if categoria != "N/A" else "N/A"

col_inputs, col_mapa = st.columns([1.5, 2])

with col_inputs:
    st.subheader("📍 Coordenadas Consulta")
    lat_input = st.number_input("Latitud", value=st.session_state.lat, format="%.6f", step=0.0001)
    lng_input = st.number_input("Longitud", value=st.session_state.lng, format="%.6f", step=0.0001)
    
    if st.button("🚀 Obtener Dato de Corrosión", type="primary", use_container_width=True):
        st.session_state.lat = round(lat_input, 6)
        st.session_state.lng = round(lng_input, 6)
        
        with st.spinner("Conectando con EDI de forma automática..."):
            datos, error_fatal = consultar_ambas_capas_automatico(st.session_state.lat, st.session_state.lng)
            
            if error_fatal:
                st.error(error_fatal)
            else:
                st.session_state.resultado = datos

    st.divider()
    
    if "resultado" in st.session_state:
        st.subheader("📊 Resultados Comparativos")
        res_all = st.session_state.resultado
        
        val_le, cat_le = extraer_datos_respuesta(res_all.get("le_v4"))
        val_std, cat_std = extraer_datos_respuesta(res_all.get("estandar"))
        
        col_res1, col_res2 = st.columns(2)
        
        # --- Local Emissions ---
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
                st.error(res_all.get("err_le", "Sin datos o servidor bloqueado."))

        # --- Zinc ISO Estándar ---
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
                st.error(res_all.get("err_std", "Sin datos o servidor bloqueado."))

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
