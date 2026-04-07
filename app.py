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

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Bóveda IA Mentor", page_icon="🔐", layout="wide")

def inicializar_ia():
    try:
        URL_NUBE = st.secrets["SUPABASE_URL"]
        KEY_NUBE = st.secrets["SUPABASE_KEY"]
        GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
        
        sb = create_client(URL_NUBE, KEY_NUBE)
        genai.configure(api_key=GEMINI_KEY)
        
        # BUSCADOR AUTOMÁTICO DE MODELO
        # Intentamos encontrar el modelo 1.5 flash, si no el pro, si no el primero disponible.
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        modelo_final = "gemini-1.5-flash" # Default
        for m in ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]:
            if m in modelos_disponibles:
                modelo_final = m
                break
        
        return sb, genai.GenerativeModel(modelo_final)
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        st.stop()

supabase, model_ai = inicializar_ia()

# --- 2. UBICACIÓN POR IP REAL ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        res = requests.get("https://ipapi.co/json/").json()
        return {
            "ciudad": res.get("city", "Santiago"),
            "pais": res.get("country_name", "Chile"),
            "moneda": "CLP" if res.get("country") == "CL" else "USD"
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP"}

# --- 3. MOTOR DE IA (SANTIAGO EXPERT) ---
def auditoria_ia_pro(row, total_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    ciudad = geo['ciudad']
    
    prompt = f"""
    Eres un Mentor Financiero experto en Santiago de Chile. 
    Analiza este gasto: "{desc}" por ${monto} CLP.
    
    INSTRUCCIONES:
    - Evalúa el precio para Santiago.
    - Menciona lugares REALES: La Vega Central, Lo Valledor, Mayorista 10, Alvi, ferias de barrio.
    - Da un plan de ahorro real de 3 pasos.

    Responde ESTRICTAMENTE en JSON:
    {{
        "tipo": "Categoría",
        "veredicto": "Sarcasmo chileno",
        "analisis": "Análisis profundo",
        "donde_ahorrar": "Lista de lugares REALES en Santiago",
        "plan": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" o "green" o "orange"
    }}
    """
    
    try:
        response = model_ai.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else: raise ValueError()
    except:
        # MENTOR MANUAL DE EMERGENCIA
        return {
            "tipo": "Análisis Local",
            "veredicto": "Economía Santiago",
            "analisis": f"Registraste ${monto} en {desc}.",
            "donde_ahorrar": "📍 En Santiago: Frutas y verduras en La Vega Central. Abarrotes en Mayorista 10 o Alvi. Usa marcas propias como Líder o Acuenta.",
            "plan": ["Ir a la feria el domingo", "Comparar precios en apps", "Planificar compras"],
            "color": "blue"
        }

# --- 4. SEGURIDAD: LOGIN ---
def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Mentor Pro</h2>", unsafe_allow_html=True)
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)
    
    with st.container(border=True):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        cap = st.number_input(f"Captcha: {st.session_state.n1} + {st.session_state.n2}?", step=1, value=0)
        
        if st.button("Ingresar", use_container_width=True):
            if u == "admin" and p == "1234567899" and cap == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Error de acceso.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

# --- 5. APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard"])

    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Registro ({geo['ciudad']})")
        with st.form("reg", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Vivienda", "Ocio", "Otros"])
            monto = st.number_input("Monto (CLP)", min_value=0)
            desc = st.text_input("¿Qué compraste? (Ej: Carne en el Lider)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": "Gasto", "categoria": cat, "monto": monto, 
                        "descripcion": desc, "ciudad": geo['ciudad'], "moneda": "CLP"
                    }).execute()
                    st.success("✅ Guardado.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA":
        st.header(f"🕵️ Auditoría Experta: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Soy tu mentor de **{geo['ciudad']}**. Analicemos tus gastos locales:")
            
            for _, row in df_g.head(8).iterrows():
                with st.spinner("IA analizando mercado chileno..."):
                    info = auditoria_ia_pro(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    c2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    st.write(info.get('analisis', '...'))
                    st.markdown(f"**📍 Hack en {geo['ciudad']}:**")
                    
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'Busca picadas.')
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    else: st.success(hack)
                    
                    st.markdown("**🚀 Plan de Acción:**")
                    for p in info.get('plan', ["Comparar precios"]): st.write(f"- {p}")
        else:
            st.info("Sin gastos registrados.")

    elif menu == "📊 Dashboard":
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: login()
else: main()
