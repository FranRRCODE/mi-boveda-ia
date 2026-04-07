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

# --- 1. CONFIGURACIÓN DE NUBE ---
try:
    # Cargar llaves desde Secrets
    URL_NUBE = st.secrets["SUPABASE_URL"]
    KEY_NUBE = st.secrets["SUPABASE_KEY"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    # Clientes
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)
    genai.configure(api_key=GEMINI_KEY)
    # Usamos flash que es más rápido y estable para este tipo de tareas
    model = genai.GenerativeModel('gemini-1.5-flash') 
except Exception as e:
    st.error(f"⚠️ Error de configuración: {e}")
    st.info("Asegúrate de tener SUPABASE_URL, SUPABASE_KEY y GEMINI_API_KEY en tus Secrets.")
    st.stop()

# --- 2. SEGURIDAD ---
USUARIO_MASTER = "admin" 
PASSWORD_MASTER = "1234567899" 

# --- 3. UBICACIÓN ---
@st.cache_data(ttl=3600)
def obtener_geo():
    try:
        # Intento obtener IP real tras el proxy de Streamlit
        res = requests.get("http://ip-api.com/json/").json()
        return {
            "ciudad": res.get("city", "Santiago"), 
            "pais": res.get("country", "Chile"), 
            "moneda": "CLP" if res.get("countryCode") == "CL" else "USD"
        }
    except: 
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP"}

# --- 4. MOTOR DE IA (CORREGIDO) ---
def auditoria_ia_gemini(row, total_gastos_mes, ciudad):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    # Prompt ultra-específico para evitar que la IA devuelva basura
    prompt = f"""
    Eres un Mentor Financiero inteligente. Analiza este gasto:
    - Item: {desc}
    - Costo: {moneda} {monto}
    - Ciudad: {ciudad}
    - Impacto: {impacto:.1f}% del presupuesto mensual.

    Responde ESTRICTAMENTE en formato JSON plano:
    {{
        "tipo": "Categoría corta",
        "analisis": "Análisis fluido de 1 oración",
        "hack": "Consejo financiero real para Chile",
        "color": "red" o "green" o "orange" o "blue"
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Limpieza de la respuesta: eliminamos bloques de código ```json ... ```
        texto = response.text
        limpio = re.search(r'\{.*\}', texto, re.DOTALL)
        if limpio:
            return json.loads(limpio.group())
        else:
            raise ValueError("No se encontró JSON en la respuesta")
            
    except Exception as e:
        # Si algo falla, registramos el error para debuggear
        return {
            "tipo": "Error de Conexión",
            "analisis": f"La IA tuvo un hipo. Error: {str(e)[:50]}",
            "hack": "Verifica que tu API Key de Gemini esté activa en Google AI Studio.",
            "color": "blue"
        }

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
    moneda_selec = st.sidebar.selectbox("Moneda de Trabajo:", ["CLP", "USD", "MXN", "EUR", "COP"])
    
    menu = st.sidebar.radio("Menú", ["➕ Registro", "🧠 Auditoría Gemini", "📊 Dashboard", "✏️ Gestionar"])

    # Cargar Datos
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro":
        st.header(f"📥 Nuevo Registro ({moneda_selec})")
        with st.form("reg", clear_on_submit=True):
            t = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            c = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            m = st.number_input("Monto", min_value=0.0)
            d = st.text_input("¿En qué gastaste? (Ej: Supermercado Lider)")
            if st.form_submit_button("Guardar"):
                if d and m > 0:
                    supabase.table("transacciones").insert({
                        "tipo": t, "categoria": c, "monto": float(m), 
                        "descripcion": d, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.success("¡Guardado exitosamente!")
                    st.rerun()

    elif menu == "🧠 Auditoría Gemini":
        st.header("🕵️ Auditoría con Gemini 1.5")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total_gastos = df_g['monto'].sum()
            
            st.info(f"Analizando tus últimos movimientos en {geo['ciudad']}...")
            
            # Solo analizamos los últimos 10 para no agotar la API
            for _, row in df_g.head(10).iterrows():
                # Llamada a la IA
                info = auditoria_ia_gemini(row, total_gastos, geo['ciudad'])
                
                with st.expander(f"🔍 {row['descripcion']} - {row['moneda']} {row['monto']:,.0f}"):
                    st.subheader(f"🏷️ {info['tipo']}")
                    st.write(info['analisis'])
                    
                    # Mostrar Hack según color
                    c = info['color']
                    if c == "red": st.error(f"💡 Hack: {info['hack']}")
                    elif c == "orange": st.warning(f"💡 Hack: {info['hack']}")
                    elif c == "green": st.success(f"💡 Hack: {info['hack']}")
                    else: st.info(f"💡 Hack: {info['hack']}")
                    
                    st.caption(f"Representa el {(row['monto']/total_gastos*100):.1f}% de tus gastos registrados.")
        else:
            st.warning("No hay gastos registrados aún.")

    elif menu == "📊 Dashboard":
        st.header("📊 Resumen Visual")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                col1, col2 = st.columns(2)
                gastos = df_m[df_m['tipo'] == 'Gasto']
                ingresos = df_m[df_m['tipo'] == 'Ingreso']
                
                col1.metric("Total Gastos", f"{moneda_selec} {gastos['monto'].sum():,.0f}")
                col2.metric("Total Ingresos", f"{moneda_selec} {ingresos['monto'].sum():,.0f}")
                
                st.plotly_chart(px.pie(gastos, values='monto', names='categoria', title="Distribución de Gastos", hole=0.4))
                st.dataframe(df_m, use_container_width=True)
            else:
                st.info(f"No hay datos para la moneda {moneda_selec}")

    elif menu == "✏️ Gestionar":
        st.header("🛠️ Editar o Borrar")
        if not df.empty:
            seleccion = st.selectbox("Selecciona transacción:", df['descripcion'] + " - " + df['id'].astype(str))
            id_sel = int(seleccion.split(" - ")[-1])
            reg = df[df['id'] == id_sel].iloc[0]
            
            with st.form("edit_form"):
                new_monto = st.number_input("Monto", value=float(reg['monto']))
                new_desc = st.text_input("Descripción", value=reg['descripcion'])
                c1, c2 = st.columns(2)
                if c1.form_submit_button("Actualizar"):
                    supabase.table("transacciones").update({"monto": new_monto, "descripcion": new_desc}).eq("id", id_sel).execute()
                    st.rerun()
                if c2.form_submit_button("Eliminar"):
                    supabase.table("transacciones").delete().eq("id", id_sel).execute()
                    st.rerun()

# --- FLUJO ---
if 'auth' not in st.session_state: st.session_state.auth = False
if not st.session_state.auth: mostrar_login()
else: main()
