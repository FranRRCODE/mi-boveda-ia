import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import random
import time
import google.generativeai as genai
import json
import re

# --- 1. CONFIGURACIÓN DE NUBE Y IA ---
try:
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("⚠️ Falta GEMINI_API_KEY en los Secrets.")
        st.stop()

    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    genai.configure(api_key=GEMINI_KEY)
    
except Exception as e:
    st.error(f"❌ Error de inicio: {e}")
    st.stop()

# --- 2. UBICACIÓN REAL POR IP (DETECTA TU CIUDAD Y MONEDA) ---
@st.cache_data(ttl=3600)
def obtener_geo_real():
    try:
        # Extraer IP real del usuario tras el proxy de Streamlit
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        
        # Consultar API de geolocalización
        url_geo = f"http://ip-api.com/json/{user_ip}" if user_ip else "http://ip-api.com/json/"
        res = requests.get(url_geo).json()
        
        ciudad = res.get("city", "Santiago")
        pais_code = res.get("countryCode", "CL")
        
        # Mapeo inteligente de monedas
        monedas_map = {
            "CL": "CLP", "MX": "MXN", "CO": "COP", "AR": "ARS", 
            "ES": "EUR", "US": "USD", "PE": "PEN", "BR": "BRL"
        }
        
        return {
            "ciudad": ciudad,
            "pais": res.get("country", "Chile"),
            "moneda": monedas_map.get(pais_code, "USD"),
            "ip": res.get("query", "0.0.0.0")
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP", "ip": "Desconocida"}

# --- 3. MOTOR DE IA CON AUTO-RECUPERACIÓN (FIX 404) ---
def auditoria_ia_local(row, total_gastos_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    prompt = f"""
    Eres un Mentor Financiero experto en {geo['ciudad']}, {geo['pais']}.
    Gasto: "{desc}" | Monto: {moneda} {monto} | Impacto: {impacto:.1f}%.

    Responde ESTRICTAMENTE en formato JSON plano:
    {{
        "tipo": "Categoría",
        "analisis": "Análisis corto y real",
        "hack_local": "Menciona tiendas, ferias o apps reales en {geo['ciudad']} para ahorrar en esto",
        "color": "red", "green", "orange" o "blue"
    }}
    """

    # Intentar con varios modelos para evitar el error 404
    modelos_a_probar = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
    
    for nombre_modelo in modelos_a_probar:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception:
            continue # Si falla, prueba el siguiente modelo
            
    # Si todos fallan, fallback manual
    return {
        "tipo": "Gasto Registrado",
        "analisis": f"Registraste un gasto en {geo['ciudad']}.",
        "hack_local": f"En {geo['ciudad']} busca siempre ferias locales para ahorrar.",
        "color": "blue"
    }

# --- 4. SEGURIDAD: LOGIN CON CAPTCHA DINÁMICO ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Bóveda IA Mentor Pro</h1>", unsafe_allow_html=True)
    
    if 'n1' not in st.session_state:
        st.session_state.n1 = random.randint(1, 10)
        st.session_state.n2 = random.randint(1, 10)

    with st.container(border=True):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        
        # CAPTCHA
        st.write(f"**Verificación:** ¿Cuánto es {st.session_state.n1} + {st.session_state.n2}?")
        res_usuario = st.number_input("Tu respuesta:", step=1, value=0)
        
        if st.button("Ingresar al Sistema", use_container_width=True):
            if u == "admin" and p == "1234567899" and res_usuario == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Credenciales o Captcha incorrectos.")
                # Refrescar captcha tras error
                st.session_state.n1 = random.randint(1, 10)
                st.session_state.n2 = random.randint(1, 10)

# --- 5. APP PRINCIPAL ---
def main():
    geo = obtener_geo_real()
    
    # Sidebar Informativa
    st.sidebar.title(f"🏠 Mentor: {geo['ciudad']}")
    st.sidebar.markdown(f"**País:** {geo['pais']} | **IP:** {geo['ip']}")
    
    moneda_selec = st.sidebar.selectbox(
        "Moneda:", 
        ["CLP", "USD", "MXN", "EUR", "COP", "PEN"], 
        index=["CLP", "USD", "MXN", "EUR", "COP", "PEN"].index(geo['moneda']) if geo['moneda'] in ["CLP", "USD", "MXN", "EUR", "COP", "PEN"] else 0
    )
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA Local", "📊 Dashboard"])

    # Cargar datos desde Supabase
    try:
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
    except:
        df = pd.DataFrame()

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Gasto en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Otros"])
            monto = st.number_input(f"Monto ({moneda_selec})", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Feria de los domingos)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.success("✅ Datos guardados.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA Local":
        st.header(f"🕵️ Auditoría Especializada: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Hola, he analizado tus gastos según la economía local de **{geo['ciudad']}**:")
            
            for _, row in df_g.head(10).iterrows():
                with st.spinner(f"Consultando ofertas en {geo['ciudad']}..."):
                    info = auditoria_ia_local(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - {row['moneda']} {row['monto']:,.0f}"):
                    st.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    st.write(info.get('analisis', 'Análisis breve disponible.'))
                    
                    st.markdown(f"**📍 Hack Local en {geo['ciudad']}:**")
                    color = info.get('color', 'blue')
                    hack = info.get('hack_local', 'Busca precios en comercios de barrio.')
                    
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    elif color == "green": st.success(hack)
                    else: st.info(hack)
        else:
            st.info("No hay gastos registrados.")

    elif menu == "📊 Dashboard":
        st.header("📊 Resumen de Gastos")
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))
            st.dataframe(df, use_container_width=True)

# --- CONTROL DE SESIÓN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    mostrar_login()
else:
    main()
