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

# --- 2. SEGURIDAD ---
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

# --- 4. MOTOR DE IA AVANZADA (EL CEREBRO) ---
def auditoria_ia_pro(row, total_gastos_mes, ciudad):
    desc = row['descripcion'].lower()
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    # Base de conocimiento de Mentoria
    mentoria = {
        "analisis": "Analizando gasto...",
        "tipo": "Gasto General",
        "hack": "Aplica la regla de las 48 horas antes de repetir este gasto.",
        "color": "blue"
    }

    # Lógica de Reconocimiento por Contexto
    if "pasaje" in desc or "bus" in desc or "turbus" in desc or "pullman" in desc:
        mentoria = {
            "tipo": "Logística y Viajes",
            "analisis": f"Este pasaje representa el **{impacto:.1f}%** de tus gastos. Los viajes a Santiago suelen ser un costo fijo camuflado.",
            "hack": "🇨🇱 **Hack Chile:** Compra pasajes los martes o miércoles por la App de Turbus/Pullman para obtener hasta un 30% de descuento. Si viajas seguido, inscríbete en programas de puntos.",
            "color": "orange"
        }
    elif "starbucks" in desc or "cafe" in desc or "dunkin" in desc:
        mentoria = {
            "tipo": "Gasto Hormiga (Deseo)",
            "analisis": f"Gasto de conveniencia. Aunque parece poco, un {impacto:.1f}% recurrente en café daña tu ahorro anual.",
            "hack": "☕ **Ahorro:** Si compras café fuera 3 veces por semana, gastas unos $60,000 al mes. Una prensa francesa y café de grano te costarían $15,000 mensuales.",
            "color": "red"
        }
    elif "super" in desc or "lider" in desc or "jumbo" in desc or "unimarc" in desc:
        mentoria = {
            "tipo": "Necesidad Básica",
            "analisis": "Este es un gasto esencial. Es clave optimizarlo para liberar presupuesto.",
            "hack": "🛒 **Hack:** En Chile, usa marcas propias (Líder/Great Value). Son un 40% más baratas. Evita comprar en 'horarios de hambre' para no sumar antojos.",
            "color": "green"
        }
    elif "uber" in desc or "didi" in desc or "cabify" in desc:
        mentoria = {
            "tipo": "Transporte de Conveniencia",
            "analisis": f"Has destinado un **{impacto:.1f}%** de tu presupuesto a este viaje. ¿Era una emergencia o comodidad?",
            "hack": "🚗 **Comparador:** Siempre abre Uber y Didi al mismo tiempo. En Santiago, Didi suele ser $1.500 más barato en viajes cortos.",
            "color": "orange"
        }
    elif "sexual" in desc or "pete" in desc:
        mentoria = {
            "tipo": "Entretenimiento Adulto",
            "analisis": "Gasto discrecional de alto valor. No genera retorno pero consume liquidez inmediata.",
            "hack": "⚠️ **Presupuesto:** Clasifica esto en un 'Fondo de Ocio'. Si el gasto supera el 10% de tus ingresos, estás comprometiendo tu estabilidad futura.",
            "color": "purple"
        }

    return mentoria

# --- 5. INTERFAZ LOGIN ---
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

    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro Rápido":
        st.header(f"📥 Registrar en {moneda_selec}")
        with st.form("reg_form", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input("Monto", min_value=0.0)
            desc = st.text_input("Descripción específica (Ej: Pasaje a Santiago)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({"tipo": tipo, "categoria": cat, "monto": float(monto), "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais'], "moneda": moneda_selec}).execute()
                    st.toast("Gasto registrado. Analizando...", icon="🧠")
                    time.sleep(1)
                    st.success("✅ Guardado.")
                else: st.error("Datos incompletos.")

    elif menu == "🧠 Auditoría IA":
        st.header("🕵️ Auditoría Inteligente Pro")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total_gastos_mes = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"¡Hola! He analizado tus últimos movimientos en **{geo['ciudad']}**. Abre cada gasto para ver tu plan de acción:")
            
            for _, row in df_g.head(10).iterrows():
                # Obtener mentoria de la IA
                info_ia = auditoria_ia_pro(row, total_gastos_mes, geo['ciudad'])
                
                with st.popover(f"🔍 {row['descripcion']} ({row['moneda']} {row['monto']:,.0f})"):
                    st.subheader(f"🏷️ {info_ia['tipo']}")
                    st.write(info_ia['analisis'])
                    
                    if info_ia['color'] == "red":
                        st.error(info_ia['hack'])
                    elif info_ia['color'] == "orange":
                        st.warning(info_ia['hack'])
                    elif info_ia['color'] == "green":
                        st.success(info_ia['hack'])
                    else:
                        st.info(info_ia['hack'])
                        
                    st.caption(f"Impacto en presupuesto: {(row['monto']/total_gastos_mes*100):.1f}%")
        else:
            st.info("No hay datos para auditar.")

    elif menu == "📊 Dashboard":
        st.header(f"Dashboard ({moneda_selec})")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                st.plotly_chart(px.pie(df_m[df_m['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.5))
                st.dataframe(df_m, use_container_width=True)

    elif menu == "✏️ Editar / Borrar":
        st.header("🛠️ Modificar Datos")
        if not df.empty:
            opciones = {f"{row['descripcion']} (${row['monto']}) | ID: {row['id']}": row['id'] for _, row in df.iterrows()}
            id_edit = opciones[st.selectbox("Selecciona:", list(opciones.keys()))]
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
