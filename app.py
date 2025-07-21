# -*- coding: utf-8 -*-
# =============================================================================
# ANALISTA DE VENTAS IA - ARCHIVO PRINCIPAL
# =============================================================================
# Responsabilidad: Orquestar la aplicación, construir la interfaz de usuario
# y llamar a los módulos correspondientes para realizar las tareas.
# =============================================================================

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os

# Importar nuestras funciones y clases desde los otros archivos
from kommo_api import get_api_data
from data_processor import procesar_datos
from pdf_generator import ReportGenerator, enviar_correo

# --- Configuración de la página ---
st.set_page_config(
    page_title="Analista de Ventas IA",
    page_icon="🤖",
    layout="wide"
)

# --- Función de carga principal con caché de Streamlit ---
@st.cache_data(ttl=3600) # Cache por 1 hora
def cargar_y_procesar_datos():
    """
    Carga las credenciales de forma segura desde st.secrets y luego
    obtiene y procesa los datos de la API.
    """
    try:
        subdomain = st.secrets["KOMMO_SUBDOMAIN"]
        access_token = st.secrets["KOMMO_ACCESS_TOKEN"]
    except KeyError as e:
        st.error(f"Error: La credencial '{e}' no se encontró en tu archivo .streamlit/secrets.toml.")
        st.error("Asegúrate de que el archivo exista y que los nombres de las claves sean correctos.")
        return None

    base_url = f"https://{subdomain}.kommo.com/api/v4"
    headers = {'Authorization': f"Bearer {access_token}"}

    api_data = get_api_data(base_url, headers)
    if api_data:
        df = procesar_datos(api_data)
        return df
    return None

# --- Inicialización del estado de la sesión ---
if 'generated_file' not in st.session_state:
    st.session_state.generated_file = None

# --- Interfaz Principal ---
st.title("🤖 Analista de Ventas IA")
st.markdown("### Grúas Móviles del Golfo")

df_master = cargar_y_procesar_datos()

if df_master is not None and not df_master.empty:
    st.sidebar.success(f"✅ Conectado. {len(df_master)} leads cargados.")
    reporter = ReportGenerator(df_master)

    st.sidebar.title("Panel de Control")
    opcion = st.sidebar.radio(
        "Elige una opción:",
        ('Análisis por Periodo', 'Reporte Histórico Completo', 'Comparar Periodos'),
        key='report_option' # Key para que el estado no se reinicie al cambiar de opción
    )

    # --- Lógica para cada opción del panel ---
    if opcion == 'Análisis por Periodo':
        st.sidebar.markdown("---")
        start_date = st.sidebar.date_input("Fecha de inicio", df_master['created_at'].min())
        end_date = st.sidebar.date_input("Fecha de fin", df_master['created_at'].max())
        
        if st.sidebar.button("Generar Reporte por Periodo"):
            df_periodo = df_master[(df_master['created_at'].dt.date >= start_date) & (df_master['created_at'].dt.date <= end_date)]
            filename = f"Reporte_Kommo_{start_date}_a_{end_date}.pdf"
            title = f"Análisis del Periodo {start_date} a {end_date}"
            
            with st.spinner("Generando reporte PDF..."):
                st.session_state.generated_file = reporter.generar_reporte_por_fechas(df_periodo, filename, title)

    elif opcion == 'Reporte Histórico Completo':
        st.sidebar.markdown("---")
        if st.sidebar.button("Generar Reporte Histórico"):
            with st.spinner("Generando reporte histórico..."):
                filename = "Reporte_Historico_Kommo.pdf"
                st.session_state.generated_file = reporter.generar_reporte_por_fechas(df_master, filename, "Análisis Histórico General")
            
    elif opcion == 'Comparar Periodos':
        st.sidebar.markdown("---")
        st.sidebar.subheader("Periodo Actual (A)")
        start_a = st.sidebar.date_input("Fecha de inicio (A)", df_master['created_at'].max().date() - timedelta(days=6))
        end_a = st.sidebar.date_input("Fecha de fin (A)", df_master['created_at'].max().date())
        
        st.sidebar.subheader("Periodo Anterior (B)")
        auto_mode = st.sidebar.checkbox("Calcular periodo anterior automáticamente", True)
        
        if auto_mode:
            delta = end_a - start_a
            start_b = start_a - delta - timedelta(days=1)
            end_b = end_a - delta - timedelta(days=1)
            st.sidebar.info(f"Periodo anterior calculado: {start_b.strftime('%Y-%m-%d')} a {end_b.strftime('%Y-%m-%d')}")
        else:
            start_b = st.sidebar.date_input("Fecha de inicio (B)", df_master['created_at'].max().date() - timedelta(days=14))
            end_b = st.sidebar.date_input("Fecha de fin (B)", df_master['created_at'].max().date() - timedelta(days=8))

        if st.sidebar.button("Generar Reporte Comparativo"):
            df_a = df_master[(df_master['created_at'].dt.date >= start_a) & (df_master['created_at'].dt.date <= end_a)]
            df_b = df_master[(df_master['created_at'].dt.date >= start_b) & (df_master['created_at'].dt.date <= end_b)]
            
            filename = f"Reporte_Comparativo_{start_a.strftime('%Y-%m-%d')}_vs_{start_b.strftime('%Y-%m-%d')}.pdf"
            
            with st.spinner("Generando reporte comparativo..."):
                st.session_state.generated_file = reporter.generar_reporte_comparativo(df_a, df_b, f"{start_a.strftime('%Y-%m-%d')} a {end_a.strftime('%Y-%m-%d')}", f"{start_b.strftime('%Y-%m-%d')} a {end_b.strftime('%Y-%m-%d')}", filename)

    # --- Sección de Descarga y Envío (si se ha generado un archivo) ---
    if st.session_state.generated_file:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Acciones del Reporte")
        
        with open(st.session_state.generated_file, "rb") as pdf_file:
            st.sidebar.download_button(
                label="Descargar Reporte", data=pdf_file,
                file_name=os.path.basename(st.session_state.generated_file), mime="application/octet-stream"
            )

        with st.sidebar.form(key='email_form'):
            recipient = st.text_input("Correo del destinatario", value=st.secrets.get('email_settings', {}).get('recipient_email', ''))
            submit_button = st.form_submit_button(label='Enviar por Correo')

            if submit_button:
                if recipient:
                    asunto = f"Reporte de Ventas: {os.path.basename(st.session_state.generated_file)}"
                    cuerpo = "Adjunto se encuentra el reporte de análisis de ventas solicitado."
                    enviar_correo(recipient, asunto, cuerpo, st.session_state.generated_file)
                else:
                    st.warning("Por favor, introduce un correo electrónico.")

    st.markdown("---")
    st.header("Chat con tu Analista IA (Próximamente)")
    st.info("En la siguiente fase, podrás hacer preguntas en lenguaje natural aquí.")

else:
    st.sidebar.error("❌ No se pudieron cargar los datos. Revisa las credenciales en .streamlit/secrets.toml")