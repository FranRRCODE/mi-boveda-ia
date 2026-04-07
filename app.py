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

# --- 1. CONFIGURACIÓN DE SEGURIDAD Y NUBE ---
try:
    # Verificamos si las llaves existen antes de intentar usarlas
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ No encontré 'GEMINI_API_KEY' en tus Secrets de Streamlit.")
        st.stop()
        
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    # Inicializar Clientes
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
except Exception as e:
    st.error(f"❌ Error al cargar configuraciones: {e}")
    st.stop()

# --- 2. UBICACIÓN REAL POR IP ---
@st.cache_data(ttl=3600)
def obtener_geo_real():
    try:
        # Detectar IP real tras proxy
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        res = requests.get(f"http://ip-api.com/json/{user_ip if user_ip else ''}").json()
        
        pais_code = res.get("countryCode", "CL")
        monedas = {"CL": "CLP", "MX": "MXN", "CO": "COP", "AR": "ARS", "ES": "EUR", "US": "USD", "PE": "PEN"}
        
        return {
            "ciudad": res.get("city", "Santiago"),
            "pais": res.get("country", "Chile"),
            "moneda": monedas.get(pais_code, "CLP"),
            "ip": res.get("query", "0.0.0.0")
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP", "ip": "Error IP"}

# --- 3. MOTOR DE IA CON HACKS LOCALES ---
def auditoria_ia_local(row, total_gastos_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    prompt = f"""
    Eres un Mentor Financiero sarcástico en {geo['ciudad']}, {geo['pais']}.
    Analiza: "{desc}" por {moneda} {monto}. Impacto: {impacto:.1f}%.

    Responde ESTRICTAMENTE en JSON con:
    {{
        "tipo": "Categoría",
        "analisis": "Análisis corto",
        "hack_local": "Menciona lugares específicos como Ferias Libres, Lider, Mayorista 10 o apps como Tuu, si estás en {geo['ciudad']}",
        "color": "red" o "green" o "orange" o "blue"
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Extraer JSON
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else: raise ValueError("Respuesta no es JSON")
    except Exception as e:
        # Si la API falla por la llave, esto te lo dirá
        return {
            "tipo": "Error de Conexión",
            "analisis": "La IA no responde.",
            "hack_local": f"⚠️ Error: {str(e)}. Revisa tu API KEY en Google AI Studio.",
            "color": "red"
        }

# --- 4. LOGIN CON CAPTCHA ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Bóveda IA Mentor Pro</h1>", unsafe_allow_html=True)
    
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

    with st.form("login_form"):
        u = st.text_input("Usuario Master")
        p = st.text_input("Contraseña", type="password")
        captcha = st.number_input(f"Captcha: {st.session_state.n1} + {st.session_state.n2}?", step=1)
        
        if st.form_submit_button("Acceder"):
            if u == "admin" and p == "1234567899" and captcha == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Error: Revisa usuario, clave o captcha.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

# --- 5. MAIN APP ---
def main():
    geo = obtener_geo_real()
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    st.sidebar.caption(f"📍 IP Detectada: {geo['ip']}")
    
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR", "COP", "PEN"], index=0 if geo['moneda']=="CLP" else 1)
    
    menu = st.sidebar.radio("Menú", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard"])

    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Registro en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Otros"])
            monto = st.number_input(f"Monto ({moneda_selec})", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Supermercado Lider)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({"tipo": tipo, "categoria": cat, "monto": float(monto), "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais'], "moneda": moneda_selec}).execute()
                    st.success("✅ Guardado.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA":
        st.header(f"🕵️ Análisis para {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            for _, row in df_g.head(5).iterrows():
                with st.spinner("Gemini analizando..."):
                    info = auditoria_ia_local(row, total, geo)
                with st.expander(f"🔍 {row['descripcion']} - {row['moneda']} {row['monto']:,.0f}"):
                    st.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    st.write(info.get('analisis', 'Sin análisis.'))
                    st.markdown(f"**📍 Hack para {geo['ciudad']}:**")
                    color = info.get('color', 'blue')
                    hack = info.get('hack_local', 'No hay datos.')
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    elif color == "green": st.success(hack)
                    else: st.info(hack)
        else:
            st.info("Registra un gasto primero.")

    elif menu == "📊 Dashboard":
        st.header("📊 Resumen")
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))

# --- FLUJO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
