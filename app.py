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

# --- 1. CONFIGURACIÓN ---
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    genai.configure(api_key=GEMINI_KEY)
except Exception as e:
    st.error("⚠️ Error en Secrets. Revisa SUPABASE y GEMINI_API_KEY.")
    st.stop()

# --- 2. UBICACIÓN POR IP REAL ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        res = requests.get(f"http://ip-api.com/json/{user_ip if user_ip else ''}").json()
        return {
            "ciudad": res.get("city", "Santiago"), 
            "moneda": "CLP" if res.get("countryCode") == "CL" else "USD",
            "pais": res.get("country", "Chile")
        }
    except:
        return {"ciudad": "Santiago", "moneda": "CLP", "pais": "Chile"}

# --- 3. MOTOR DE IA CON AUTO-RECUPERACIÓN (SOLUCIÓN AL 404) ---
def auditoria_ia_v3(row, total_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    ciudad = geo['ciudad']
    
    prompt = f"""
    Eres un Mentor Financiero experto en la economía de {ciudad}, Chile. 
    Analiza este gasto: "{desc}" por un valor de ${monto} CLP.
    
    INSTRUCCIONES:
    1. Evalúa el monto según los precios en {ciudad}.
    2. Da consejos reales: Menciona La Vega Central, Lo Valledor, Mayorista 10, Alvi o ferias libres.
    3. Si es transporte, menciona trucos de la Bip! o apps como Didi.
    4. Sé sarcástico pero muy útil.

    Responde exclusivamente en JSON:
    {{
        "tipo": "Categoría real",
        "veredicto": "Sarcasmo chileno sobre el gasto",
        "analisis": "Análisis profundo de por qué es caro o barato en Santiago",
        "donde_ahorrar": "Lista de lugares REALES en {ciudad} con mejores precios para esto.",
        "plan": ["Paso 1 para ahorrar", "Paso 2 para ahorrar", "Paso 3 para ahorrar"],
        "color": "red" o "green" o "orange"
    }}
    """

    # --- LISTA DE MODELOS A PROBAR (PARA EVITAR EL 404) ---
    modelos_a_probar = ['gemini-1.5-flash-latest', 'gemini-1.5-flash', 'gemini-pro']
    
    last_error = ""
    for nombre_modelo in modelos_a_probar:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            
            # Limpieza y extracción de JSON
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            last_error = str(e)
            continue # Si falla (404), prueba el siguiente modelo
            
    # SI TODOS FALLAN, USAMOS ESTE MENTOR MANUAL CHILENO
    return {
        "tipo": "Gasto Registrado",
        "veredicto": "IA Temporalmente fuera de línea",
        "analisis": f"Registraste un gasto de ${monto} en {ciudad}. (Error Técnico: {last_error[:50]})",
        "donde_ahorrar": f"En {ciudad}, la regla de oro es: NUNCA compres en el Jumbo si quieres ahorrar. Anda a La Vega Central para frutas/verduras y al Mayorista 10 para abarrotes.",
        "plan": ["Revisa tu presupuesto semanal", "Compara precios en la App 'Tuu'", "Usa marcas propias"],
        "color": "orange"
    }

# --- 4. SEGURIDAD: LOGIN CON CAPTCHA ---
def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Bóveda IA Mentor</h2>", unsafe_allow_html=True)
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 9), random.randint(1, 9)
    
    with st.container(border=True):
        u = st.text_input("Usuario Master")
        p = st.text_input("Contraseña", type="password")
        captcha_res = st.number_input(f"Captcha: ¿Cuánto es {st.session_state.n1} + {st.session_state.n2}?", step=1)
        
        if st.button("Ingresar al Sistema", use_container_width=True):
            if u == "admin" and p == "1234567899" and captcha_res == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Acceso Denegado.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 9), random.randint(1, 9)

# --- 5. APLICACIÓN PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    st.sidebar.info(f"📍 Detectado en **{geo['pais']}**")
    
    menu = st.sidebar.radio("Menú", ["➕ Registro Rápido", "🧠 Auditoría IA Santiago", "📊 Dashboard"])

    # Datos Supabase
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro Rápido":
        st.header(f"📥 Registro de Gastos ({geo['ciudad']})")
        with st.form("r_form", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Vivienda", "Ocio", "Otros"])
            monto = st.number_input(f"Monto ({geo['moneda']})", min_value=0)
            desc = st.text_input("¿En qué gastaste? (Ej: Pan y cecinas en el negocio)")
            if st.form_submit_button("Guardar Gasto"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": "Gasto", "categoria": cat, "monto": monto, 
                        "descripcion": desc, "ciudad": geo['ciudad'], "moneda": geo['moneda']
                    }).execute()
                    st.toast("Gasto guardado. Gemini analizando...")
                    st.rerun()

    elif menu == "🧠 Auditoría IA Santiago":
        st.header(f"🕵️ Auditoría Experta: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Hola, soy tu mentor experto en **Santiago**. He analizado tus gastos:")
            
            for _, row in df_g.head(8).iterrows():
                with st.spinner(f"Conectando con el cerebro de Google..."):
                    info = auditoria_ia_v3(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    # Layout
                    col1, col2 = st.columns([3, 1])
                    col1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    col2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    st.write(info.get('analisis', 'Sin análisis disponible.'))
                    
                    # Hack Local (Muestra comercios reales de Santiago)
                    st.markdown(f"#### 📍 Mejores ofertas en {geo['ciudad']}:")
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'Busca en locales cercanos.')
                    
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    elif color == "green": st.success(hack)
                    else: st.info(hack)
                    
                    # Plan de acción paso a paso
                    st.markdown("**🚀 Plan de Acción:**")
                    for paso in info.get('plan', []):
                        st.write(f"- {paso}")
        else:
            st.info("No hay gastos registrados aún.")

    elif menu == "📊 Dashboard":
        st.header("📊 Distribución de Gastos")
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))
            st.dataframe(df, use_container_width=True)

# --- CONTROL DE FLUJO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: login()
else: main()
