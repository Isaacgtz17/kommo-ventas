# -*- coding: utf-8 -*-
# =============================================================================
# MÓDULO DEL DASHBOARD INTERACTIVO
# =============================================================================
# Responsabilidad: Construir la interfaz visual del dashboard en tiempo real,
# incluyendo filtros, KPIs, gráficos y tablas.
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import visualizations as viz # Usaremos nuestro módulo de gráficos
from config import CONFIG # Importar la configuración para umbrales

def display_filters(df):
    """Muestra los filtros en la barra lateral y devuelve el DF filtrado."""
    st.sidebar.header("Filtros del Dashboard")
    
    # Filtro por Ejecutivo
    ejecutivos = sorted(df['responsable_nombre'].unique())
    selected_execs = st.sidebar.multiselect(
        "Filtrar por Ejecutivo:",
        options=ejecutivos,
        default=ejecutivos
    )

    # Filtro por Rango de Fechas
    min_date = df['created_at'].min().date()
    max_date = df['created_at'].max().date()
    selected_start, selected_end = st.sidebar.date_input(
        "Filtrar por Fecha de Creación:",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    if not selected_execs or not selected_start or not selected_end:
        st.sidebar.warning("Por favor, selecciona al menos un ejecutivo y un rango de fechas válido.")
        return pd.DataFrame()

    # Aplicar filtros
    filtered_df = df[
        (df['responsable_nombre'].isin(selected_execs)) &
        (df['created_at'].dt.date >= selected_start) &
        (df['created_at'].dt.date <= selected_end)
    ]
    
    return filtered_df

def display_kpis(df):
    """Calcula y muestra los KPIs principales en tarjetas."""
    st.subheader("Indicadores Clave de Rendimiento (KPIs)")
    
    total_leads = len(df)
    leads_ganados = (df['estado'] == 'Ganado').sum()
    tasa_conversion = (leads_ganados / total_leads * 100) if total_leads > 0 else 0
    valor_ganado = df[df['estado'] == 'Ganado']['price'].sum()
    
    # Calcular ciclo de venta promedio solo para leads ganados con fecha de cierre
    df_ganados_con_cierre = df[(df['estado'] == 'Ganado') & pd.notna(df['dias_para_cerrar'])]
    ciclo_venta_promedio = df_ganados_con_cierre['dias_para_cerrar'].mean() if not df_ganados_con_cierre.empty else 0

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Leads Generados", f"{total_leads:,}")
    col2.metric("Leads Ganados", f"{leads_ganados:,}")
    col3.metric("Tasa de Conversión", f"{tasa_conversion:.2f}%")
    col4.metric("Valor Ganado", f"${valor_ganado:,.2f}")
    col5.metric("Ciclo de Venta Prom.", f"{ciclo_venta_promedio:.1f} días")

def build_dashboard(df_master):
    """Función principal que construye toda la página del dashboard."""
    
    df_filtered = display_filters(df_master)

    if df_filtered.empty:
        st.warning("No hay datos para mostrar con los filtros seleccionados.")
        return

    display_kpis(df_filtered)
    st.markdown("---")

    # Visualizaciones
    st.subheader("Análisis Visual del Periodo")
    
    col1, col2 = st.columns(2)

    with col1:
        img_funnel_path = "temp_assets/funnel_dashboard.png"
        viz.crear_funnel_ejecutivo(df_filtered, img_funnel_path)
        if os.path.exists(img_funnel_path):
            st.image(img_funnel_path, use_container_width=True)
            os.remove(img_funnel_path)

    with col2:
        img_salud_path = "temp_assets/salud_dashboard.png"
        viz.crear_grafico_salud_leads(df_filtered, img_salud_path)
        if os.path.exists(img_salud_path):
            st.image(img_salud_path, use_container_width=True)
            os.remove(img_salud_path)

    # Tablas de datos para análisis profundo
    st.markdown("---")
    st.subheader("Análisis Detallado")

    tab1, tab2 = st.tabs(["Leads Críticos", "Últimos Leads Ganados"])

    with tab1:
        leads_criticos = df_filtered[df_filtered['salud_lead'] == 'Crítico'].sort_values(by='dias_sin_actualizar', ascending=False)
        st.write(f"**{len(leads_criticos)} leads en estado crítico (más de {CONFIG['dias_lead_critico']} días sin actualizar):**")
        st.dataframe(leads_criticos[['name', 'responsable_nombre', 'dias_sin_actualizar', 'price']])

    with tab2:
        leads_ganados_recientes = df_filtered[df_filtered['estado'] == 'Ganado'].sort_values(by='closed_at', ascending=False)
        st.write(f"**{len(leads_ganados_recientes)} leads ganados en el periodo seleccionado:**")
        st.dataframe(leads_ganados_recientes[['name', 'responsable_nombre', 'price', 'closed_at']])
