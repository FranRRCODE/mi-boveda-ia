import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import yfinance as yf
import hashlib
import random
from datetime import datetime

# --- CONFIGURACIÓN DE SUPABASE ---
# Uso de secretos de Streamlit (Más seguro)
URL_NUBE = st.secrets["sb_publishable_Dszp5pC1TZupO6Q0GLGBRQ_31f9F2mI"]
KEY_NUBE = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91eWFmZnF1aHZma3p3bHFsY29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NTUyNTU0MSwiZXhwIjoyMDkxMTAxNTQxfQ.YnkeUa-5f1QeETFmaPnr5GvB_Ni-vj9vdq2Ylx8VVys"]
supabase: Client = create_client(URL_NUBE, KEY_NUBE)

# --- CONFIGURACIÓN DE USUARIO ---
USUARIO_MASTER = "admin" 
PASSWORD_MASTER = "1234567899" # Cámbiala por tu contraseña real

def generar_hash(texto):
    return hashlib.sha256(str.encode(texto)).hexdigest()

# --- FUNCIONES DE UBICACIÓN ---
def obtener_geo():
    try:
        res = requests.get('https://ipapi.co/json/').json()
        return {"ciudad": res.get("city"), "pais": res.get("country_name"), "code": res.get("country"), "moneda": res.get("currency")}
    except:
        return {"ciudad": "Desconocida", "pais": "Global", "code": "US", "moneda": "USD"}

# --- LÓGICA DE IA ---
def analizar_ia_personalizado(desc, monto, geo):
    desc = desc.lower()
    hacks = {
        "starbucks": "☕ **Hack IA:** Gastar en café de marca reduce tu capacidad de inversión. Lleva termo propio.",
        "netflix": "📺 **Optimización:** Revisa si realmente usas este servicio a diario o cámbiate al plan con anuncios.",
        "uber": "🚗 **Movilidad:** Compara con Didi; las tarifas varían hasta un 20% en tu zona.",
        "doggis": "🌭 **Tip Chile:** Los miércoles hay promociones de 2x1 en la App.",
        "amazon": "📦 **Compra Online:** Usa comparadores de precios; evita las compras por impulso.",
        "supermercado": "🛒 **Súper:** Compra marcas blancas; ahorras un 30% en básicos.",
        "servicios sexuales": "⚠️ **Gestión Riesgo:** Gasto discrecional alto. Pon un tope mensual fijo."
    }
    for clave in hacks:
        if clave in desc:
            return hacks[clave]
    return f"🔍 **Análisis General:** Gasto en {geo['ciudad']}. Aplica la regla de las 48h antes de repetir este gasto."

# --- INTERFAZ LOGIN ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 IA Finance Secure</h1>", unsafe_allow_html=True)
    if 'c_n1' not in st.session_state:
        st.session_state.c_n1 = random.randint(1, 10)
        st.session_state.c_n2 = random.randint(1, 10)

    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        captcha = st.number_input(f"🤖 Captcha: {st.session_state.c_n1} + {st.session_state.c_n2}?", step=1)
        if st.form_submit_button("Entrar"):
            if captcha == (st.session_state.c_n1 + st.session_state.c_n2):
                if u == USUARIO_MASTER and p == PASSWORD_MASTER:
                    st.session_state.auth = True
                    st.rerun()
                else: st.error("Error de credenciales")
            else: st.error("Captcha incorrecto")

# --- APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"📍 {geo['ciudad']}")
    menu = st.sidebar.radio("Menú", ["➕ Registro", "🧠 IA Mentor", "📊 Datos"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    if menu == "➕ Registro":
        st.header("📥 Nuevo Movimiento (Nube)")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input(f"Monto ({geo['moneda']})", min_value=0.0)
            desc = st.text_input("Descripción")
            if st.form_submit_button("Guardar"):
                data = {"tipo": tipo, "categoria": cat, "monto": monto, "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais']}
                supabase.table("transacciones").insert(data).execute()
                st.success("Guardado en Nube")

    elif menu == "🧠 IA Mentor":
        st.header("🤖 Análisis IA")
        res = supabase.table("transacciones").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            for _, row in df[df['tipo'] == 'Gasto'].tail(10).iterrows():
                with st.expander(f"📌 {row['descripcion']} - ${row['monto']}"):
                    st.write(analizar_ia_personalizado(row['descripcion'], row['monto'], geo))
        else: st.info("Sin datos.")

    elif menu == "📊 Datos":
        st.header("Dashboard")
        res = supabase.table("transacciones").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            fig = px.pie(df[df['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.4)
            st.plotly_chart(fig)
            st.dataframe(df)

# --- CONTROLADOR ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    mostrar_login()
else:
    main()
