import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Consulta Directa ISO 9223 EDI")

st.title("⚡ Consulta Directa de Corrosividad ISO 9223")
st.caption("Herramienta de consulta rápida para el equipo vía API de EDI.")

# Configuración en la barra lateral para autenticación individual
with st.sidebar:
    st.header("🔑 Autenticación EDI")
    st.caption("Introduce tus credenciales de sesión obtenidas desde DevTools (F12).")
    
    user_session = st.text_input("Cookie Session", type="password", help="Valor completo de la cookie 'session'").strip()
    user_csrftoken = st.text_input("X-CSRFToken", type="password", help="Valor del encabezado 'x-csrftoken'").strip()
    
    st.info("💡 Cada usuario debe usar sus propias credenciales activas en la web de EDI.")

if "lat" not in st.session_state:
    st.session_state.lat = 40.416700
if "lng" not in st.session_state:
    st.session_state.lng = -3.703700

col_inputs, col_mapa = st.columns([1, 2.2])

def obtener_corrosion_api(lat, lng, session_cookie, csrf_token):
    url = "https://secure.engineeringdirector.com/api/aiq/parent_raster/322/point_lookup"
    
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://secure.engineeringdirector.com",
        "referer": "https://secure.engineeringdirector.com/map/ISO9223_zinc_2020_2024_1km",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
        "x-csrftoken": csrf_token
    }
    
    cookies = {
        "session": session_cookie
    }
    
    payload = {
        "points": [
            {
                "latitude": float(lat),
                "longitude": float(lng)
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 200:
            try:
                return response.json(), None
            except Exception:
                return None, f"Respuesta no válida del servidor: {response.text[:200]}"
        else:
            return None, f"Error HTTP {response.status_code}: Token o Sesión caducados. Vuelve a copiar las claves de F12."
    except Exception as e:
        return None, str(e)

with col_inputs:
    st.subheader("📍 Coordenadas Consulta")
    
    lat_input = st.number_input("Latitud", value=st.session_state.lat, format="%.6f", step=0.0001)
    lng_input = st.number_input("Longitud", value=st.session_state.lng, format="%.6f", step=0.0001)
    
    if st.button("🚀 Obtener Dato de Corrosión", type="primary", use_container_width=True):
        if not user_session or not user_csrftoken:
            st.error("⚠️ Debes ingresar tu 'Cookie Session' y 'X-CSRFToken' en la barra lateral para realizar consultas.")
        else:
            st.session_state.lat = round(lat_input, 6)
            st.session_state.lng = round(lng_input, 6)
            
            with st.spinner("Consultando API de EDI..."):
                data, err = obtener_corrosion_api(
                    st.session_state.lat, 
                    st.session_state.lng, 
                    user_session, 
                    user_csrftoken
                )
                if err:
                    st.error(err)
                else:
                    st.session_state.resultado = data

    st.divider()
    
    if "resultado" in st.session_state:
        st.subheader("📊 Resultado Obtenido")
        st.json(st.session_state.resultado)

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
