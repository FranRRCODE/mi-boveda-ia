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
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    
    genai.configure(api_key=GEMINI_KEY)
    
    # CAMBIO DEFINITIVO: Usamos 'gemini-pro' que es el modelo más compatible (v1.0)
    # Este modelo no debería dar error 404 nunca si la API Key es válida.
    model = genai.GenerativeModel('gemini-pro') 
    
except Exception as e:
    st.error(f"⚠️ Error de configuración: {e}")
    st.stop()

# --- 2. SEGURIDAD ---
USUARIO_MASTER = "admin" 
PASSWORD_MASTER = "1234567899" 

# --- 3. UBICACIÓN AUTOMÁTICA ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        res = requests.get("http://ip-api.com/json/").json()
        return {"ciudad": res.get("city", "Santiago"), "pais": res.get("country", "Chile"), "moneda": "CLP" if res.get("countryCode") == "CL" else "USD"}
    except: return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP"}

# --- 4. MOTOR DE IA (REFORZADO PARA GEMINI PRO) ---
def auditoria_ia_gemini(row, total_gastos_mes, ciudad):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    # Prompt optimizado para modelos Pro
    prompt = f"""
    Eres un Mentor Financiero en {ciudad}. 
    Gasto: "{desc}" | Monto: {moneda} {monto} | % del mes: {impacto:.1f}%

    Responde SOLO con este formato JSON:
    {{
        "tipo": "categoría",
        "analisis": "breve frase de impacto",
        "hack": "consejo financiero real",
        "color": "red" o "green" o "orange" o "blue"
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Limpieza de texto para asegurar que solo leamos el JSON
        texto_sucio = response.text
        match = re.search(r'\{.*\}', texto_sucio, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("Respuesta no es JSON")
    except Exception as e:
        # Si Gemini Pro falla, usamos este análisis simple para no romper la app
        return {
            "tipo": "Gasto Registrado",
            "analisis": f"Registraste {monto} en {desc}.",
            "hack": "Si este error persiste, revisa tu API KEY en Google AI Studio.",
            "color": "blue"
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
            else: st.error("Error de acceso.")

# --- 6. APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"📍 Mentor en {geo['ciudad']}")
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR", "COP"])
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA", "📊 Dashboard", "✏️ Gestión"])

    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Registro ({moneda_selec})")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input("Monto", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Compra Supermercado)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({"tipo": tipo, "categoria": cat, "monto": float(monto), "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais'], "moneda": moneda_selec}).execute()
                    st.success("✅ Guardado.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA":
        st.header("🕵️ Auditoría con Gemini Pro")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            for _, row in df_g.head(8).iterrows():
                with st.spinner("Analizando..."):
                    info = auditoria_ia_gemini(row, total, geo['ciudad'])
                with st.expander(f"🔍 {row['descripcion']} ({row['moneda']} {row['monto']:,.0f})"):
                    st.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    st.write(info.get('analisis', 'Análisis breve.'))
                    c = info.get('color', 'blue')
                    h = info.get('hack', 'Sin hacks.')
                    if c == "red": st.error(h)
                    elif c == "orange": st.warning(h)
                    elif c == "green": st.success(h)
                    else: st.info(h)
        else:
            st.info("Sin datos.")

    elif menu == "📊 Dashboard":
        st.header("📊 Resumen")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                st.plotly_chart(px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.5))
                st.dataframe(df_m)

    elif menu == "✏️ Gestión":
        st.header("⚙️ Editar/Borrar")
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

if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
