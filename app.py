import streamlit as st
from supabase import create_client, Client
import pandas as pd
import plotly.express as px
import requests
import random
import time
from datetime import datetime

# --- 1. CONFIGURACIÓN DE NUBE ---
try:
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
except Exception:
    st.error("⚠️ Configura tus Secrets en Streamlit Cloud.")
    st.stop()

# --- 2. CONFIGURACIÓN DE SEGURIDAD ---
USUARIO_MASTER = "admin" 
PASSWORD_MASTER = "1234567899" 

# --- 3. UBICACIÓN AUTOMÁTICA ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        res = requests.get(f"http://ip-api.com/json/{user_ip}").json()
        return {"ciudad": res.get("city", "Santiago"), "pais": res.get("country", "Chile"), "moneda": "CLP" if res.get("countryCode") == "CL" else "USD"}
    except: return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP"}

# --- 4. MOTOR DE IA INTERACTIVA (REACCIONES) ---
def reaccion_ia_inmediata(desc, monto, moneda):
    desc = desc.lower()
    if "starbucks" in desc or "cafe" in desc:
        return "☕ ¡Cuidado! Ese café hoy pudo ser una inversión a futuro. ¿Llevaste tu termo?"
    if "uber" in desc or "didi" in desc:
        return "🚗 ¿Había mucha tarifa dinámica? La próxima vez intenta caminar si es cerca."
    if "netflix" in desc or "spotify" in desc:
        return "📺 Las suscripciones son 'vampiros' de dinero. ¡Revísalas!"
    if monto > 50000 and moneda == "CLP" or monto > 100:
        return "🚨 ¡Gasto pesado detectado! Espero que haya estado en el presupuesto."
    return "✅ Registro anotado. ¡Sigue así, el control es poder!"

# --- 5. INTERFAZ LOGIN ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Bóveda IA Interactiva</h1>", unsafe_allow_html=True)
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
    st.sidebar.title(f"📍 {geo['ciudad']}")
    moneda_selec = st.sidebar.selectbox("Moneda:", ["CLP", "USD", "MXN", "EUR", "COP", "ARS"])
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro Rápido", "🧠 Auditoría IA", "📊 Dashboard", "✏️ Editar"])

    # Cargar datos de la nube
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    # --- A: REGISTRO CON POP-UPS (TOASTS) ---
    if menu == "➕ Registro Rápido":
        st.header(f"📥 Nuevo Gasto en {moneda_selec}")
        
        with st.form("reg_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input("Monto", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Starbucks, Uber, Arriendo)")
            
            if st.form_submit_button("Guardar en Nube"):
                if desc and monto > 0:
                    data = {"tipo": tipo, "categoria": cat, "monto": float(monto), "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais'], "moneda": moneda_selec}
                    supabase.table("transacciones").insert(data).execute()
                    
                    # --- INTERACTIVIDAD: POP-UP (TOAST) ---
                    reaccion = reaccion_ia_inmediata(desc, monto, moneda_selec)
                    st.toast(reaccion, icon='🤖')
                    time.sleep(1)
                    st.success("✅ Guardado con éxito.")
                else:
                    st.error("Faltan datos.")

    # --- B: AUDITORÍA INTERACTIVA (CHATS Y POPOVERS) ---
    elif menu == "🧠 Auditoría IA":
        st.header("🕵️ Auditoría de Gastos Inteligente")
        
        if not df.empty:
            st.chat_message("assistant").write(f"Hola! He analizado tus últimos movimientos en **{geo['ciudad']}**. Aquí tienes mis hallazgos:")
            
            # Usar Popovers para cada hallazgo
            gastos_f = df[df['tipo'] == 'Gasto'].head(5)
            for _, row in gastos_f.iterrows():
                with st.popover(f"🔍 Análisis: {row['descripcion']} ({row['moneda']} {row['monto']:,.0f})"):
                    st.write(f"**Categoría:** {row['categoria']}")
                    st.write(f"**Fecha:** {row['fecha']}")
                    st.markdown("---")
                    # Lógica personalizada
                    if "starbucks" in row['descripcion'].lower():
                        st.info("💡 **Consejo:** El gasto en marcas de lujo de café puede representar el 15% de tu ahorro mensual. ¡Intenta usar la App para puntos!")
                    elif "uber" in row['descripcion'].lower():
                        st.warning("💡 **Alternativa:** En horas valle, caminar o usar transporte público te ahorraría el 70% de este monto.")
                    else:
                        st.write("El gasto parece normal, pero recuerda siempre pedir boleta para control de impuestos.")

            # Resumen interactivo
            total_g = df[df['tipo'] == 'Gasto']['monto'].sum()
            with st.chat_message("user"):
                st.write(f"¿Cuál es mi situación general?")
            
            with st.chat_message("assistant"):
                if total_g > 500000: # Ejemplo CLP
                    st.error("Estás gastando por encima del promedio. Necesitamos un plan de recorte urgente.")
                else:
                    st.success("Vas por buen camino. Tu flujo de caja está saludable.")
        else:
            st.info("Registra datos para que la IA pueda hablarte.")

    # --- C: DASHBOARD ---
    elif menu == "📊 Dashboard":
        st.header("📊 Tu Salud Financiera")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                st.plotly_chart(px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.5, title="Gastos por Categoría"))
                st.dataframe(df_m, use_container_width=True)
            else: st.warning(f"No hay registros en {moneda_selec}")

    # --- D: EDITAR ---
    elif menu == "✏️ Editar":
        st.header("🛠️ Corregir Datos")
        if not df.empty:
            opciones = {f"{row['descripcion']} (${row['monto']})": row['id'] for _, row in df.iterrows()}
            id_e = opciones[st.selectbox("Selecciona:", list(opciones.keys()))]
            reg = df[df['id'] == id_e].iloc[0]
            with st.form("edit"):
                m_n = st.number_input("Nuevo Monto", value=float(reg['monto']))
                d_n = st.text_input("Nueva Descrip.", value=reg['descripcion'])
                if st.form_submit_button("Actualizar"):
                    supabase.table("transacciones").update({"monto": m_n, "descripcion": d_n}).eq("id", id_e).execute()
                    st.rerun()

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
