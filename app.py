# -*- coding: utf-8 -*-
# =============================================================================
# ANALISTA DE VENTAS IA - ARCHIVO PRINCIPAL
# =============================================================================
# Responsabilidad: Orquestar la aplicación, construir la interfaz de usuario
# y llamar a los módulos correspondientes para realizar las tareas.
# =============================================================================

import streamlit as st
from datetime import datetime, timedelta

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
    try:
        subdomain = st.secrets["KOMMO_SUBDOMAIN"]
        access_token = st.secrets["KOMMO_ACCESS_TOKEN"]
    except FileNotFoundError:
        st.error("Archivo 'secrets.toml' no encontrado. Por favor, créalo en la carpeta '.streamlit'.")
        return None
    except KeyError as e:
        st.error(f"Error: La credencial '{e}' no se encontró en tu archivo 'secrets.toml'.")
        return None

    api_data = get_api_data(
        base_url=f"https://{subdomain}.kommo.com/api/v4",
        headers={'Authorization': f"Bearer {access_token}"}
    )
    df = procesar_datos(api_data)
    return df

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
        ('Análisis por Periodo', 'Reporte Histórico Completo', 'Comparar Periodos')
    )

    if opcion == 'Análisis por Periodo':
        st.sidebar.markdown("---")
        start_date = st.sidebar.date_input("Fecha de inicio", df_master['created_at'].min())
        end_date = st.sidebar.date_input("Fecha de fin", df_master['created_at'].max())
        
        if st.sidebar.button("Generar Reporte por Periodo"):
            df_periodo = df_master[(df_master['created_at'].dt.date >= start_date) & (df_master['created_at'].dt.date <= end_date)]
            filename = f"Reporte_Kommo_{start_date}_a_{end_date}.pdf"
            title = f"Análisis del Periodo {start_date} a {end_date}"
            
            with st.spinner("Generando reporte PDF..."):
                generated_file = reporter.generar_reporte_por_fechas(df_periodo, filename, title)
            
            if generated_file:
                with open(generated_file, "rb") as pdf_file:
                    st.sidebar.download_button(
                        label="Descargar Reporte", data=pdf_file,
                        file_name=generated_file, mime="application/octet-stream"
                    )
                if st.sidebar.button("Enviar por Correo"):
                     with st.spinner("Enviando correo..."):
                        enviar_correo(f"Reporte de Ventas: {start_date} a {end_date}", "Adjunto reporte de ventas.", generated_file)

    elif opcion == 'Reporte Histórico Completo':
        st.sidebar.markdown("---")
        if st.sidebar.button("Generar Reporte Histórico"):
            with st.spinner("Generando reporte histórico..."):
                filename = "Reporte_Historico_Kommo.pdf"
                generated_file = reporter.generar_reporte_por_fechas(df_master, filename, "Análisis Histórico General")
            
            if generated_file:
                with open(generated_file, "rb") as pdf_file:
                    st.sidebar.download_button(
                        label="Descargar Reporte Histórico", data=pdf_file,
                        file_name=generated_file, mime="application/octet-stream"
                    )
                if st.sidebar.button("Enviar Histórico por Correo"):
                    with st.spinner("Enviando correo..."):
                        enviar_correo("Reporte Histórico de Ventas", "Adjunto reporte histórico de ventas.", generated_file)

    elif opcion == 'Comparar Periodos':
        st.sidebar.markdown("---")
        st.sidebar.subheader("Periodo Actual (A)")
        start_a = st.sidebar.date_input("Fecha de inicio (A)", df_master['created_at'].max() - timedelta(days=7))
        end_a = st.sidebar.date_input("Fecha de fin (A)", df_master['created_at'].max())
        
        st.sidebar.subheader("Periodo Anterior (B)")
        auto_mode = st.sidebar.checkbox("Calcular periodo anterior automáticamente", True)
        
        if auto_mode:
            delta = end_a - start_a
            start_b = start_a - delta - timedelta(days=1)
            end_b = end_a - delta - timedelta(days=1)
            st.sidebar.info(f"Periodo anterior calculado: {start_b.strftime('%Y-%m-%d')} a {end_b.strftime('%Y-%m-%d')}")
        else:
            start_b = st.sidebar.date_input("Fecha de inicio (B)", df_master['created_at'].max() - timedelta(days=14))
            end_b = st.sidebar.date_input("Fecha de fin (B)", df_master['created_at'].max() - timedelta(days=8))

        if st.sidebar.button("Generar Reporte Comparativo"):
            df_a = df_master[(df_master['created_at'].dt.date >= start_a) & (df_master['created_at'].dt.date <= end_a)]
            df_b = df_master[(df_master['created_at'].dt.date >= start_b) & (df_master['created_at'].dt.date <= end_b)]
            
            filename = f"Reporte_Comparativo_{start_a.strftime('%Y-%m-%d')}_vs_{start_b.strftime('%Y-%m-%d')}.pdf"
            
            with st.spinner("Generando reporte comparativo..."):
                # La función de comparación aún no está en pdf_generator.py, la añadiremos después.
                # Por ahora, esto es un placeholder.
                st.warning("La generación de reportes comparativos está en desarrollo.")
                generated_file = None

            if generated_file:
                with open(generated_file, "rb") as pdf_file:
                    st.sidebar.download_button(
                        label="Descargar Comparativo", data=pdf_file,
                        file_name=generated_file, mime="application/octet-stream"
                    )
                if st.sidebar.button("Enviar Comparativo por Correo"):
                    with st.spinner("Enviando correo..."):
                        enviar_correo("Reporte Comparativo de Ventas", "Adjunto reporte comparativo de ventas.", generated_file)

    st.markdown("---")
    st.header("Chat con tu Analista IA (Próximamente)")
    st.info("En la siguiente fase, podrás hacer preguntas en lenguaje natural aquí.")

else:
    st.sidebar.error("❌ No se pudieron cargar los datos. Revisa las credenciales en .streamlit/secrets.toml")
