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

# --- 1. CONFIGURACIÓN DE NUBE Y IA ---
try:
    # Cargar llaves desde Secrets
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    # Clientes
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    
    # Configurar Gemini
    genai.configure(api_key=GEMINI_KEY)
    # CAMBIO CLAVE: Usamos 'gemini-1.5-flash-latest' para evitar el error 404
    model = genai.GenerativeModel('gemini-1.5-flash-latest') 
except Exception as e:
    st.error(f"⚠️ Error de configuración: {e}")
    st.info("Revisa tus Secrets en Streamlit Cloud.")
    st.stop()

# --- 2. SEGURIDAD ---
USUARIO_MASTER = "admin" 
PASSWORD_MASTER = "1234567899" 

# --- 3. UBICACIÓN AUTOMÁTICA ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        res = requests.get("http://ip-api.com/json/").json()
        return {
            "ciudad": res.get("city", "Santiago"), 
            "pais": res.get("country", "Chile"), 
            "moneda": "CLP" if res.get("countryCode") == "CL" else "USD"
        }
    except: 
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP"}

# --- 4. MOTOR DE IA GEMINI (REFORZADO) ---
def auditoria_ia_gemini(row, total_gastos_mes, ciudad):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    prompt = f"""
    Eres un Mentor Financiero experto en {ciudad}. 
    Analiza este gasto: "{desc}" de {moneda} {monto}.
    Representa el {impacto:.1f}% del total del mes.

    Responde ÚNICAMENTE un objeto JSON con estas llaves:
    "tipo": categoria creativa,
    "analisis": frase corta de impacto,
    "hack": consejo financiero específico para Chile,
    "color": "red" (gasto innecesario), "green" (necesidad), "orange" (transporte/fijo), "blue" (otros).
    """

    try:
        response = model.generate_content(prompt)
        # Extraer solo el contenido JSON usando Regex (por si la IA mete texto extra)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            return {
                "tipo": "Gasto Registrado",
                "analisis": "Análisis en proceso.",
                "hack": "Intenta ser más específico en la descripción.",
                "color": "blue"
            }
    except Exception as e:
        return {
            "tipo": "Error de IA",
            "analisis": f"Hipo técnico: {str(e)[:40]}",
            "hack": "Revisa que tu API Key tenga cuota disponible en Google AI Studio.",
            "color": "red"
        }

# --- 5. INTERFAZ LOGIN ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Bóveda IA Mentor Pro</h1>", unsafe_allow_html=True)
    if 'c_n1' not in st.session_state:
        st.session_state.c_n1, st.session_state.c_n2 = random.randint(1, 10), random.randint(1, 10)
    with st.form("login"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        cap = st.number_input(f"Captcha: {st.session_state.c_n1} + {st.session_state.c_n2}?", step=1)
        if st.form_submit_button("Entrar"):
            if cap == (st.session_state.c_n1 + st.session_state.c_n2) and u == USUARIO_MASTER and p == PASSWORD_MASTER:
                st.session_state.auth = True
                st.rerun()
            else: st.error("Credenciales incorrectas.")

# --- 6. APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"📍 Mentor en {geo['ciudad']}")
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR", "COP"])
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard", "✏️ Editar/Borrar"])

    # Cargar datos desde Supabase
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Registro ({moneda_selec})")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input("Monto", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Feria del sábado)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.success("✅ Guardado correctamente.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA":
        st.header("🕵️ Auditoría Gemini 1.5")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            for _, row in df_g.head(10).iterrows():
                with st.spinner(f"Analizando {row['descripcion']}..."):
                    info = auditoria_ia_gemini(row, total, geo['ciudad'])
                
                with st.expander(f"🔍 {row['descripcion']} ({row['moneda']} {row['monto']:,.0f})"):
                    st.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    st.write(info.get('analisis', 'Análisis no disponible.'))
                    
                    c = info.get('color', 'blue')
                    h = info.get('hack', 'Sin consejos por ahora.')
                    if c == "red": st.error(f"💡 {h}")
                    elif c == "orange": st.warning(f"💡 {h}")
                    elif c == "green": st.success(f"💡 {h}")
                    else: st.info(f"💡 {h}")
        else:
            st.info("No hay datos para auditar.")

    elif menu == "📊 Dashboard":
        st.header("📊 Dashboard")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                st.plotly_chart(px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.5))
                st.dataframe(df_m, use_container_width=True)

    elif menu == "✏️ Editar/Borrar":
        st.header("⚙️ Gestión")
        if not df.empty:
            opc = {f"{r['descripcion']} ({r['id']})": r['id'] for _, r in df.iterrows()}
            id_sel = opc[st.selectbox("Selecciona:", list(opc.keys()))]
            reg = df[df['id'] == id_sel].iloc[0]
            with st.form("edit"):
                n_m = st.number_input("Monto", value=float(reg['monto']))
                n_d = st.text_input("Descripción", value=reg['descripcion'])
                c1, c2 = st.columns(2)
                if c1.form_submit_button("Actualizar"):
                    supabase.table("transacciones").update({"monto": n_m, "descripcion": n_d}).eq("id", id_sel).execute()
                    st.rerun()
                if c2.form_submit_button("Eliminar"):
                    supabase.table("transacciones").delete().eq("id", id_sel).execute()
                    st.rerun()

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
