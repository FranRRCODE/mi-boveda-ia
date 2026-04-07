import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import random
import time
from openai import OpenAI # <--- Cambiamos a OpenAI
import json

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Bóveda IA Mentor Pro", page_icon="🔐", layout="wide")

def inicializar_servicios():
    try:
        URL_NUBE = st.secrets["SUPABASE_URL"]
        KEY_NUBE = st.secrets["SUPABASE_KEY"]
        GPT_KEY = st.secrets["OPENAI_API_KEY"] # <--- Usar OpenAI Key
        
        sb = create_client(URL_NUBE, KEY_NUBE)
        # Inicializar Cliente de OpenAI
        client_gpt = OpenAI(api_key=GPT_KEY)
        
        return sb, client_gpt
    except Exception as e:
        st.error(f"Error de configuración: {e}")
        st.stop()

supabase, gpt = inicializar_servicios()

# --- 2. UBICACIÓN POR IP REAL ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        res = requests.get("https://ipapi.co/json/").json()
        return {
            "ciudad": res.get("city", "Santiago"),
            "pais": res.get("country_name", "Chile"),
            "moneda": "CLP" if res.get("country") == "CL" else "USD"
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP"}

# --- 3. MOTOR DE IA (GPT-4o-mini EXPERT SANTIAGO) ---
def auditoria_ia_gpt(row, total_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    ciudad = geo['ciudad']
    
    # Prompt de alta precisión para Santiago
    prompt_sistema = f"""
    Eres un Mentor Financiero 'Tiburón' experto en la economía de {ciudad}, Chile. 
    Analiza los gastos de forma sarcástica, directa y muy útil. 
    Menciona comercios reales: La Vega Central, Lo Valledor, Mayorista 10, Alvi, ferias libres.
    Responde SIEMPRE en formato JSON puro.
    """
    
    prompt_usuario = f"""
    Analiza este gasto: "{desc}" por ${monto} CLP en {ciudad}.
    
    Responde en JSON:
    {{
        "tipo": "Categoría exacta",
        "veredicto": "Sarcasmo financiero sobre el precio",
        "analisis": "Análisis profundo de por qué es caro/barato en Santiago",
        "donde_ahorrar": "Lista de lugares REALES en Santiago con mejores precios",
        "plan": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" (caro), "green" (ahorro), "orange" (normal)
    }}
    """
    
    try:
        response = gpt.chat.completions.create(
            model="gpt-4o-mini", # El modelo más rápido y barato de OpenAI
            messages=[
                {"role": "system", "content": prompt_sistema},
                {"role": "user", "content": prompt_usuario}
            ],
            response_format={ "type": "json_object" } # Forzamos respuesta JSON
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "tipo": "Error",
            "veredicto": "GPT Offline",
            "analisis": f"Error técnico: {str(e)[:50]}",
            "donde_ahorrar": "📍 En Santiago: Prefiere ferias libres o el Mayorista 10.",
            "plan": ["Reintentar luego", "Verificar API Key"],
            "color": "blue"
        }

# --- 4. SEGURIDAD: LOGIN CON CAPTCHA ---
def login():
    st.markdown("<h2 style='text-align: center;'>🔐 Acceso Mentor Pro</h2>", unsafe_allow_html=True)
    if 'n1' not in st.session_state:
        st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)
    
    with st.container(border=True):
        u = st.text_input("Usuario Master")
        p = st.text_input("Contraseña", type="password")
        cap = st.number_input(f"Captcha: ¿Cuánto es {st.session_state.n1} + {st.session_state.n2}?", step=1, value=0)
        
        if st.button("Ingresar", use_container_width=True):
            if u == "admin" and p == "1234567899" and cap == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Acceso denegado.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

# --- 5. APLICACIÓN PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    st.sidebar.info(f"📍 Detectado en **{geo['pais']}**")
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría GPT", "📊 Dashboard"])

    # Cargar datos desde Supabase
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Registro en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Vivienda", "Ocio", "Otros"])
            monto = st.number_input("Monto (CLP)", min_value=0)
            desc = st.text_input("Descripción (Ej: Carne en el Lider)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": "Gasto", "categoria": cat, "monto": monto, 
                        "descripcion": desc, "ciudad": geo['ciudad'], "moneda": "CLP"
                    }).execute()
                    st.success("✅ Gasto registrado.")
                    st.rerun()

    elif menu == "🧠 Auditoría GPT":
        st.header(f"🕵️ Auditoría Pro con OpenAI: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Soy tu mentor GPT en **{geo['ciudad']}**. He analizado tus gastos:")
            
            for _, row in df_g.head(10).iterrows():
                with st.spinner(f"GPT analizando {row['descripcion']}..."):
                    info = auditoria_ia_gpt(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    c2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    st.write(info.get('analisis', 'Sin análisis.'))
                    
                    st.markdown(f"**📍 Hacks para {geo['ciudad']}:**")
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'Busca picadas.')
                    
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    else: st.success(hack)
                    
                    st.markdown("**🚀 Plan de Acción:**")
                    for p in info.get('plan', []): st.write(f"- {p}")
        else:
            st.info("Registra un gasto para empezar.")

    elif menu == "📊 Dashboard":
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: login()
else: main()
