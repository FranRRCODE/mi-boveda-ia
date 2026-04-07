import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import yfinance as yf
import random
from datetime import datetime

# --- CONFIGURACIÓN DE NUBE ---
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
except:
    st.error("⚠️ Configura tus Secrets en Streamlit Cloud (SUPABASE_URL y SUPABASE_KEY)")
    st.stop()

# --- CONFIGURACIÓN DE USUARIO ---
USUARIO_MASTER = "admin"
PASSWORD_MASTER = "1234567899"

# --- FUNCIONES DE UBICACIÓN Y MONEDA ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        res = requests.get('https://ipapi.co/json/').json()
        return {
            "ciudad": res.get("city", "Desconocida"),
            "pais": res.get("country_name", "Global"),
            "code": res.get("country", "US"),
            "moneda_sugerida": res.get("currency", "USD")
        }
    except:
        return {"ciudad": "Desconocida", "pais": "Global", "code": "US", "moneda_sugerida": "USD"}

# --- LÓGICA DE IA ---
def analizar_ia_personalizado(desc, monto, moneda, geo):
    desc = desc.lower()
    # Ajuste de contexto según moneda (ejemplo rápido: 1000 CLP no es igual a 1000 USD)
    es_moneda_devaluada = moneda in ["CLP", "COP", "ARS", "PYG"]
    monto_critico = 50000 if es_moneda_devaluada else 100

    hacks = {
        "starbucks": "☕ **Hack IA:** El café de marca es una fuga de capital. Usa termo propio para descuentos.",
        "netflix": "📺 **Optimización:** Revisa tus suscripciones. Si no las usas diario, cámbiate a planes básicos.",
        "uber": f"🚗 **Movilidad:** En {geo['ciudad']}, compara Uber vs Didi. Puedes ahorrar un 15% por viaje.",
        "doggis": "🌭 **Tip Local:** Usa los cupones de la App. Los miércoles de 2x1 son la mejor opción.",
        "amazon": "📦 **Compra Online:** Usa comparadores. Si el monto supera {moneda} {monto_critico}, espera 48h antes de comprar.",
        "supermercado": "🛒 **Súper:** Compra marcas blancas; ahorras un 30% en productos básicos.",
        "servicios sexuales": "⚠️ **Gestión:** Gasto discrecional alto. Pon un tope mensual fijo en {moneda} para no afectar tu renta."
    }
    
    for clave in hacks:
        if clave in desc:
            return hacks[clave]
    return f"🔍 **Análisis General:** Gasto detectado en {geo['ciudad']}. ¿Es realmente necesario este gasto de {moneda} {monto}?"

# --- INTERFAZ LOGIN ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 IA Finance Secure</h1>", unsafe_allow_html=True)
    if 'c_n1' not in st.session_state:
        st.session_state.c_n1 = random.randint(1, 10)
        st.session_state.c_n2 = random.randint(1, 10)

    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        captcha = st.number_input(f"🤖 Captcha: {st.session_state.c_n1} + {st.session_state.c_n2}?", step=1)
        if st.form_submit_button("Entrar"):
            if captcha == (st.session_state.c_n1 + st.session_state.c_n2) and u == USUARIO_MASTER and p == PASSWORD_MASTER:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Datos incorrectos o Captcha fallido.")

# --- APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    
    # --- CONFIGURACIÓN DE MONEDA EN SIDEBAR ---
    st.sidebar.title(f"📍 {geo['ciudad']}")
    
    lista_monedas = ["USD", "CLP", "MXN", "COP", "EUR", "ARS", "PEN", "BRL"]
    # Intentamos pre-seleccionar la moneda de su país
    idx_default = lista_monedas.index(geo['moneda_sugerida']) if geo['moneda_sugerida'] in lista_monedas else 0
    
    moneda_selec = st.sidebar.selectbox("Selecciona tu moneda:", lista_monedas, index=idx_default)
    
    # Mostrar tipo de cambio si no es USD
    if moneda_selec != "USD":
        try:
            t_cambio = yf.Ticker(f"USD{moneda_selec}=X").history(period="1d")['Close'].iloc[-1]
            st.sidebar.metric(f"1 USD a {moneda_selec}", f"${t_cambio:.2f}")
        except: pass

    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 IA Mentor", "📊 Datos"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    # --- SECCIONES ---
    if menu == "➕ Registro":
        st.header(f"📥 Registro en {moneda_selec}")
        with st.form("reg_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input(f"Monto Total", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Uber, Starbucks, Arriendo)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    data = {
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }
                    supabase.table("transacciones").insert(data).execute()
                    st.success(f"✅ Guardado en {moneda_selec}")

    elif menu == "🧠 IA Mentor":
        st.header("🤖 Análisis Personalizado")
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            for _, row in df[df['tipo'] == 'Gasto'].head(10).iterrows():
                # Pasamos la moneda guardada en el registro a la IA
                moneda_registro = row.get('moneda', 'USD')
                with st.expander(f"📌 {row['descripcion']} ({moneda_registro} {row['monto']:,.0f})"):
                    st.write(analizar_ia_personalizado(row['descripcion'], row['monto'], moneda_registro, geo))
        else: st.info("Sin movimientos.")

    elif menu == "📊 Datos":
        st.header("Dashboard Financiero")
        res = supabase.table("transacciones").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            # Solo mostramos gráficos de la moneda actualmente seleccionada para no mezclar peras con manzanas
            df_moneda = df[df['moneda'] == moneda_selec]
            if not df_moneda.empty:
                st.subheader(f"Gastos en {moneda_selec}")
                fig = px.pie(df_moneda[df_moneda['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_moneda, use_container_width=True)
            else:
                st.warning(f"No hay registros guardados en {moneda_selec}.")
        else: st.info("No hay datos.")

# --- CONTROLADOR ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    mostrar_login()
else:
    main()
