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

# --- 1. CONFIGURACIÓN DE NUBE ---
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    genai.configure(api_key=GEMINI_KEY)
except Exception as e:
    st.error("⚠️ Configura los Secrets (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY).")
    st.stop()

# --- 2. UBICACIÓN REAL POR IP ---
@st.cache_data(ttl=3600)
def obtener_geo_real():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        res = requests.get(f"http://ip-api.com/json/{user_ip}").json()
        return {
            "ciudad": res.get("city", "Santiago"),
            "pais": res.get("country", "Chile"),
            "moneda": "CLP" if res.get("countryCode") == "CL" else "USD",
            "cod_pais": res.get("countryCode", "CL")
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP", "cod_pais": "CL"}

# --- 3. CEREBRO DE EMERGENCIA (Si Gemini falla) ---
def mentor_chileno_manual(desc, monto, ciudad):
    desc = desc.lower()
    if "super" in desc or "lider" in desc or "jumbo" in desc or "santa isabel" in desc:
        return {
            "tipo": "Supermercado / Comida",
            "veredicto": "Gasto Crítico",
            "analisis": f"En {ciudad}, los supermercados de cadena son cómodos pero caros.",
            "donde_ahorrar": "📍 Anda a La Vega Central o Lo Valledor. Si no puedes, el Mayorista 10 o Alvi tienen precios 20% más bajos que el Jumbo.",
            "plan": ["Usa marcas propias (Lider/Acuenta)", "No vayas al super con hambre", "Revisa la App 'Tuu'"],
            "color": "orange"
        }
    if "uber" in desc or "didi" in desc or "cabify" in desc or "transporte" in desc:
        return {
            "tipo": "Transporte de App",
            "veredicto": "Comodidad vs Ahorro",
            "analisis": "Moverse en app en Santiago sube el gasto mensual en un 15% sin que te des cuenta.",
            "donde_ahorrar": "📍 Usa la micro/Metro fuera de hora punta (Tarifa Baja). Compara Didi y Uber siempre; Didi suele ser $1.500 más barato.",
            "plan": ["Carga tu Bip con anticipación", "Camina tramos cortos", "Usa Didi Moto si vas solo"],
            "color": "blue"
        }
    return {
        "tipo": "Gasto General",
        "veredicto": "Analizado",
        "analisis": f"Gasto registrado en {ciudad}.",
        "donde_ahorrar": "📍 Busca picadas locales o ferias libres de barrio.",
        "plan": ["Registra todo", "Compara precios", "Evita el gasto hormiga"],
        "color": "green"
    }

# --- 4. MOTOR DE IA GEMINI AVANZADO ---
def auditoria_ia_pro(row, total_gastos_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    prompt = f"""
    Eres un Mentor Financiero Sarcástico en {geo['ciudad']}, Chile. 
    Gasto: "{desc}" | Monto: {moneda} {monto} | Impacto: {impacto:.1f}%.

    Responde ESTRICTAMENTE en JSON con estos campos:
    "tipo": categoria,
    "veredicto": veredicto corto,
    "analisis": analisis detallado de por que este gasto importa en Santiago,
    "donde_ahorrar": menciona lugares REALES de Santiago (La Vega, Mayorista 10, Alvi, ferias),
    "plan": [3 pasos de ahorro],
    "color": "red" o "green" o "orange" o "blue"
    """

    modelos = ['gemini-1.5-flash', 'gemini-pro']
    for m in modelos:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            clean = re.search(r'\{.*\}', response.text, re.DOTALL).group()
            return json.loads(clean)
        except:
            continue
            
    # SI TODO FALLA, USAR EL MENTOR MANUAL
    return mentor_chileno_manual(desc, monto, geo['ciudad'])

# --- 5. LOGIN CON CAPTCHA ---
def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Bóveda IA</h2>", unsafe_allow_html=True)
    if 'c1' not in st.session_state:
        st.session_state.c1, st.session_state.c2 = random.randint(1, 9), random.randint(1, 9)
    
    with st.form("f_login"):
        u = st.text_input("Usuario")
        p = st.text_input("Password", type="password")
        captcha = st.number_input(f"Captcha: {st.session_state.c1} + {st.session_state.c2}?", step=1)
        if st.form_submit_button("Entrar"):
            if u == "admin" and p == "1234567899" and captcha == (st.session_state.c1 + st.session_state.c2):
                st.session_state.auth = True
                st.rerun()
            else: st.error("Error en credenciales.")

# --- 6. APP PRINCIPAL ---
def main():
    geo = obtener_geo_real()
    st.sidebar.title(f"📍 Mentor en {geo['ciudad']}")
    st.sidebar.caption(f"Moneda: {geo['moneda']} | IP: Detectada")
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría Experta", "📊 Dashboard"])

    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Registro ({geo['ciudad']})")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Otros"])
            monto = st.number_input(f"Monto ({geo['moneda']})", min_value=0.0)
            desc = st.text_input("Descripción específica (Ej: Supermercado Santa Isabel)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({"tipo": tipo, "categoria": cat, "monto": float(monto), "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais'], "moneda": geo['moneda']}).execute()
                    st.success("Guardado.")
                    st.rerun()

    elif menu == "🧠 Auditoría Experta":
        st.header(f"🕵️ Análisis Experto: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            for _, row in df_g.head(10).iterrows():
                with st.spinner("Analizando..."):
                    info = auditoria_ia_pro(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    c1, c2 = st.columns([2, 1])
                    c1.subheader(f"🏷️ {info['tipo']}")
                    c2.markdown(f"**Veredicto:** `{info['veredicto']}`")
                    
                    st.write(info['analisis'])
                    st.markdown(f"**📍 Mejores ofertas en {geo['ciudad']}:**")
                    
                    # Colores dinámicos
                    if info['color'] == "red": st.error(info['donde_ahorrar'])
                    elif info['color'] == "orange": st.warning(info['donde_ahorrar'])
                    elif info['color'] == "green": st.success(info['donde_ahorrar'])
                    else: st.info(info['donde_ahorrar'])
                    
                    st.markdown("**🚀 Plan de Acción:**")
                    for p in info['plan']: st.write(f"- {p}")
        else: st.info("No hay gastos.")

    elif menu == "📊 Dashboard":
        st.header("📊 Inteligencia Financiera")
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: login()
else: main()
