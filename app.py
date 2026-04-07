import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import random
import time
import google.generativeai as genai  # <--- Nueva Librería
import json

# --- 1. CONFIGURACIÓN DE NUBE Y IA ---
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"] # <--- Añadir en Secrets
    
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    
    # Configurar Gemini
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') # Modelo rápido y eficiente
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

# --- 4. NUEVO MOTOR DE IA CON GEMINI ---
def auditoria_ia_gemini(row, total_gastos_mes, ciudad):
    """
    Usa Google Gemini para analizar el gasto de forma fluida.
    """
    monto = row['monto']
    desc = row['descripcion']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    # Prompt diseñado para obtener una respuesta estructurada
    prompt = f"""
    Eres un mentor financiero experto, sarcástico pero útil, basado en {ciudad}.
    Analiza el siguiente gasto de un usuario:
    - Descripción: "{desc}"
    - Monto: {moneda} {monto}
    - Porcentaje del gasto total del mes: {impacto:.2f}%
    
    Responde estrictamente en formato JSON con la siguiente estructura:
    {{
        "tipo": "Categoría creativa del gasto",
        "analisis": "Un análisis corto y fluido de por qué este gasto importa o cómo afecta las finanzas.",
        "hack": "Un consejo práctico, específico para Chile/Latam y nada genérico.",
        "color": "red (si es crítico/hormiga), green (si es necesario), orange (si es transporte/logistica), blue (otros)"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Limpiar la respuesta por si Gemini añade ```json ... ```
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(texto_limpio)
    except Exception as e:
        # Fallback en caso de error de la API
        return {
            "tipo": "Gasto General",
            "analisis": f"No pude conectar con el cerebro de la IA, pero veo que gastaste {monto}.",
            "hack": "Intenta registrar tus gastos con descripciones más claras.",
            "color": "blue"
        }

# --- 5. INTERFAZ LOGIN (Igual que antes) ---
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
            else: st.error("Datos incorrectos.")

# --- 6. APP PRINCIPAL ---
def main():
    geo = obtener_geo()
    st.sidebar.title(f"📍 Mentor en {geo['ciudad']}")
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR", "COP"])
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro Rápido", "🧠 Auditoría IA", "📊 Dashboard", "✏️ Editar / Borrar"])

    # Obtener datos de Supabase
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro Rápido":
        st.header(f"📥 Registrar en {moneda_selec}")
        with st.form("reg_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input("Monto", min_value=0.0)
            desc = st.text_input("Descripción específica (Ej: Starbucks de la mañana)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.toast("Gasto registrado. Gemini está pensando...", icon="🧠")
                    time.sleep(1)
                    st.success("✅ Guardado.")
                else: st.error("Datos incompletos.")

    elif menu == "🧠 Auditoría IA":
        st.header("🕵️ Auditoría con Gemini 1.5 Pro")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total_gastos_mes = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"¡Hola! Soy tu mentor IA. He analizado tus últimos movimientos en **{geo['ciudad']}**. Haz clic en cada uno para ver mi análisis real:")
            
            for _, row in df_g.head(8).iterrows():
                # Llamada a Gemini
                with st.spinner(f"Analizando '{row['descripcion']}'..."):
                    info_ia = auditoria_ia_gemini(row, total_gastos_mes, geo['ciudad'])
                
                with st.popover(f"🔍 {row['descripcion']} ({row['moneda']} {row['monto']:,.0f})"):
                    st.subheader(f"🏷️ {info_ia.get('tipo', 'Gasto')}")
                    st.write(info_ia.get('analisis', 'Sin análisis disponible.'))
                    
                    color = info_ia.get('color', 'blue')
                    hack = info_ia.get('hack', 'No hay hacks por ahora.')
                    
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    elif color == "green": st.success(hack)
                    else: st.info(hack)
                        
                    st.caption(f"Impacto real: {(row['monto']/total_gastos_mes*100):.1f}% de tus gastos.")
        else:
            st.info("No hay datos para auditar.")

    elif menu == "📊 Dashboard":
        # ... (Código de Dashboard igual que antes)
        st.header(f"Dashboard ({moneda_selec})")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                st.plotly_chart(px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.5))
                st.dataframe(df_m, use_container_width=True)

    elif menu == "✏️ Editar / Borrar":
        # ... (Código de Editar igual que antes)
        st.header("🛠️ Modificar Datos")
        if not df.empty:
            opciones = {f"{row['descripcion']} (${row['monto']}) | ID: {row['id']}": row['id'] for _, row in df.iterrows()}
            id_sel = st.selectbox("Selecciona:", list(opciones.keys()))
            id_edit = opciones[id_sel]
            reg = df[df['id'] == id_edit].iloc[0]
            with st.form("edit"):
                n_m = st.number_input("Monto", value=float(reg['monto']))
                n_d = st.text_input("Descripción", value=reg['descripcion'])
                c1, c2 = st.columns(2)
                if c1.form_submit_button("Guardar"):
                    supabase.table("transacciones").update({"monto": n_m, "descripcion": n_d}).eq("id", id_edit).execute()
                    st.rerun()
                if c2.form_submit_button("Borrar"):
                    supabase.table("transacciones").delete().eq("id", id_edit).execute()
                    st.rerun()

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
