    import streamlit as st
    from supabase import create_client, Client
    import pandas as pd
    import plotly.express as px
    import requests
    import yfinance as yf
    import hashlib
    import random
    from datetime import datetime

    # --- CONFIGURACIÓN DE SUPABASE (PEGA TUS LLAVES AQUÍ) ---
    URL_NUBE = "https://ouyaffquhvfkzwlqlcoi.supabase.co"
    KEY_NUBE = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im91eWFmZnF1aHZma3p3bHFsY29pIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU1MjU1NDEsImV4cCI6MjA5MTEwMTU0MX0.ZOh6q1ae5bWiFLw10iKF2Qijo-oAn67IXjl6TmVecOA"
    supabase: Client = create_client(URL_NUBE, KEY_NUBE)

    # --- CONFIGURACIÓN DE USUARIO (CAMBIA ESTO) ---
    USUARIO_MASTER = "FranciscoRR" 
    PASSWORD_MASTER = "1212@@2020" # Cambia esta por una real

    def generar_hash(texto):
        return hashlib.sha256(str.encode(texto)).hexdigest()

    # --- FUNCIONES DE UBICACIÓN ---
    def obtener_geo():
        try:
            res = requests.get('https://ipapi.co/json/').json()
            return {"ciudad": res.get("city"), "pais": res.get("country_name"), "code": res.get("country"), "moneda": res.get("currency")}
        except:
            return {"ciudad": "Desconocida", "pais": "Global", "code": "US", "moneda": "USD"}

    # --- LÓGICA DE IA Y RECOMENDACIONES ---
    def analizar_ia_personalizado(desc, monto, geo):
        desc = desc.lower()
        pais = geo['code']
        
        # Base de conocimiento (Hacks Específicos)
        hacks = {
            "starbucks": "☕ **Hack IA:** Gastar mucho en café de marca reduce tu capacidad de inversión un 10% anual. Usa un termo propio para descuentos.",
            "netflix": "📺 **Optimización:** ¿Ves Netflix a diario? Si no, activa el plan con anuncios o rota meses entre apps.",
            "uber": "🚗 **Movilidad:** Compara con Didi antes de pedir. En tu zona, las tarifas varían hasta un 20%.",
            "doggis": "🌭 **Tip Local (Chile):** Usa los cupones de la App los miércoles de 2x1.",
            "amazon": "📦 **Compra Online:** Usa comparadores de precios históricos. No compres por impulso.",
            "supermercado": "🛒 **Súper:** Compra marcas blancas; ahorras un 30% en productos básicos.",
            "servicios sexuales": "⚠️ **Gestión Riesgo:** Este es un gasto discrecional alto. Pon un tope mensual para no afectar tu renta."
        }
        
        for clave in hacks:
            if clave in desc:
                return hacks[clave]
        
        return f"🔍 **Análisis General:** Gasto en {geo['ciudad']}. Aplica la regla de las 48h antes de comprar esto de nuevo."

    # --- INTERFAZ DE LOGIN CON CAPTCHA ---
    def mostrar_login():
        st.markdown("<h1 style='text-align: center;'>🔐 IA Finance Secure Access</h1>", unsafe_allow_html=True)
        
        if 'c_n1' not in st.session_state:
            st.session_state.c_n1 = random.randint(1, 10)
            st.session_state.c_n2 = random.randint(1, 10)

        with st.form("login"):
            u = st.text_input("Usuario")
            p = st.text_input("Contraseña", type="password")
            captcha = st.number_input(f"🤖 Captcha Anti-Bot: ¿Cuánto es {st.session_state.c_n1} + {st.session_state.c_n2}?", step=1)
            
            if st.form_submit_button("Entrar a mi Bóveda"):
                if captcha == (st.session_state.c_n1 + st.session_state.c_n2):
                    if u == USUARIO_MASTER and p == PASSWORD_MASTER:
                        st.session_state.auth = True
                        st.success("Acceso Correcto")
                        st.rerun()
                    else:
                        st.error("Credenciales Incorrectas")
                else:
                    st.error("Captcha Incorrecto")
                    st.session_state.c_n1 = random.randint(1, 10)
                    st.session_state.c_n2 = random.randint(1, 10)

    # --- APP PRINCIPAL ---
    def main():
        st.set_page_config(page_title="IA Finance Master", layout="wide")
        geo = obtener_geo()
        
        st.sidebar.title(f"📍 {geo['ciudad']}, {geo['pais']}")
        menu = st.sidebar.radio("Navegación", ["➕ Registro", "🧠 Inteligencia Financiera", "📊 Dashboard"])
        
        if st.sidebar.button("Cerrar Sesión"):
            st.session_state.auth = False
            st.rerun()

        if menu == "➕ Registro":
            st.header("📥 Nuevo Registro en la Nube")
            with st.form("reg", clear_on_submit=True):
                tipo = st.selectbox("Tipo", ["Gasto", "Ingreso"])
                cat = st.selectbox("Categoría", ["Comida", "Vivienda", "Ocio", "Transporte", "Sueldo", "Otros"])
                monto = st.number_input(f"Monto ({geo['moneda']})", min_value=0.0)
                desc = st.text_input("Descripción específica")
                if st.form_submit_button("Guardar"):
                    data = {"tipo": tipo, "categoria": cat, "monto": monto, "descripcion": desc, "ciudad": geo['ciudad'], "pais": geo['pais']}
                    supabase.table("transacciones").insert(data).execute()
                    st.success("Guardado en Supabase (Nube)")

        elif menu == "🧠 Inteligencia Financiera":
            st.header("🤖 Análisis de Mentoría IA")
            res = supabase.table("transacciones").select("*").execute()
            df = pd.DataFrame(res.data)
            
            if not df.empty:
                for _, row in df[df['tipo'] == 'Gasto'].tail(10).iterrows():
                    with st.expander(f"📌 {row['descripcion']} - ${row['monto']}"):
                        st.write(analizar_ia_personalizado(row['descripcion'], row['monto'], geo))
            else:
                st.info("Sin datos.")

        elif menu == "📊 Dashboard":
            st.header("Análisis Gráfico")
            res = supabase.table("transacciones").select("*").execute()
            df = pd.DataFrame(res.data)
            if not df.empty:
                fig = px.pie(df[df['tipo'] == 'Gasto'], values='monto', names='categoria', hole=0.4)
                st.plotly_chart(fig)
                st.dataframe(df)

    # --- CONTROLADOR ---
    if 'auth' not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        mostrar_login()
    else:
        main()