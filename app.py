import streamlit as st
import requests
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide", page_title="Consulta Directa ISO 9223 EDI")

st.title("⚡ Consulta Directa de Corrosividad ISO 9223 (Local Emissions LE v4)")
st.caption("Herramienta de consulta rápida para el equipo vía API de EDI - Capa LE v4 (Raster 436).")

with st.sidebar:
    st.header("🔑 Autenticación EDI")
    with st.expander("❓ ¿Cómo obtener tus credenciales?", expanded=False):
        st.markdown("""
        **Pasos en la web de EDI:**
        1. Entra en [EDI](https://secure.engineeringdirector.com/).
        2. En el menú lateral ve a **Lithosphere** > **Additional Maps**.
        3. Desplázate hacia abajo y selecciona el mapa:  
           **`ISO 9223 Zinc Corrosion Rate - Local Emissions (LE v4)`**.
        4. Abre DevTools en tu navegador (**F12**).
        5. Ve a la pestaña **Network** (Red) y haz un clic en cualquier punto del mapa.
        6. Busca la petición llamada **`point_lookup`**.
        7. En los encabezados (*Request Headers*):
           - Copia el texto tras `session=` en **Cookie Session**.
           - Copia el valor de `x-csrftoken` en **X-CSRFToken**.
        """)

    user_session = st.text_input("Cookie Session", type="password", help="Valor de la cookie 'session'").strip()
    user_csrftoken = st.text_input("X-CSRFToken", type="password", help="Valor del encabezado 'x-csrftoken'").strip()
    st.info("💡 Cada usuario debe usar sus propias credenciales activas en la web de EDI.")
if "lat" not in st.session_state:
    st.session_state.lat = 40.416700
if "lng" not in st.session_state:
    st.session_state.lng = -3.703700

col_inputs, col_mapa = st.columns([1.5, 2])

def obtener_corrosion_api(lat, lng, session_cookie, csrf_token):
    # Endpoint fijado a la capa 436 (Local Emissions LE v4)
    url = "https://secure.engineeringdirector.com/api/aiq/parent_raster/436/point_lookup"
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "origin": "https://secure.engineeringdirector.com",
        "referer": "https://secure.engineeringdirector.com/map/ISO9223_zinc_local_emissions_v4",
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
            with st.spinner("Consultando API de EDI (Capa 436 - LE v4)..."):
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
        res_data = st.session_state.resultado
        try:
            results_list = res_data.get("results", [])
            units = res_data.get("units", "µm/yr")
            if results_list:
                first_res = results_list[0]
                valor = first_res.get("value", None)
                categoria = "N/A"
                secondary = first_res.get("secondary_scoring", [])
                if secondary and isinstance(secondary, list):
                    categoria = secondary[0].get("result", "N/A")
                
                val_str = f"{valor:.3f} {units}" if valor is not None else "N/A"
                cat_str = f"C{categoria}" if categoria != "N/A" else "N/A"
                
                m1, m2 = st.columns(2)
                with m1:
                    st.markdown(
                        f"""
Tasa de Corrosión


{val_str}

                        """,
                        unsafe_allow_html=True
                    )
                with m2:
                    st.markdown(
                        f"""

Categoría ISO 9223


{cat_str}

                        """,
                        unsafe_allow_html=True
                    )
            else:
                st.warning("No se encontraron resultados para esta ubicación.")
            st.write("")
            with st.expander("🔍 Ver respuesta JSON original"):
                st.json(res_data)
        except Exception:
            st.json(res_data)

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
