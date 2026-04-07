import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import yfinance as yf
import hashlib
import random
from datetime import datetime

# --- 1. CONFIGURACIÓN DE NUBE (SEGURA) ---
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
except Exception:
    st.error("⚠️ Configura tus Secrets en Streamlit Cloud.")
    st.stop()

# --- 2. CONFIGURACIÓN DE USUARIO ---
USUARIO_MASTER = "admin" 
PASSWORD_MASTER = "1234567899" 

# --- 3. DETECCIÓN AUTOMÁTICA DE UBICACIÓN POR IP REAL ---
@st.cache_data(ttl=3600)
def obtener_geo_automatica():
    try:
        # Intentamos obtener la IP del usuario desde los encabezados de Streamlit
        # X-Forwarded-For suele contener la IP real del cliente
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        
        # Si no hay IP en los headers (local), usamos la IP del servidor como fallback
        url_api = f"http://ip-api.com/json/{user_ip}" if user_ip else "http://ip-api.com/json/"
        
        res = requests.get(url_api).json()
        
        if res.get("status") == "success":
            return {
                "ciudad": res.get("city", "Santiago"),
                "pais": res.get("country", "Chile"),
                "code": res.get("countryCode", "CL"),
                "moneda": "CLP" if res.get("countryCode") == "CL" else "USD",
                "ip": user_ip
            }
    except:
        pass
    # Valores por defecto de seguridad
    return {"ciudad": "Santiago", "pais": "Chile", "code": "CL", "moneda": "CLP", "ip": "Local"}

# --- 4. LÓGICA DE IA ---
def analizar_ia_personalizado(desc, monto, moneda, ciudad):
    desc = desc.lower()
    es_moneda_baja = moneda in ["CLP", "COP", "ARS", "PYG"]
    monto_aviso = 40000 if es_moneda_baja else 100

    hacks = {
        "starbucks": "☕ **Hack IA:** El café premium es una fuga silenciosa. Usa el termo de la marca para obtener descuentos.",
        "netflix": "📺 **Optimización:** Revisa tus suscripciones. Considera el plan con anuncios para ahorrar un 40%.",
        "uber": f"🚗 **Movilidad en {ciudad}:** Compara con Didi o Cabify. En horas punta, ahorras hasta un 20%.",
        "doggis": "🌭 **Tip Local:** Los miércoles de '2x1' en la App son el mejor hack de ahorro.",
        "amazon": f"📦 **Compra Online:** Si el monto supera {moneda} {monto_aviso}, espera 48h antes de comprar.",
        "supermercado": "🛒 **Súper:** Compra marcas propias; ahorras un 30% en la canasta básica.",
        "servicios sexuales": "⚠️ **Gestión Financiera:** Gasto discrecional alto. Define un tope mensual fijo.",
        "gasolina": "⛽ **Eficiencia:** Carga combustible temprano; la densidad es mayor por el frío."
    }
    for clave, consejo in hacks.items():
        if clave in desc: return consejo
    return f"🔍 **Análisis General:** Detectado en {ciudad}. ¿Es necesario este gasto de {moneda} {monto:,.0f}?"

# --- 5. INTERFAZ LOGIN ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 IA Finance Secure</h1>", unsafe_allow_html=True)
    if 'c_n1' not in st.session_state:
        st.session_state.c_n1, st.session_state.c_n2 = random.randint(1, 10), random.randint(1, 10)

    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        captcha = st.number_input(f"🤖 Captcha: {st.session_state.c_n1} + {st.session_state.c_n2}?", step=1)
        if st.form_submit_button("Entrar"):
            if captcha == (st.session_state.c_n1 + st.session_state.c_n2) and u == USUARIO_MASTER and p == PASSWORD_MASTER:
                st.session_state.auth = True
                st.rerun()
            else: st.error("Datos incorrectos.")

# --- 6. APP PRINCIPAL ---
def main():
    # Ubicación 100% Automática
    geo = obtener_geo_automatica()
    
    st.sidebar.title("📍 Ubicación Inteligente")
    st.sidebar.success(f"Detectado en: **{geo['ciudad']}, {geo['pais']}**")
    
    # Moneda Automática
    lista_monedas = ["CLP", "USD", "MXN", "COP", "EUR", "ARS", "BRL", "PEN"]
    idx_def = lista_monedas.index(geo['moneda']) if geo['moneda'] in lista_monedas else 1
    moneda_selec = st.sidebar.selectbox("Moneda:", lista_monedas, index=idx_def)
    
    # Tipo de Cambio Real
    if moneda_selec != "USD":
        try:
            t_cambio = yf.Ticker(f"USD{moneda_selec}=X").history(period="1d")['Close'].iloc[-1]
            st.sidebar.metric(f"1 USD a {moneda_selec}", f"${t_cambio:.2f}")
        except: pass

    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Mentor IA", "📊 Dashboard"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    if menu == "➕ Registro":
        st.header(f"📥 Registro en {moneda_selec}")
        with st.form("reg_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input(f"Monto ({moneda_selec})", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Uber, Starbucks, Doggis)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    data = {"tipo": tipo, "categoria": cat, "monto": float(monto), "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais'], "moneda": moneda_selec}
                    supabase.table("transacciones").insert(data).execute()
                    st.success(f"✅ Guardado en la nube.")

    elif menu == "🧠 Mentor IA":
        st.header(f"🤖 Análisis IA ({geo['ciudad']})")
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            for _, row in df[df['tipo'] == 'Gasto'].head(10).iterrows():
                m_reg = row.get('moneda', moneda_selec)
                with st.expander(f"📌 {row['descripcion']} - {m_reg} {row['monto']:,.0f}"):
                    st.info(analizar_ia_personalizado(row['descripcion'], row['monto'], m_reg, geo['ciudad']))

    elif menu == "📊 Dashboard":
        st.header(f"Dashboard ({moneda_selec})")
        res = supabase.table("transacciones").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                c1, c2, c3 = st.columns(3)
                ing, gas = df_m[df_m['tipo'] == 'Ingreso']['monto'].sum(), df_m[df_m['tipo'] == 'Gasto']['monto'].sum()
                c1.metric("Ingresos", f"{moneda_selec} {ing:,.0f}")
                c2.metric("Gastos", f"{moneda_selec} {gas:,.0f}")
                c3.metric("Balance", f"{moneda_selec} {ing-gas:,.0f}")
                st.plotly_chart(px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.4))
            else: st.warning(f"Sin registros en {moneda_selec}.")

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
