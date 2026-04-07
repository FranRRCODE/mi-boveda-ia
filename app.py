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

# --- 1. CONFIGURACIÓN INICIAL (DEBE SER LO PRIMERO) ---
st.set_page_config(page_title="Bóveda IA Mentor", page_icon="🔐")

def cargar_config():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        g_key = st.secrets["GEMINI_API_KEY"]
        sb = create_client(url, key)
        genai.configure(api_key=g_key)
        return sb
    except Exception as e:
        st.error(f"Error en Secrets: {e}")
        st.stop()

supabase = cargar_config()

# --- 2. UBICACIÓN POR IP (PARA SANTIAGO) ---
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
def auditoria_ia(row, total_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    ciudad = geo['ciudad']
    
    prompt = f"""
    Eres un Mentor Financiero experto en la economía de {ciudad}, Chile. 
    Analiza este gasto: "{desc}" por ${monto} CLP.
    
    INSTRUCCIONES:
    - Evalúa si el precio es bueno para {ciudad}.
    - Menciona tiendas reales de Santiago: La Vega, Mayorista 10, Alvi, ferias libres.
    - Da un plan de ahorro real.

    Responde ESTRICTAMENTE en JSON:
    {{
        "tipo": "Categoría",
        "veredicto": "Sarcasmo financiero",
        "analisis": "Análisis profundo",
        "donde_ahorrar": "Lugares reales en Santiago",
        "plan": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" o "green" o "orange"
    }}
    """
    
    try:
        # Intentamos con 1.5 flash, si da 404 el sistema usará el fallback manual
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("No JSON")
    except Exception as e:
        # FALLBACK MANUAL (CONSEJOS REALES DE SANTIAGO SI LA IA FALLA)
        return {
            "tipo": "Análisis Local",
            "veredicto": "Mentoría Santiago",
            "analisis": f"Registraste ${monto} en {desc}. (IA Offline)",
            "donde_ahorrar": "📍 En Santiago: Frutas y verduras siempre en La Vega Central. Abarrotes en Mayorista 10 o Alvi. Evita el Jumbo si buscas ahorrar.",
            "plan": ["Comprar en ferias libres", "Usa marcas propias Lider/Acuenta", "Planifica la semana"],
            "color": "blue"
        }

# --- 4. LOGIN CON CAPTCHA ---
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
                st.error("Credenciales incorrectas.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

# --- 5. APLICACIÓN PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard"])

    # Cargar datos de Supabase
    try:
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
    except:
        df = pd.DataFrame()

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Gasto en {geo['ciudad']}")
        with st.form("form_reg", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Vivienda", "Ocio", "Otros"])
            monto = st.number_input("Monto (CLP)", min_value=0)
            desc = st.text_input("Descripción (Ej: Feria del domingo)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    # LÍNEA CORREGIDA ABAJO:
                    supabase.table("transacciones").insert({"tipo": "Gasto", "categoria": cat, "monto": monto, "descripcion": desc, "ciudad": geo['ciudad'], "moneda": "CLP"}).execute()
                    st.success("✅ Guardado.")
                    time.sleep(1)
                    st.rerun()

    elif menu == "🧠 Auditoría IA":
        st.header(f"🕵️ Auditoría Experta: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Soy tu mentor de **{geo['ciudad']}**. Analicemos:")
            
            for _, row in df_g.head(5).iterrows():
                with st.spinner("Analizando..."):
                    info = auditoria_ia(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    c2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    st.write(info.get('analisis', 'Sin análisis.'))
                    st.markdown(f"**📍 Hacks para {geo['ciudad']}:**")
                    
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'Busca picadas.')
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    else: st.success(hack)
                    
                    st.markdown("**🚀 Plan de Acción:**")
                    for p in info.get('plan', ["Comparar precios"]): 
                        st.write(f"- {p}")
        else:
            st.info("Sin gastos registrados.")

    elif menu == "📊 Dashboard":
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))

# --- CONTROL ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    login()
else:
    main()
