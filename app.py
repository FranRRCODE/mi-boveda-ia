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
        st.error(f"Configuración fallida: {e}")
        st.stop()

supabase = cargar_config()

# --- 2. UBICACIÓN POR IP (MÉTODO ULTRA-ESTABLE) ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        # Usamos una API simple para obtener la IP del usuario
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
        "analisis": "Análisis profundo para {ciudad}",
        "donde_ahorrar": "Lugares reales en Santiago (ej: Mayorista 10, Ferias)",
        "plan": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" o "green" o "orange"
    }}
    """
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        # Extraer JSON con Regex para evitar errores de texto extra
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("No se encontró JSON")
    except Exception as e:
        # FALLBACK: Si la IA falla, usamos lógica manual experta en Santiago
        return {
            "tipo": "Gasto Registrado",
            "veredicto": "Mentoría offline",
            "analisis": f"Registraste ${monto} en {desc}. Error IA: {str(e)[:30]}",
            "donde_ahorrar": f"📍 En {ciudad}: Anda a La Vega Central si es comida o usa el Mayorista 10 para abarrotes.",
            "plan": ["Comparar precios en ferias", "Usar marcas de cadena (Lider/Acuenta)"],
            "color": "blue"
        }

# --- 4. SEGURIDAD: LOGIN CON CAPTCHA ---
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
    st.sidebar.info(f"📍 Detectado en **{geo['pais']}**")
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard"])

    # Cargar datos
    try:
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
    except:
        df = pd.DataFrame()

    if menu == "➕ Registro":
        st.header(f"📥 Registrar Gasto en {geo['ciudad']}")
        with st.form("form_reg", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Vivienda", "Ocio", "Otros"])
            monto = st.number_input("Monto (CLP)", min_value=0)
            desc = st.text_input("Descripción (Ej: Compras en el Lider)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": "Gasto", "categoria": cat, "monto": monto, 
                        "descripcion": desc, "ciudad": geo['ciudad'], "moneda": "CLP
