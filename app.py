import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import random
import time
from groq import Groq # <--- Nueva IA gratuita
import json
import re

# --- 1. CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Bóveda IA Mentor Pro", page_icon="🔐", layout="wide")

def inicializar_servicios():
    try:
        URL_NUBE = st.secrets["SUPABASE_URL"]
        KEY_NUBE = st.secrets["SUPABASE_KEY"]
        GROQ_KEY = st.secrets["GROQ_API_KEY"] # <--- Usar Groq Key
        
        sb = create_client(URL_NUBE, KEY_NUBE)
        # Inicializar Cliente de Groq
        client_groq = Groq(api_key=GROQ_KEY)
        
        return sb, client_groq
    except Exception as e:
        st.error(f"Error de configuración: {e}")
        st.stop()

supabase, ai_groq = inicializar_servicios()

# --- 2. UBICACIÓN POR IP REAL ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        res = requests.get("https://ipapi.co/json/").json()
        return {"ciudad": res.get("city", "Santiago"), "pais": "Chile", "moneda": "CLP"}
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP"}

# --- 3. MOTOR DE IA (LLAMA 3.1 VIA GROQ - GRATIS Y RÁPIDO) ---
def auditoria_ia_groq(row, total_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    ciudad = geo['ciudad']
    
    # --- FILTRO DE SEGURIDAD PREVIO ---
    # Si la descripción contiene palabras que bloquean a Llama, usamos el mentor manual.
    palabras_sensibles = ["sexual", "pete", "escort", "adulto", "droga"]
    if any(p in desc.lower() for p in palabras_sensibles):
        return {
            "tipo": "Gasto Discrecional",
            "veredicto": "Privacidad absoluta",
            "analisis": f"Este es un gasto personal que la IA no puede auditar por políticas de seguridad.",
            "donde_ahorrar": "📍 Santiago: Mantén un fondo separado para gastos discrecionales para no afectar tu arriendo.",
            "plan": ["Clasificar como 'Otros'", "Establecer un tope mensual", "Revisar prioridad"],
            "color": "blue"
        }

    # PROMPT PROFESIONAL (Evita bloqueos de seguridad)
    prompt = f"""
    Eres un Asistente de Finanzas Personales experto en {ciudad}, Chile. 
    Analiza este gasto: "{desc}" por ${monto} CLP. 

    Responde ESTRICTAMENTE en JSON con esta estructura:
    {{
        "tipo": "Categoría",
        "veredicto": "Veredicto corto y útil",
        "analisis": "Análisis de por qué este gasto es relevante en Santiago",
        "donde_ahorrar": "Lugares reales en Santiago (ej: La Vega, Mayorista 10, Ferias)",
        "plan": ["Paso 1", "Paso 2", "Paso 3"],
        "color": "red" o "green" o "orange"
    }}
    """
    
    try:
        # Usamos el modelo 3.1 8B que es muy estable y menos "asustadizo"
        chat_completion = ai_groq.chat.completions.create(
            messages=[
                {"role": "system", "content": "Eres un asistente financiero chileno que solo responde en JSON."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.1,
        )
        
        texto_ia = chat_completion.choices[0].message.content
        match = re.search(r'\{.*\}', texto_ia, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            raise ValueError("No JSON detected")

    except Exception as e:
        # Fallback manual si la IA sigue bloqueada
        return {
            "tipo": "Análisis Santiago",
            "veredicto": "Mentoría Local",
            "analisis": f"Registraste ${monto} en {desc}. (IA Protegida)",
            "donde_ahorrar": "📍 Santiago: Si es comida, prefiere La Vega o Ferias. Si es transporte, usa Metro fuera de hora punta.",
            "plan": ["Comparar precios en el barrio", "Usar marcas blancas", "Revisar gastos hormiga"],
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
        cap = st.number_input(f"Captcha: {st.session_state.n1} + {st.session_state.n2}?", step=1, value=0)
        
        if st.button("Ingresar al Sistema", use_container_width=True):
            if u == "admin" and p == "1234567899" and cap == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Error: Datos incorrectos.")
                st.session_state.n1, st.session_state.n2 = random.randint(1, 10), random.randint(1, 10)

# --- 5. APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    st.sidebar.info(f"📍 Detectado en **{geo['pais']}**")
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Auditoría IA Gratis", "📊 Dashboard"])

    # Cargar datos desde Supabase
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Registro en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            cat = st.selectbox("Categoría", ["Comida", "Transporte", "Vivienda", "Ocio", "Otros"])
            monto = st.number_input("Monto (CLP)", min_value=0)
            desc = st.text_input("Descripción (Ej: Lider, Uber, Feria)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": "Gasto", "categoria": cat, "monto": monto, 
                        "descripcion": desc, "ciudad": geo['ciudad'], "moneda": "CLP"
                    }).execute()
                    st.success("✅ Gasto registrado.")
                    st.rerun()

    elif menu == "🧠 Auditoría IA Gratis":
        st.header(f"🕵️ Auditoría con Llama 3.1: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Soy tu mentor de **{geo['ciudad']}**. Analicemos tus gastos locales con IA gratuita:")
            
            for _, row in df_g.head(10).iterrows():
                with st.spinner(f"IA analizando {row['descripcion']}..."):
                    info = auditoria_ia_groq(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - ${row['monto']:,.0f}"):
                    c1, c2 = st.columns([3, 1])
                    c1.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    c2.markdown(f"**Veredicto:** `{info.get('veredicto', 'N/A')}`")
                    
                    st.write(info.get('analisis', '...'))
                    st.markdown(f"**📍 Hack en {geo['ciudad']}:**")
                    
                    color = info.get('color', 'blue')
                    hack = info.get('donde_ahorrar', 'Busca picadas.')
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    else: st.success(hack)
                    
                    st.markdown("**🚀 Plan de Acción:**")
                    for p in info.get('plan', ["Controlar gasto"]): st.write(f"- {p}")
        else:
            st.info("Sin gastos registrados.")

    elif menu == "📊 Dashboard":
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: login()
else: main()
