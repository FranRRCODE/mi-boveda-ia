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
    
    # Configuración de Gemini 1.5 Flash (El más rápido y capaz para JSON)
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
except Exception as e:
    st.error(f"❌ Error de configuración: {e}")
    st.stop()

# --- 2. UBICACIÓN REAL POR IP (DETECTA TU CIUDAD) ---
@st.cache_data(ttl=3600)
def obtener_geo_real():
    try:
        # Detectar IP real tras el proxy de Streamlit
        headers = st.context.headers
        user_ip = headers.get("X-Forwarded-For", "").split(",")[0]
        
        if user_ip:
            res = requests.get(f"http://ip-api.com/json/{user_ip}").json()
        else:
            res = requests.get("http://ip-api.com/json/").json()
            
        pais_code = res.get("countryCode", "CL")
        # Diccionario de Monedas
        monedas = {"CL": "CLP", "MX": "MXN", "CO": "COP", "AR": "ARS", "ES": "EUR", "US": "USD", "PE": "PEN"}
        
        return {
            "ciudad": res.get("city", "Santiago"),
            "pais": res.get("country", "Chile"),
            "moneda": monedas.get(pais_code, "USD"),
            "ip": res.get("query", "0.0.0.0")
        }
    except:
        return {"ciudad": "Santiago", "pais": "Chile", "moneda": "CLP", "ip": "Desconocida"}

# --- 3. MOTOR DE IA (ANÁLISIS Y OFERTAS LOCALES) ---
def auditoria_ia_local(row, total_gastos_mes, geo):
    desc = row['descripcion']
    monto = row['monto']
    moneda = row['moneda']
    impacto = (monto / total_gastos_mes) * 100 if total_gastos_mes > 0 else 0
    
    prompt = f"""
    Eres un Mentor Financiero experto en {geo['ciudad']}, {geo['pais']}.
    Analiza este gasto: "{desc}" por {moneda} {monto}. Impacto: {impacto:.1f}%.

    Responde ESTRICTAMENTE en JSON con:
    {{
        "tipo": "Categoría Creativa",
        "analisis": "Frase de impacto sobre el gasto",
        "hack_local": "Dime tiendas, ferias o apps REALES en {geo['ciudad']} donde ahorrar en esto",
        "color": "red" (innecesario), "green" (necesario), "orange" (transporte/logistica), "blue" (otros)
    }}
    """

    try:
        response = model.generate_content(prompt)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else: raise ValueError("Respuesta inválida")
    except Exception as e:
        return {
            "tipo": "Error de IA",
            "analisis": f"Error técnico: {str(e)[:40]}",
            "hack_local": f"En {geo['ciudad']} siempre es mejor comparar precios antes de comprar.",
            "color": "blue"
        }

# --- 4. SEGURIDAD: LOGIN CON CAPTCHA ---
def mostrar_login():
    st.markdown("<h1 style='text-align: center;'>🔐 Bóveda IA Mentor Pro</h1>", unsafe_allow_html=True)
    
    # Generar números aleatorios para el captcha si no existen
    if 'n1' not in st.session_state:
        st.session_state.n1 = random.randint(1, 10)
        st.session_state.n2 = random.randint(1, 10)

    with st.form("login_form"):
        u = st.text_input("Usuario Master")
        p = st.text_input("Contraseña", type="password")
        
        # El Captcha
        st.markdown(f"**Verificación de Seguridad:**")
        resultado_usuario = st.number_input(f"¿Cuánto es {st.session_state.n1} + {st.session_state.n2}?", step=1)
        
        if st.form_submit_button("Acceder al Sistema"):
            if u == "admin" and p == "1234567899" and resultado_usuario == (st.session_state.n1 + st.session_state.n2):
                st.session_state.auth = True
                st.success("Acceso concedido")
                st.rerun()
            else:
                st.error("Credenciales incorrectas o Captcha fallido.")
                # Cambiar captcha tras error
                st.session_state.n1 = random.randint(1, 10)
                st.session_state.n2 = random.randint(1, 10)

# --- 5. APP PRINCIPAL ---
def main():
    geo = obtener_geo_real()
    
    st.sidebar.title(f"🏠 Mentor en {geo['ciudad']}")
    st.sidebar.info(f"📍 Ubicación detectada por IP")
    
    moneda_selec = st.sidebar.selectbox(
        "Moneda de Trabajo:", 
        ["CLP", "USD", "MXN", "EUR", "COP", "PEN"], 
        index=["CLP", "USD", "MXN", "EUR", "COP", "PEN"].index(geo['moneda']) if geo['moneda'] in ["CLP", "USD", "MXN", "EUR", "COP", "PEN"] else 1
    )
    
    menu = st.sidebar.radio("Menú", ["➕ Registro Rápido", "🧠 Auditoría IA Local", "📊 Dashboard", "⚙️ Gestión"])

    # Cargar Datos de Supabase
    res = supabase.table("transacciones").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(res.data)

    if menu == "➕ Registro Rápido":
        st.header(f"📥 Registro en {geo['ciudad']}")
        with st.form("reg", clear_on_submit=True):
            tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
            cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
            monto = st.number_input(f"Monto ({moneda_selec})", min_value=0.0)
            desc = st.text_input("¿Qué compraste? (Ej: Supermercado Lider)")
            if st.form_submit_button("Guardar"):
                if desc and monto > 0:
                    supabase.table("transacciones").insert({
                        "tipo": tipo, "categoria": cat, "monto": float(monto), 
                        "descripcion": desc, "ciudad": geo['ciudad'], 
                        "pais": geo['pais'], "moneda": moneda_selec
                    }).execute()
                    st.toast("Guardado en la nube ☁️")
                    st.rerun()

    elif menu == "🧠 Auditoría IA Local":
        st.header(f"🕵️ Análisis Experto para {geo['ciudad']}")
        if not df.empty:
            df_g = df[df['tipo'] == 'Gasto']
            total = df_g['monto'].sum()
            
            st.chat_message("assistant").write(f"Hola, he analizado tus gastos según los precios actuales en **{geo['ciudad']}**:")
            
            for _, row in df_g.head(10).iterrows():
                with st.spinner(f"Consultando ofertas en {geo['ciudad']}..."):
                    info = auditoria_ia_local(row, total, geo)
                
                with st.expander(f"🔍 {row['descripcion']} - {row['moneda']} {row['monto']:,.0f}"):
                    st.subheader(f"🏷️ {info.get('tipo', 'Gasto')}")
                    st.write(info.get('analisis', '...'))
                    
                    st.markdown(f"**📍 Hack Local ({geo['ciudad']}):**")
                    color = info.get('color', 'blue')
                    hack = info.get('hack_local', 'Revisa ofertas en tu barrio.')
                    
                    if color == "red": st.error(hack)
                    elif color == "orange": st.warning(hack)
                    elif color == "green": st.success(hack)
                    else: st.info(hack)
        else:
            st.warning("No hay registros para auditar.")

    elif menu == "📊 Dashboard":
        st.header("📊 Inteligencia de Datos")
        if not df.empty:
            df_m = df[df['moneda'] == moneda_selec]
            if not df_m.empty:
                st.plotly_chart(px.pie(df_m[df_m['tipo']=='Gasto'], values='monto', names='categoria', hole=0.5))
                st.dataframe(df_m, use_container_width=True)

    elif menu == "⚙️ Gestión":
        st.header("🛠️ Modificar Datos")
        if not df.empty:
            opc = {f"{r['descripcion']} ({r['id']})": r['id'] for _, r in df.iterrows()}
            id_sel = opc[st.selectbox("Selecciona transacción:", list(opc.keys()))]
            reg = df[df['id'] == id_sel].iloc[0]
            with st.form("edit"):
                n_m = st.number_input("Monto", value=float(reg['monto']))
                n_d = st.text_input("Descripción", value=reg['descripcion'])
                if st.form_submit_button("Actualizar"):
                    supabase.table("transacciones").update({"monto": n_m, "descripcion": n_d}).eq("id", id_sel).execute()
                    st.rerun()
                if st.form_submit_button("Eliminar Gasto"):
                    supabase.table("transacciones").delete().eq("id", id_sel).execute()
                    st.rerun()

# --- CONTROL DE FLUJO ---
if 'auth' not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    mostrar_login()
else:
    main()
