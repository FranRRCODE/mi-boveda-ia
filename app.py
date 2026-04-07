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
    st.error("⚠️ Configura los Secrets: SUPABASE_URL, SUPABASE_KEY y GEMINI_API_KEY.")
    st.stop()

# --- 2. UBICACIÓN POR IP REAL ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        res = requests.get(f"http://ip-api.com/json/{user_ip if user_ip else ''}").json()
        return {
            "ciudad": res.get("city", "Santiago"), 
            "moneda": "CLP" if res.get("countryCode") == "CL" else "USD",
            "pais": res.get("country", "Chile")
        }
    except:
        return {"ciudad": "Santiago", "moneda": "CLP", "pais": "Chile"}

# --- 3. BUSCADOR AUTOMÁTICO DE MODELOS (SOLUCIÓN AL 404) ---
def obtener_modelo_valido():
    """Busca en tu cuenta de Google qué modelo tienes permitido usar."""
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # Retornamos el nombre del modelo disponible (ej: models/gemini-1.5-flash)
                return m.name
    except:
        return None
    return None

def auditoria_ia_v4(row, total_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    ciudad = geo['ciudad']
    
    prompt = f"""
    Eres un Mentor Financiero 'Tiburón' en {ciudad}, Chile. 
    Analiza este gasto: "{desc}" por ${monto} CLP.
    
    INSTRUCCIONES:
    - Sé muy específico sobre Santiago. 
    - Menciona lugares REALES: La Vega Central, Lo Valledor, Mayorista 10, Alvi, ferias libres.
    - Compara precios: ¿Es caro para {ciudad}?
    - Da un plan de ahorro real.

    Responde ESTRICTAMENTE en JSON:
    {{
        "tipo": "Categoría",
        "veredicto": "Sarcasmo financiero",
        "analisis": "Análisis profundo para {ciudad}",
        "donde_ahorrar": "Lugares reales en Santiago (ej: Mayorista 10, Ferias)",
        "plan": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" o "green" o "orange"
    }}
    """

    modelo_nombre = obtener_modelo_valido()
    
    if not modelo_nombre:
        return {
            "tipo": "Error de API",
            "veredicto": "API Key sin permisos",
            "analisis": "Tu API Key no tiene modelos habilitados en Google AI Studio.",
            "donde_ahorrar": "📍 Hack: Anda a La Vega Central, es lo más barato de Santiago.",
            "plan": ["Revisa tu API Key", "Habilita Gemini 1.5 en AI Studio"],
            "color": "red"
        }

    try:
        model = genai.GenerativeModel(modelo_nombre)
        response = model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        return json.loads(match.group())
    except Exception as e:
        return {
            "tipo": "Gasto Registrado",
            "veredicto": "IA con Hipo",
            "analisis": f"Error detectado: {str(e)[:50]}",
            "donde_ahorrar": "📍 En Santiago: Prefiere siempre ferias libres de barrio antes que el super.",
            "plan": ["Comparar precios", "Usar efectivo en ferias"],
            "color": "orange"
        }

# --- 4. LOGIN CON CAPTCHA ---
def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Mentor Pro</h2>", unsafe_allow_html=True)
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)
    
    with st.container(border=True):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        cap = st.number_input(f"Captcha: {st.session_state.n1} + {st.session_state.n2}?", step=1)
        if st.button("Entrar", use_container_width=True):
            if u == "admin" and p == "1234567899" and cap == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Datos incorrectos.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

# --- 5. APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"🏠 Mentor: {geo['ciudad']}")
    st.sidebar.caption(f"📍 Detectado en **{geo['pais']}**")
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard"])

    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Registrar en {geo['ciudad']}")
        with st.form("f"):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Vivienda", "Ocio", "Otros"])
            monto = st.number_input("Monto (CLP)", min_value=0)
            desc = st.text_input("Descripción (Ej: Feria del sábado)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({"tipo": "Gasto", "categoria": cat, "monto": monto, "descripcion": desc, "ciudad": geo['ciudad'], "moneda": "CLP"}).execute()
                    st.success("Guardado.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA":
        st.header(f"🕵️ Auditoría Local: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            for _, row in df_g.head(8).iterrows():
                with st.spinner("IA analizando mercado chileno..."):
                    info = auditoria_ia_v4(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    c2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    st.write(info.get('analisis', 'Sin análisis.'))
                    st.markdown(f"**📍 Hacks para ahorrar en {geo['ciudad']}:**")
                    
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'Busca picadas locales.')
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    else: st.success(hack)
                    
                    st.markdown("**🚀 Plan de Acción:**")
                    for p in info.get('plan', []): st.write(f"- {p}")
        else:
            st.info("Sin gastos.")

    elif menu == "📊 Dashboard":
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: login()
else: main()
