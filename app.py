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
    st.error("⚠️ Configura tus Secrets en Streamlit Cloud (SUPABASE_URL y SUPABASE_KEY)")
    st.stop()

# --- 2. CONFIGURACIÓN DE USUARIO ---
USUARIO_MASTER = "admin" 
# Esta es tu contraseña real (Cámbiala si quieres)
PASSWORD_MASTER = "1234567899" 

# --- 3. FUNCIONES DE UBICACIÓN (MEJORADAS) ---
@st.cache_data(ttl=3600)
def obtener_geo_automatica():
    try:
        # Usamos ip-api.com que es más permisiva con servidores de la nube
        res = requests.get('http://ip-api.com/json/').json()
        if res.get("status") == "success":
            return {
                "ciudad": res.get("city", "Santiago"),
                "pais": res.get("country", "Chile"),
                "code": res.get("countryCode", "CL"),
                "moneda": "CLP" if res.get("countryCode") == "CL" else "USD"
            }
    except:
        pass
    # Valores por defecto si falla la detección
    return {"ciudad": "Santiago", "pais": "Chile", "code": "CL", "moneda": "CLP"}

# --- 4. LÓGICA DE IA PERSONALIZADA ---
def analizar_ia_personalizado(desc, monto, moneda, ciudad):
    desc = desc.lower()
    es_moneda_baja = moneda in ["CLP", "COP", "ARS", "PYG"]
    monto_aviso = 40000 if es_moneda_baja else 100

    hacks = {
        "starbucks": "☕ **Hack IA:** El café premium es una fuga silenciosa. Usa el termo de la marca para obtener descuentos en cada recarga.",
        "netflix": "📺 **Optimización:** ¿Ves Netflix a diario? Si no, cambia al plan con anuncios o comparte gastos legalmente.",
        "uber": f"🚗 **Movilidad en {ciudad}:** Compara con Didi o Cabify. En horas punta, la diferencia suele ser de hasta un 20%.",
        "doggis": "🌭 **Tip Local:** Revisa la App de Doggis los miércoles; los cupones de '2x1' son el mejor hack de ahorro en comida rápida.",
        "amazon": f"📦 **Compra Online:** Si el monto supera {moneda} {monto_aviso}, aplica la regla de las 48h antes de confirmar el pago.",
        "supermercado": "🛒 **Súper:** Compra marcas propias (Líder, Great Value, etc); ahorras un 30% en la canasta básica.",
        "servicios sexuales": "⚠️ **Gestión Financiera:** Este es un gasto discrecional de alto impacto. Define un presupuesto mensual fijo para no comprometer tus ahorros.",
        "gasolina": "⛽ **Eficiencia:** Carga combustible temprano en la mañana; la densidad es mayor y obtienes un poco más por tu dinero."
    }
    
    for clave, consejo in hacks.items():
        if clave in desc:
            return consejo
            
    return f"🔍 **Análisis General:** Gasto en {ciudad}. Pregúntate: ¿Este gasto de {moneda} {monto:,.0f} me acerca a mis metas de ahorro?"

# --- 5. INTERFAZ DE LOGIN ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 IA Finance Secure Access</h1>", unsafe_allow_html=True)
    
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
                st.session_state.c_n1 = random.randint(1, 10)
                st.session_state.c_n2 = random.randint(1, 10)

# --- 6. APP PRINCIPAL ---
def main():
    # Obtener ubicación inicial
    geo_auto = obtener_geo_automatica()
    
    # --- BARRA LATERAL (CONFIGURACIÓN) ---
    st.sidebar.title("📍 Configuración Local")
    
    # Selector de Ubicación Manual (Por si la IP falla)
    ubicacion_user = st.sidebar.text_input("Tu Ciudad/País:", value=f"{geo_auto['ciudad']}, {geo_auto['pais']}")
    ciudad_final = ubicacion_user.split(",")[0].strip()
    
    # Selector de Moneda Global
    lista_monedas = ["CLP", "USD", "MXN", "COP", "EUR", "ARS", "BRL", "PEN"]
    idx_def = lista_monedas.index(geo_auto['moneda']) if geo_auto['moneda'] in lista_monedas else 1
    moneda_selec = st.sidebar.selectbox("Moneda de trabajo:", lista_monedas, index=idx_def)
    
    # Mostrar Tasa de Cambio Real
    if moneda_selec != "USD":
        try:
            t_cambio = yf.Ticker(f"USD{moneda_selec}=X").history(period="1d")['Close'].iloc[-1]
            st.sidebar.metric(f"1 USD a {moneda_selec}", f"${t_cambio:.2f}")
        except:
            pass

    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Mentor IA", "📊 Dashboard"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    # --- SECCIÓN A: REGISTRO ---
    if menu == "➕ Registro":
        st.header(f"📥 Registro en {moneda_selec}")
        with st.form("reg_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            tipo = col1.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = col2.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input(f"Monto Total ({moneda_selec})", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Starbucks, Uber, Doggis)")
            
            if st.form_submit_button("Guardar en Nube"):
                if desc and monto > 0:
                    data = {
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": ciudad_final, 
                        "pais": ubicacion_user.split(",")[-1].strip(), "moneda": moneda_selec
                    }
                    supabase.table("transacciones").insert(data).execute()
                    st.success(f"✅ Guardado exitosamente en {moneda_selec}")
                else:
                    st.warning("Completa la descripción y el monto.")

    # --- SECCIÓN B: MENTOR IA ---
    elif menu == "🧠 Mentor IA":
        st.header(f"🤖 Análisis IA para {ciudad_final}")
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            gastos_df = df[df['tipo'] == 'Gasto'].head(10)
            if not gastos_df.empty:
                for _, row in gastos_df.iterrows():
                    m_reg = row.get('moneda', moneda_selec)
                    with st.expander(f"📌 {row['descripcion']} - {m_reg} {row['monto']:,.0f}"):
                        st.info(analizar_ia_personalizado(row['descripcion'], row['monto'], m_reg, ciudad_final))
            else:
                st.info("No hay gastos registrados para analizar.")
        else:
            st.info("La nube está vacía. Registra movimientos primero.")

    # --- SECCIÓN C: DASHBOARD ---
    elif menu == "📊 Dashboard":
        st.header(f"Resumen Financiero ({moneda_selec})")
        res = supabase.table("transacciones").select("*").execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            # Filtramos solo por la moneda seleccionada para no mezclar valores
            df_m = df[df['moneda'] == moneda_selec]
            
            if not df_m.empty:
                c1, c2, c3 = st.columns(3)
                ing = df_m[df_m['tipo'] == 'Ingreso']['monto'].sum()
                gas = df_m[df_m['tipo'] == 'Gasto']['monto'].sum()
                c1.metric("Ingresos", f"{moneda_selec} {ing:,.0f}")
                c2.metric("Gastos", f"{moneda_selec} {gas:,.0f}")
                c3.metric("Balance", f"{moneda_selec} {ing-gas:,.0f}")
                
                st.subheader("Distribución de Gastos")
                fig = px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("Historial de Transacciones")
                st.dataframe(df_m.sort_values(by='id', ascending=False), use_container_width=True)
            else:
                st.warning(f"No hay registros guardados en la moneda {moneda_selec}.")
        else:
            st.info("No hay datos registrados.")

# --- CONTROLADOR DE SESIÓN ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    mostrar_login()
else:
    main()
