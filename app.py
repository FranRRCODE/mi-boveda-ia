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

# --- 4. REACCIONES DE IA (POP-UPS) ---
def reaccion_ia_inmediata(desc, monto, moneda):
    desc = desc.lower()
    if "starbucks" in desc or "cafe" in desc:
        return "☕ ¡Cuidado! Ese café hoy pudo ser una inversión. ¿Llevaste tu termo?"
    if "uber" in desc or "didi" in desc:
        return "🚗 ¿Tarifa dinámica? La próxima vez intenta caminar si es cerca."
    if "netflix" in desc or "spotify" in desc:
        return "📺 Los suscripciones son 'vampiros' de dinero. ¡Revísalas!"
    if monto > 50000 and moneda == "CLP" or monto > 100:
        return "🚨 ¡Gasto pesado detectado! Espero que esté en el presupuesto."
    return "✅ Registro anotado. ¡El control es poder!"

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
    
    menu = st.sidebar.radio("Navegación", ["➕ Registro Rápido", "🧠 Auditoría IA", "📊 Dashboard", "✏️ Editar / Borrar"])

    # Cargar datos de la nube
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    # --- SECCIÓN A: REGISTRO CON POP-UPS ---
    if menu == "➕ Registro Rápido":
        st.header(f"📥 Nuevo Movimiento ({moneda_selec})")
        with st.form("reg_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input("Monto", min_value=0.0)
            desc = st.text_input("Descripción (Ej: Starbucks, Uber, Arriendo)")
            if st.form_submit_button("Guardar en Nube"):
                if desc and monto > 0:
                    data = {"tipo": tipo, "categoria": cat, "monto": float(monto), "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais'], "moneda": moneda_selec}
                    supabase.table("transacciones").insert(data).execute()
                    st.toast(reaccion_ia_inmediata(desc, monto, moneda_selec), icon='🤖')
                    time.sleep(1)
                    st.success("✅ Guardado.")
                else: st.error("Faltan datos.")

    # --- SECCIÓN B: AUDITORÍA IA ---
    elif menu == "🧠 Auditoría IA":
        st.header("🕵️ Auditoría Inteligente")
        if not df.empty:
            st.chat_message("assistant").write(f"¡Hola! He analizado tus movimientos en **{geo['ciudad']}**. Haz clic en los botones para ver detalles:")
            gastos_f = df[df['tipo'] == 'Gasto'].head(5)
            for _, row in gastos_f.iterrows():
                with st.popover(f"🔍 {row['descripcion']} ({row['moneda']} {row['monto']:,.0f})"):
                    st.write(f"**Categoría:** {row['categoria']}")
                    if "starbucks" in row['descripcion'].lower():
                        st.info("💡 **Tip:** Lleva tu propio termo para ahorrar dinero y ayudar al planeta.")
                    elif "uber" in row['descripcion'].lower():
                        st.warning("💡 **Tip:** Compara con Didi o usa transporte público para ahorrar un 70%.")
                    else: st.write("Gasto analizado correctamente.")
        else: st.info("Sin datos registrados.")

    # --- SECCIÓN C: DASHBOARD ---
    elif menu == "📊 Dashboard":
        st.header(f"Dashboard ({moneda_selec})")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                st.plotly_chart(px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.5))
                st.dataframe(df_m, use_container_width=True)
            else: st.warning(f"Sin registros en {moneda_selec}")

    # --- SECCIÓN D: EDITAR / BORRAR (CORREGIDA) ---
    elif menu == "✏️ Editar / Borrar":
        st.header("🛠️ Modificar o Eliminar Movimientos")
        if not df.empty:
            # Seleccionador de registros
            opciones = {f"{row['descripcion']} (${row['monto']}) | ID: {row['id']}": row['id'] for _, row in df.iterrows()}
            seleccion = st.selectbox("Selecciona el registro a corregir:", list(opciones.keys()))
            id_edit = opciones[seleccion]
            
            # Obtener datos del registro seleccionado
            reg_actual = df[df['id'] == id_edit].iloc[0]
            
            st.markdown("---")
            with st.form("form_edicion"):
                st.write(f"Editando Registro ID: {id_edit}")
                nuevo_monto = st.number_input("Nuevo Monto", value=float(reg_actual['monto']))
                nueva_desc = st.text_input("Nueva Descripción", value=reg_actual['descripcion'])
                
                col_save, col_del = st.columns(2)
                
                # Botón de Guardar
                if col_save.form_submit_button("💾 Guardar Cambios"):
                    supabase.table("transacciones").update({"monto": nuevo_monto, "descripcion": nueva_desc}).eq("id", id_edit).execute()
                    st.success("✅ Actualizado con éxito.")
                    time.sleep(1)
                    st.rerun()
                
                # Botón de Borrar
                if col_del.form_submit_button("🗑️ BORRAR PERMANENTE"):
                    supabase.table("transacciones").delete().eq("id", id_edit).execute()
                    st.warning("🗑️ Registro eliminado de la nube.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("No hay datos para editar.")

# --- CONTROL ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
