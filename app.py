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

# --- 1. CONFIGURACIÓN ---
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    genai.configure(api_key=GEMINI_KEY)
except Exception as e:
    st.error("⚠️ Error en Secrets. Revisa SUPABASE y GEMINI_API_KEY.")
    st.stop()

# --- 2. UBICACIÓN POR IP ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        res = requests.get(f"http://ip-api.com/json/{user_ip}").json()
        return {"ciudad": res.get("city", "Santiago"), "moneda": "CLP" if res.get("countryCode") == "CL" else "USD"}
    except:
        return {"ciudad": "Santiago", "moneda": "CLP"}

# --- 3. MOTOR DE IA (CON DETECTOR DE ERRORES REAL) ---
def auditoria_ia_v3(row, total_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    
    # PROMPT MEJORADO PARA CHILE
    prompt = f"""
    Eres un Mentor Financiero experto en Santiago de Chile. 
    Analiza este gasto: "{desc}" por ${monto} CLP.
    
    Responde estrictamente en JSON:
    {{
        "tipo": "Categoría real",
        "veredicto": "Sarcasmo chileno sobre el gasto",
        "analisis": "Análisis profundo de por qué es caro o barato en Santiago",
        "donde_ahorrar": "Menciona tiendas reales como La Vega, Mayorista 10, Alvi o ferias de barrio en Santiago",
        "plan": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" o "green" o "orange"
    }}
    """

    # Intentamos con el modelo más estable del mundo: gemini-1.5-flash
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Limpieza de JSON
        texto_ia = response.text
        match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("La IA no respondió en formato JSON")

    except Exception as e:
        # SI FALLA, TE MOSTRARÁ EL ERROR REAL PARA QUE LO SOLUCIONEMOS
        return {
            "tipo": "ERROR DE CONEXIÓN IA",
            "veredicto": "El cerebro de Google está desconectado.",
            "analisis": f"DETALLE TÉCNICO: {str(e)}",
            "donde_ahorrar": "REVISA TU API KEY EN GOOGLE AI STUDIO. Asegúrate de que el modelo Gemini 1.5 esté activo.",
            "plan": ["Verificar API Key", "Revisar región de Streamlit", "Intentar más tarde"],
            "color": "red"
        }

# --- 4. LOGIN CON CAPTCHA ---
def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Bóveda IA Mentor</h2>", unsafe_allow_html=True)
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)
    
    with st.form("l"):
        u = st.text_input("Usuario")
        p = st.text_input("Clave", type="password")
        res_cap = st.number_input(f"Captcha: {st.session_state.n1} + {st.session_state.n2}?", step=1)
        if st.form_submit_button("Entrar"):
            if u == "admin" and p == "1234567899" and res_cap == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else: st.error("Error.")

# --- 5. APP ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"📍 Mentor en {geo['ciudad']}")
    
    menu = st.sidebar.radio("Menú", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard"])

    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Gasto en {geo['ciudad']}")
        with st.form("r", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Ocio", "Vivienda", "Otros"])
            monto = st.number_input("Monto", min_value=0)
            desc = st.text_input("Descripción (Ej: Compras en el Lider)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({"tipo": "Gasto", "categoria": cat, "monto": monto, "descripcion": desc, "ciudad": geo['ciudad'], "moneda": geo['moneda']}).execute()
                    st.success("Guardado.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA":
        st.header(f"🕵️ Auditoría Real: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            for _, row in df_g.head(5).iterrows():
                with st.spinner("Conectando con la IA..."):
                    info = auditoria_ia_v3(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    st.subheader(f"🏷️ {info['tipo']}")
                    st.markdown(f"**Veredicto:** {info['veredicto']}")
                    st.write(info['analisis'])
                    
                    st.info(f"📍 **DÓNDE AHORRAR EN SANTIAGO:** \n\n {info['donde_ahorrar']}")
                    
                    st.markdown("**🚀 PLAN DE ACCIÓN:**")
                    for p in info['plan']: st.write(f"- {p}")
        else: st.info("Sin datos.")

    elif menu == "📊 Dashboard":
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.4))

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: login()
else: main()
