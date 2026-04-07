import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import yfinance as yf
import hashlib
import random
from datetime import datetime

# --- CONFIGURACIÓN DE NUBE (SEGURA) ---
# He cambiado los nombres para que coincidan exactamente con lo que usaremos en Secrets
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
except Exception as e:
    st.error("Error de configuración: No se encontraron las llaves en los Secrets de Streamlit.")
    st.stop()

# --- CONFIGURACIÓN DE USUARIO ---
USUARIO_MASTER = "admin" 
PASSWORD_MASTER = "1234567899" # Asegúrate de que esta sea la que quieras usar

# --- FUNCIONES DE UBICACIÓN ---
def obtener_geo():
    try:
        res = requests.get('https://ipapi.co/json/').json()
        return {
            "ciudad": res.get("city", "Desconocida"), 
            "pais": res.get("country_name", "Global"), 
            "code": res.get("country", "US"), 
            "moneda": res.get("currency", "USD")
        }
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
    return f"🔍 **Análisis General:** Gasto detectado en {geo['ciudad']}. Aplica la regla de las 48h antes de repetir este gasto."

# --- INTERFAZ LOGIN ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 IA Finance Secure</h1>", unsafe_allow_html=True)
    
    # Inicializar captcha si no existe
    if 'c_n1' not in st.session_state:
        st.session_state.c_n1 = random.randint(1, 10)
        st.session_state.c_n2 = random.randint(1, 10)

    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        captcha = st.number_input(f"🤖 Captcha: ¿Cuánto es {st.session_state.c_n1} + {st.session_state.c_n2}?", step=1)
        
        if st.form_submit_button("Entrar"):
            if captcha == (st.session_state.c_n1 + st.session_state.c_n2):
                if u == USUARIO_MASTER and p == PASSWORD_MASTER:
                    st.session_state.auth = True
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
            else:
                st.error("Captcha incorrecto. Intenta de nuevo.")
                # Resetear captcha tras error
                st.session_state.c_n1 = random.randint(1, 10)
                st.session_state.c_n2 = random.randint(1, 10)

# --- APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"📍 {geo['ciudad']}")
    
    # Mostrar el dólar si estamos en Chile o Latam
    try:
        if geo['code'] == "CL":
            dolar = yf.Ticker("USDCLP=X").history(period="1d")['Close'].iloc[-1]
            st.sidebar.metric("Dólar (CLP)", f"${dolar:.2f}")
    except:
        pass

    menu = st.sidebar.radio("Menú", ["➕ Registro", "🧠 IA Mentor", "📊 Datos"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    if menu == "➕ Registro":
        st.header("📥 Nuevo Movimiento (Nube)")
        with st.form("reg_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input(f"Monto ({geo['moneda']})", min_value=0.0)
            desc = st.text_input("Descripción específica")
            if st.form_submit_button("Guardar en Nube"):
                if desc and monto > 0:
                    data = {
                        "tipo": tipo, 
                        "categoria": cat, 
                        "monto": float(monto), 
                        "descripcion": desc, 
                        "ciudad": geo['ciudad'], 
                        "pais": geo['pais']
                    }
                    supabase.table("transacciones").insert(data).execute()
                    st.success("✅ Guardado exitosamente en Supabase.")
                else:
                    st.error("Por favor completa la descripción y el monto.")

    elif menu == "🧠 IA Mentor":
        st.header("🤖 Análisis de Mentoría IA")
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            st.write("Últimos consejos basados en tus gastos:")
            gastos = df[df['tipo'] == 'Gasto'].head(10)
            for _, row in gastos.iterrows():
                with st.expander(f"📌 {row['descripcion']} - ${row['monto']}"):
                    st.write(analizar_ia_personalizado(row['descripcion'], row['monto'], geo))
        else:
            st.info("Aún no hay datos registrados en la nube.")

    elif menu == "📊 Datos":
        st.header("Dashboard de Control")
        res = supabase.table("transacciones").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.pie(df[df['tipo'] == 'Gasto'], values='monto', names='categoria', title="Distribución de Gastos", hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.write("Tabla de movimientos:")
                st.dataframe(df, use_container_width=True)
        else:
            st.info("Registra datos para ver el análisis gráfico.")

# --- CONTROLADOR DE SESIÓN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    mostrar_login()
else:
    main()
