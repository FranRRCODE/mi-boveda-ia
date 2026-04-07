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
    genai.configure(api_key=GEMINI_KEY)
    
except Exception as e:
    st.error(f"❌ Error de inicio: {e}")
    st.stop()

# --- 2. UBICACIÓN REAL POR IP ---
@st.cache_data(ttl=3600)
def obtener_geo_real():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        url_geo = f"http://ip-api.com/json/{user_ip}" if user_ip else "http://ip-api.com/json/"
        res = requests.get(url_geo).json()
        
        ciudad = res.get("city", "Santiago")
        pais_code = res.get("countryCode", "CL")
        
        monedas_map = {"CL": "CLP", "MX": "MXN", "CO": "COP", "AR": "ARS", "ES": "EUR", "US": "USD"}
        
        return {
            "ciudad": ciudad,
            "pais": res.get("country", "Chile"),
            "moneda": monedas_map.get(pais_code, "CLP"),
            "ip": res.get("query", "0.0.0.0")
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP", "ip": "Desconocida"}

# --- 3. NUEVO MOTOR DE IA AVANZADO (SANTIAGO EXPERT) ---
def auditoria_ia_local(row, total_gastos_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    # Prompt ultra-detallado para Chile
    prompt = f"""
    Eres un Mentor Financiero 'Tiburón' experto en economía doméstica en {geo['ciudad']}, {geo['pais']}.
    Analiza este gasto: "{desc}" por {moneda} {monto}.
    Contexto: Es el {impacto:.1f}% del presupuesto mensual del usuario.

    TAREA:
    1. Determina si el monto es caro, justo o barato para los precios actuales en {geo['ciudad']}.
    2. Si es comida/supermercado: Compara precios entre Lider, Jumbo, Mayorista 10, y menciona si conviene ir a La Vega Central o Lo Valledor.
    3. Si es transporte: Compara Red Metropolitana, Uber, Didi y Cabify en Santiago.
    4. Si es ocio/café: Sé crítico sobre el 'Gasto Hormiga'.
    5. Da un plan de ahorro de 3 pasos para este tipo de gasto.

    Responde ÚNICAMENTE en JSON con esta estructura exacta:
    {{
        "tipo": "Categoría específica",
        "veredicto": "Ej: Caro / Buen precio / Gasto Innecesario",
        "analisis_detallado": "Explicación de 3-4 líneas sobre este gasto en el mercado de {geo['ciudad']}",
        "donde_ahorrar": "Nombres de tiendas, ferias o apps específicas en Santiago para este gasto",
        "plan_ahorro": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" o "green" o "orange" o "blue"
    }}
    """

    # Intentar con 1.5 Flash primero (es el que mejor maneja JSON detallado)
    for nombre_modelo in ['gemini-1.5-flash', 'gemini-pro']:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            response = model.generate_content(prompt)
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if match:
                return json.loads(match.group())
        except:
            continue
            
    return {
        "tipo": "Gasto General",
        "veredicto": "No analizado",
        "analisis_detallado": "No pudimos conectar con el cerebro de la IA para un análisis profundo.",
        "donde_ahorrar": "Busca siempre en Mayoristas o Ferias Libres en Santiago.",
        "plan_ahorro": ["Registrar más gastos", "Comparar en apps", "Evitar compras impulsivas"],
        "color": "blue"
    }

# --- 4. SEGURIDAD: LOGIN CON CAPTCHA ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Bóveda IA Mentor Pro</h1>", unsafe_allow_html=True)
    
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 12), random.randint(1, 12)

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
                st.session_state.n1, st.session_state.n2 = random.randint(1, 12), random.randint(1, 12)

# --- 5. APP PRINCIPAL ---
def main():
    geo = obtener_geo_real()
    
    st.sidebar.title(f"🏠 Mentor: {geo['ciudad']}")
    st.sidebar.info(f"📍 Detectado en {geo['pais']}")
    
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR"], index=0 if geo['moneda']=="CLP" else 1)
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría Pro IA", "📊 Dashboard"])

    # Datos Supabase
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Gasto en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Otros"])
            monto = st.number_input(f"Monto ({moneda_selec})", min_value=0.0)
            desc = st.text_input("Descripción específica (Ej: Supermercado Santa Isabel)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.success("✅ Guardado en la nube.")
                    st.rerun()

    elif menu == "🧠 Auditoría Pro IA":
        st.header(f"🕵️ Auditoría Especializada: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Hola, he analizado tus gastos considerando el mercado de **{geo['ciudad']}**. Aquí está tu diagnóstico:")
            
            for _, row in df_g.head(8).iterrows():
                with st.spinner(f"Analizando '{row['descripcion']}' en Santiago..."):
                    info = auditoria_ia_local(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - {row['moneda']} {row['monto']:,.0f}"):
                    # Encabezado con Veredicto
                    col1, col2 = st.columns([2, 1])
                    col1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    col2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    # Análisis Detallado
                    st.write(info.get('analisis_detallado', 'Sin detalles.'))
                    
                    # Dónde ahorrar (Nombres reales)
                    st.markdown(f"#### 📍 Mejores ofertas en {geo['ciudad']}:")
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'Busca en locales cercanos.')
                    
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    elif color == "green": st.success(hack)
                    else: st.info(hack)
                    
                    # Plan de Ahorro
                    st.markdown("**🚀 Plan de Acción:**")
                    for paso in info.get('plan_ahorro', []):
                        st.write(f"- {paso}")
        else:
            st.info("Registra un gasto primero para auditar.")

    elif menu == "📊 Dashboard":
        st.header("📊 Dashboard de Gastos")
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))
            st.dataframe(df, use_container_width=True)

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
