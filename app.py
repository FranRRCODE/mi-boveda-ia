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
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("⚠️ Configura 'GEMINI_API_KEY' en los Secrets de Streamlit.")
        st.stop()

    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    
    # Configurar Google AI
    genai.configure(api_key=GEMINI_KEY)
    
except Exception as e:
    st.error(f"❌ Error de inicio: {e}")
    st.stop()

# --- 2. UBICACIÓN REAL POR IP (DETECTA SANTIAGO) ---
@st.cache_data(ttl=3600)
def obtener_geo_real():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        url_geo = f"http://ip-api.com/json/{user_ip}" if user_ip else "http://ip-api.com/json/"
        res = requests.get(url_geo).json()
        
        return {
            "ciudad": res.get("city", "Santiago"),
            "pais": res.get("country", "Chile"),
            "moneda": "CLP" if res.get("countryCode") == "CL" else "USD",
            "ip": res.get("query", "0.0.0.0")
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP", "ip": "Desconocida"}

# --- 3. MOTOR DE IA AVANZADO (SANTIAGO EXPERT) ---
def auditoria_ia_local(row, total_gastos_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    # Prompt de alta precisión para Santiago
    prompt = f"""
    Actúa como un Gurú Financiero experto en la economía de {geo['ciudad']}, Chile. 
    Analiza este gasto del usuario: "{desc}" por un valor de {moneda} {monto}.
    Representa el {impacto:.1f}% del gasto total mensual registrado.

    INSTRUCCIONES PARA TU RESPUESTA:
    1. Evalúa si el monto es EXCESIVO para el mercado chileno actual.
    2. Da consejos REALES: si es comida, menciona La Vega Central, Lo Valledor, Mayorista 10, o marcas propias (Great Value/Lider).
    3. Si es transporte, menciona trucos de la Tarjeta Bip!, apps como Didi o Uber con descuentos.
    4. Sé sarcástico pero muy útil.

    RESPONDE EXCLUSIVAMENTE EN FORMATO JSON PLANO:
    {{
        "tipo": "Categoría específica",
        "veredicto": "Ej: Caro / Justo / Despilfarro",
        "analisis_detallado": "Análisis profundo de por qué este gasto es así en Santiago.",
        "donde_ahorrar": "Lista de lugares o apps REALES en Santiago con mejores precios para esto.",
        "plan_accion": ["Paso 1 para ahorrar", "Paso 2 para ahorrar", "Paso 3 para ahorrar"],
        "color": "red" (caro/malo), "green" (ahorro/bueno), "orange" (necesario/justo), "blue" (otros)
    }}
    """

    # Intentamos con 1.5 Flash primero, si falla usamos Pro
    for model_name in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            
            # Limpiar y extraer JSON de la respuesta de la IA
            texto_ia = response.text
            match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
            if match:
                return json.loads(match.group())
        except Exception as e:
            error_msg = str(e)
            continue # Probar el siguiente modelo
            
    # Si todo falla, mostrar el error real para arreglarlo
    return {
        "tipo": "Error de Conexión",
        "veredicto": "IA Fuera de línea",
        "analisis_detallado": f"Error detectado: {error_msg[:100]}",
        "donde_ahorrar": "Intenta revisar tu API KEY en Google AI Studio. Asegúrate de tener saldo o cuota gratis activa.",
        "plan_accion": ["Verificar API KEY", "Reintentar en unos minutos"],
        "color": "red"
    }

# --- 4. SEGURIDAD: LOGIN CON CAPTCHA ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Bóveda IA Mentor Pro</h1>", unsafe_allow_html=True)
    
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

    with st.container(border=True):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        
        st.write(f"**Seguridad:** ¿Cuánto es {st.session_state.n1} + {st.session_state.n2}?")
        res_usuario = st.number_input("Tu respuesta:", step=1, value=0)
        
        if st.button("Ingresar", use_container_width=True):
            if u == "admin" and p == "1234567899" and res_usuario == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Credenciales o Captcha incorrectos.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

# --- 5. APP PRINCIPAL ---
def main():
    geo = obtener_geo_real()
    
    st.sidebar.title(f"🏠 Mentor: {geo['ciudad']}")
    st.sidebar.markdown(f"📍 Detectado en **{geo['pais']}**")
    
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR"], index=0)
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría Pro IA", "📊 Dashboard"])

    # Cargar datos de Supabase
    try:
        res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
    except:
        df = pd.DataFrame()

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Registro en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Otros"])
            monto = st.number_input(f"Monto ({moneda_selec})", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Compras en el Lider)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.success("✅ Guardado.")
                    st.rerun()

    elif menu == "🧠 Auditoría Pro IA":
        st.header(f"🕵️ Análisis Experto: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Soy tu mentor experto en **Santiago**. He analizado tus gastos:")
            
            for _, row in df_g.head(5).iterrows():
                with st.spinner(f"Analizando '{row['descripcion']}'..."):
                    info = auditoria_ia_local(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - {row['moneda']} {row['monto']:,.0f}"):
                    # Layout del Análisis
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    c2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    st.write(info.get('analisis_detallado', '...'))
                    
                    # Hack Local (Muestra comercios reales de Santiago)
                    st.markdown(f"#### 📍 Mejores ofertas en {geo['ciudad']}:")
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'No hay datos.')
                    
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    elif color == "green": st.success(hack)
                    else: st.info(hack)
                    
                    # Plan de acción paso a paso
                    st.markdown("**🚀 Plan de Acción:**")
                    for paso in info.get('plan_accion', []):
                        st.write(f"- {paso}")
                    
                    st.caption(f"Impacto: {(row['monto']/total*100):.1f}% del presupuesto.")
        else:
            st.info("Registra gastos para empezar.")

    elif menu == "📊 Dashboard":
        st.header("📊 Inteligencia de Gastos")
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))
            st.dataframe(df, use_container_width=True)

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
