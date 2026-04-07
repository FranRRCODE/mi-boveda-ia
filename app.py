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
    
    # Configuración de Gemini
    genai.configure(api_key=GEMINI_KEY)
    # Usamos 1.5 Flash que es el más moderno y potente actualmente
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
except Exception as e:
    st.error(f"❌ Error crítico de configuración: {e}")
    st.stop()

# --- 2. UBICACIÓN REAL POR IP ---
@st.cache_data(ttl=3600)
def obtener_geo_avanzada():
    """Detecta la ubicación real del usuario, no la del servidor."""
    try:
        # Intentamos obtener la IP del cliente a través de los headers de Streamlit
        user_ip = st.context.headers.get("X-Forwarded-For")
        if user_ip:
            user_ip = user_ip.split(",")[0]
            res = requests.get(f"http://ip-api.com/json/{user_ip}").json()
        else:
            # Fallback si no detecta header
            res = requests.get("http://ip-api.com/json/").json()
        
        pais_code = res.get("countryCode", "CL")
        
        # Mapeo de monedas por país
        monedas = {
            "CL": "CLP", "MX": "MXN", "CO": "COP", "AR": "ARS", 
            "ES": "EUR", "US": "USD", "PE": "PEN"
        }
        
        return {
            "ciudad": res.get("city", "Santiago"),
            "pais": res.get("country", "Chile"),
            "moneda": monedas.get(pais_code, "USD"),
            "ip": res.get("query", "0.0.0.0")
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP", "ip": "Local"}

# --- 3. MOTOR DE IA (DETERMINA OFERTAS LOCALES) ---
def auditoria_ia_pro(row, total_gastos_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    # El Prompt ahora obliga a buscar ofertas locales según la ciudad
    prompt = f"""
    Eres un Mentor Financiero experto en la ciudad de {geo['ciudad']}, {geo['pais']}.
    El usuario gastó {moneda} {monto} en: "{desc}". 
    Este gasto representa el {impacto:.1f}% de su mes.

    TAREA:
    1. Clasifica el gasto.
    2. Da un análisis financiero crudo.
    3. RECOMIENDA OFERTAS O TIENDAS REALES en {geo['ciudad']} donde este gasto sea más barato 
       (Ej: si es super en Chile, menciona Lider o ferias libres; si es en México, Bodega Aurrera, etc).

    Responde ESTRICTAMENTE en este formato JSON:
    {{
        "tipo": "Categoría",
        "analisis": "Frase de impacto",
        "hack_local": "Oferta o tienda específica en {geo['ciudad']} para ahorrar",
        "color": "red" o "green" o "orange" o "blue"
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Extraer JSON limpiamente
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else: raise ValueError("Respuesta no válida")
    except Exception as e:
        # DETECTOR DE ERROR REAL (Para debug)
        return {
            "tipo": "Error de Diagnóstico",
            "analisis": f"No pude conectar con Gemini. Error: {str(e)[:50]}",
            "hack_local": "Revisa si tu API KEY en Google AI Studio tiene permisos para 'Gemini 1.5 Flash'.",
            "color": "red"
        }

# --- 4. APP PRINCIPAL ---
def main():
    geo = obtener_geo_avanzada()
    
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    st.sidebar.caption(f"📍 IP: {geo['ip']} | 🌎 {geo['pais']}")
    
    # Selección de moneda (Default según IP)
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR", "COP", "PEN"], index=["CLP", "USD", "MXN", "EUR", "COP", "PEN"].index(geo['moneda']) if geo['moneda'] in ["CLP", "USD", "MXN", "EUR", "COP", "PEN"] else 1)
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro Rápido", "🧠 Auditoría Local IA", "📊 Dashboard"])

    # Cargar Datos
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro Rápido":
        st.header(f"📥 Registrar Gasto en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input(f"Monto ({moneda_selec})", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Compra de carne en el super)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.success("Registrado. ¡Gemini está analizando tu zona!")
                    st.rerun()

    elif menu == "🧠 Auditoría Local IA":
        st.header(f"🕵️ Auditoría Especializada: {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"He detectado que estás en **{geo['ciudad']}**. Aquí tienes mi análisis de tus gastos locales:")
            
            for _, row in df_g.head(8).iterrows():
                with st.spinner(f"Buscando ofertas en {geo['ciudad']}..."):
                    info = auditoria_ia_pro(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - {row['moneda']} {row['monto']:,.0f}"):
                    st.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    st.write(info.get('analisis', '...'))
                    
                    # Hack Local basado en la ciudad detectada por IP
                    st.markdown(f"**📍 Hack para {geo['ciudad']}:**")
                    c = info.get('color', 'blue')
                    h = info.get('hack_local', 'No hay ofertas detectadas.')
                    
                    if c == "red": st.error(h)
                    elif c == "orange": st.warning(h)
                    elif c == "green": st.success(h)
                    else: st.info(h)

    elif menu == "📊 Dashboard":
        st.header("📊 Resumen General")
        if not df.empty:
            st.plotly_chart(px.pie(df[df['tipo']=='Gasto'], values='monto', names='categoria', hole=0.4))
            st.dataframe(df, use_container_width=True)

# --- SEGURIDAD ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("🔐 Bóveda IA")
    u = st.text_input("Usuario")
    p = st.text_input("Password", type="password")
    if st.button("Entrar"):
        if u == "admin" and p == "1234567899":
            st.session_state.auth = True
            st.rerun()
else:
    main()
