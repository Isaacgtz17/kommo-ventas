# -*- coding: utf-8 -*-

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import os
# Asegúrate de que las funciones importadas sean las correctas
from pdf_generator import ReportGenerator, enviar_correo 
# Asumimos que app.py tiene la función de carga de datos
from PaginaPrincipal import cargar_y_procesar_datos 

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Generador de Reportes", 
    page_icon="📄",
    layout="wide"
)

# --- Funciones Auxiliares ---
def get_date_range(period, min_date, max_date):
    """Calcula el rango de fechas basado en un periodo predefinido."""
    today = datetime.now().date()
    
    if period == "Hoy":
        return today, today
    elif period == "Ayer":
        start = today - timedelta(days=1)
        return start, start
    elif period == "Últimos 7 días":
        start = today - timedelta(days=6)
        return start, today
    elif period == "Últimos 30 días":
        start = today - timedelta(days=29)
        return start, today
    elif period == "Esta semana": # Lunes a Hoy
        start = today - timedelta(days=today.weekday())
        return start, today
    elif period == "Este mes":
        start = today.replace(day=1)
        return start, today
    elif period == "Mes pasado":
        last_month_end = today.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return last_month_start, last_month_end
    elif period == "Todo el tiempo":
        return min_date, max_date
    # Devuelve None para la opción 'Manual'
    return None, None

# --- Título de la Página ---
st.title("📄 Generador de Reportes PDF")
st.markdown("Utiliza esta sección para crear análisis estáticos y detallados en formato PDF.")

# --- Carga de Datos ---
df_master = cargar_y_procesar_datos()

if df_master is not None and not df_master.empty:
    reporter = ReportGenerator(df_master)

    if 'generated_file_reports' not in st.session_state:
        st.session_state.generated_file_reports = None

    opcion = st.selectbox(
        "Elige un tipo de reporte:",
        ('Análisis por Periodo', 'Reporte Histórico Completo', 'Comparar Periodos')
    )
    st.markdown("---")

    # --- Lógica para cada tipo de reporte ---
    if opcion == 'Análisis por Periodo':
        st.subheader("1. Selecciona el Rango de Fechas")
        
        min_date = df_master['created_at'].min().date()
        max_date = df_master['created_at'].max().date()

        date_options = [
            "Manual", "Hoy", "Ayer", "Últimos 7 días", "Últimos 30 días", 
            "Esta semana", "Este mes", "Mes pasado", "Todo el tiempo"
        ]
        
        selected_period = st.selectbox(
            "Selecciona un periodo",
            options=date_options,
            index=3, # Por defecto 'Últimos 7 días'
            key="reports_period_selector"
        )
        
        is_manual = selected_period == "Manual"

        if is_manual:
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input("Fecha de inicio", value=max_date - timedelta(days=7))
            with col2:
                end_date = st.date_input("Fecha de fin", value=max_date)
        else:
            start_date, end_date = get_date_range(selected_period, min_date, max_date)
            st.info(f"Periodo seleccionado: del {start_date.strftime('%Y-%m-%d')} al {end_date.strftime('%Y-%m-%d')}")

        st.subheader("2. Genera el Reporte")
        if st.button("Generar Reporte por Periodo"):
            df_periodo = df_master[
                (df_master['created_at'].dt.date >= start_date) &
                (df_master['created_at'].dt.date <= end_date)
            ]
            filename = f"reports/Reporte_Kommo_{start_date}_a_{end_date}.pdf"
            title = f"Análisis del Periodo {start_date} a {end_date}"
            
            if not os.path.exists('reports'):
                os.makedirs('reports')

            with st.spinner("Generando reporte PDF..."):
                st.session_state.generated_file_reports = reporter.generar_reporte_por_fechas(df_periodo, filename, title)

    elif opcion == 'Reporte Histórico Completo':
        st.subheader("Genera el Reporte Histórico Completo")
        st.write("Este reporte analizará todos los datos disponibles en la base de datos.")
        if st.button("Generar Reporte Histórico"):
            with st.spinner("Generando reporte histórico..."):
                filename = "reports/Reporte_Historico_Kommo.pdf"
                if not os.path.exists('reports'):
                    os.makedirs('reports')
                st.session_state.generated_file_reports = reporter.generar_reporte_por_fechas(df_master, filename, "Análisis Histórico General")

    elif opcion == 'Comparar Periodos':
        st.subheader("1. Define los Periodos a Comparar")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Periodo Actual (A)**")
            start_a = st.date_input("Fecha de inicio (A)", value=df_master['created_at'].max().date() - timedelta(days=6))
            end_a = st.date_input("Fecha de fin (A)", value=df_master['created_at'].max().date())
        with col2:
            st.markdown("**Periodo Anterior (B)**")
            auto_mode = st.checkbox("Calcular periodo anterior automáticamente", True)
            if auto_mode:
                delta = end_a - start_a
                start_b = start_a - delta - timedelta(days=1)
                end_b = end_a - delta - timedelta(days=1)
                st.info(f"Periodo anterior calculado: {start_b.strftime('%Y-%m-%d')} a {end_b.strftime('%Y-%m-%d')}")
            else:
                start_b = st.date_input("Fecha de inicio (B)", value=df_master['created_at'].max().date() - timedelta(days=14))
                end_b = st.date_input("Fecha de fin (B)", value=df_master['created_at'].max().date() - timedelta(days=8))
        
        st.subheader("2. Genera el Reporte Comparativo")
        if st.button("Generar Reporte Comparativo"):
            df_a = df_master[(df_master['created_at'].dt.date >= start_a) & (df_master['created_at'].dt.date <= end_a)]
            df_b = df_master[(df_master['created_at'].dt.date >= start_b) & (df_master['created_at'].dt.date <= end_b)]
            filename = f"reports/Reporte_Comparativo_{start_a.strftime('%Y-%m-%d')}_vs_{start_b.strftime('%Y-%m-%d')}.pdf"
            if not os.path.exists('reports'):
                os.makedirs('reports')
            with st.spinner("Generando reporte comparativo..."):
                # Nota: La función generar_reporte_comparativo no fue actualizada en este ejemplo.
                # Se necesitaría una lógica similar a la de generar_reporte_por_fechas.
                st.session_state.generated_file_reports = reporter.generar_reporte_comparativo(df_a, df_b, f"{start_a.strftime('%Y-%m-%d')} a {end_a.strftime('%Y-%m-%d')}", f"{start_b.strftime('%Y-%m-%d')} a {end_b.strftime('%Y-%m-%d')}", filename)

    # --- Acciones Post-Generación ---
    if st.session_state.generated_file_reports:
        st.markdown("---")
        st.subheader("3. Acciones del Reporte")
        
        with open(st.session_state.generated_file_reports, "rb") as pdf_file:
            st.download_button(
                label="Descargar Reporte",
                data=pdf_file,
                file_name=os.path.basename(st.session_state.generated_file_reports),
                mime="application/octet-stream"
            )

        with st.form(key='email_form_reports'):
            st.write("**Enviar por Correo Electrónico**")
            default_email = st.secrets.get('email_settings', {}).get('recipient_email', '')
            recipient = st.text_input("Correo del destinatario", value=default_email)
            submit_button = st.form_submit_button(label='Confirmar Envío')

            if submit_button:
                if recipient:
                    asunto = f"Reporte de Ventas: {os.path.basename(st.session_state.generated_file_reports)}"
                    cuerpo = "Adjunto se encuentra el reporte de análisis de ventas solicitado."
                    enviar_correo(asunto, cuerpo, st.session_state.generated_file_reports)
                else:
                    st.warning("Por favor, introduce un correo electrónico.")
else:
    st.error("❌ No se pudieron cargar los datos. Revisa las credenciales en .streamlit/secrets.toml")

