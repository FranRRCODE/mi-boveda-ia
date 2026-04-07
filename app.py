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

# --- 3. DETECCIÓN AUTOMÁTICA DE UBICACIÓN ---
@st.cache_data(ttl=3600)
def obtener_geo_automatica():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        url_api = f"http://ip-api.com/json/{user_ip}" if user_ip else "http://ip-api.com/json/"
        res = requests.get(url_api).json()
        if res.get("status") == "success":
            return {
                "ciudad": res.get("city", "Santiago"),
                "pais": res.get("country", "Chile"),
                "code": res.get("countryCode", "CL"),
                "moneda": "CLP" if res.get("countryCode") == "CL" else "USD"
            }
    except: pass
    return {"ciudad": "Santiago", "pais": "Chile", "code": "CL", "moneda": "CLP"}

# --- 4. LÓGICA DE IA ---
def analizar_ia_personalizado(desc, monto, moneda, ciudad):
    desc = desc.lower()
    hacks = {
        "starbucks": "☕ **Hack IA:** El café premium es una fuga silenciosa. Usa el termo de la marca para descuentos.",
        "netflix": "📺 **Optimización:** Revisa tus suscripciones. Considera el plan con anuncios.",
        "uber": f"🚗 **Movilidad en {ciudad}:** Compara con Didi. Ahorras hasta un 20%.",
        "doggis": "🌭 **Tip Local:** Los miércoles de '2x1' en la App son el mejor hack.",
        "amazon": "📦 **Compra Online:** Aplica la regla de las 48h antes de comprar.",
        "supermercado": "🛒 **Súper:** Compra marcas propias; ahorras un 30%."
    }
    for clave, consejo in hacks.items():
        if clave in desc: return consejo
    return f"🔍 **Análisis:** Detectado en {ciudad}. ¿Es necesario este gasto de {moneda} {monto:,.0f}?"

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
    geo = obtener_geo_automatica()
    st.sidebar.title("📍 Ubicación")
    st.sidebar.success(f"**{geo['ciudad']}, {geo['pais']}**")
    
    lista_monedas = ["CLP", "USD", "MXN", "COP", "EUR", "ARS", "BRL", "PEN"]
    idx_def = lista_monedas.index(geo['moneda']) if geo['moneda'] in lista_monedas else 1
    moneda_selec = st.sidebar.selectbox("Moneda:", lista_monedas, index=idx_def)
    
    st.sidebar.markdown("---")
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Mentor IA", "📊 Dashboard", "✏️ Editar / Borrar"])
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

    # --- A: REGISTRO ---
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
                    st.success("✅ Guardado en la nube.")

    # --- B: MENTOR IA ---
    elif menu == "🧠 Mentor IA":
        st.header(f"🤖 Análisis IA ({geo['ciudad']})")
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            for _, row in df[df['tipo'] == 'Gasto'].head(10).iterrows():
                m_reg = row.get('moneda', moneda_selec)
                with st.expander(f"📌 {row['descripcion']} - {m_reg} {row['monto']:,.0f}"):
                    st.info(analizar_ia_personalizado(row['descripcion'], row['monto'], m_reg, geo['ciudad']))

    # --- C: DASHBOARD ---
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
                st.dataframe(df_m.sort_values(by="id", ascending=False), use_container_width=True)
            else: st.warning(f"Sin registros en {moneda_selec}.")

    # --- D: EDITAR / BORRAR (NUEVA OPCIÓN) ---
    elif menu == "✏️ Editar / Borrar":
        st.header("🛠️ Modificar Movimientos")
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        
        if not df.empty:
            # Seleccionar por ID y Descripción
            opciones = {f"ID: {row['id']} | {row['descripcion']} (${row['monto']})": row['id'] for _, row in df.iterrows()}
            seleccion = st.selectbox("Selecciona el registro a corregir:", list(opciones.keys()))
            id_a_editar = opciones[seleccion]
            
            # Obtener datos actuales del registro seleccionado
            registro = df[df['id'] == id_a_editar].iloc[0]
            
            st.markdown("---")
            with st.form("edit_form"):
                st.write(f"Modificando Registro ID: {id_a_editar}")
                col1, col2 = st.columns(2)
                nuevo_tipo = col1.selectbox("Tipo", ["Gasto", "Ingreso"], index=0 if registro['tipo'] == "Gasto" else 1)
                nueva_cat = col2.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"], 
                                           index=["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"].index(registro['categoria']))
                nuevo_monto = st.number_input("Monto Corregido", value=float(registro['monto']))
                nueva_desc = st.text_input("Descripción Corregida", value=registro['descripcion'])
                
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.form_submit_button("💾 Guardar Cambios"):
                    update_data = {"tipo": nuevo_tipo, "categoria": nueva_cat, "monto": nuevo_monto, "descripcion": nueva_desc}
                    supabase.table("transacciones").update(update_data).eq("id", id_a_editar).execute()
                    st.success("✅ ¡Registro actualizado!")
                    st.rerun()
                
                if col_btn2.form_submit_button("🗑️ Borrar Permanentemente"):
                    supabase.table("transacciones").delete().eq("id", id_a_editar).execute()
                    st.warning("🗑️ Registro eliminado.")
                    st.rerun()
        else:
            st.info("No hay datos para editar.")

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
