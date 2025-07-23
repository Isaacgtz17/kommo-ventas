# -*- coding: utf-8 -*-

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
from kommo_api import get_api_data
from data_processor import procesar_datos
from config import CONFIG # Importar la configuración

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Analista de Ventas IA",
    page_icon="📊",
    layout="wide"
)

# --- Funciones Auxiliares ---
@st.cache_data(ttl=3600)
def cargar_y_procesar_datos():
    try:
        subdomain = st.secrets["KOMMO_SUBDOMAIN"]
        access_token = st.secrets["KOMMO_ACCESS_TOKEN"]
    except FileNotFoundError:
        st.error("Archivo 'secrets.toml' no encontrado.")
        return None
    except KeyError as e:
        st.error(f"Error: La credencial '{e}' no se encontró en 'secrets.toml'.")
        return None

    with st.spinner('Obteniendo y procesando datos desde Kommo...'):
        api_data = get_api_data(
            base_url=f"https://{subdomain}.kommo.com/api/v4",
            headers={'Authorization': f"Bearer {access_token}"}
        )
        if not api_data or not api_data.get('leads'):
            st.warning("No se obtuvieron datos de leads desde la API.")
            return pd.DataFrame()
        df = procesar_datos(api_data)
    return df

def get_date_range(period, min_date, max_date):
    try:
        mexico_tz = pytz.timezone('America/Mexico_City')
    except pytz.UnknownTimeZoneError:
        mexico_tz = pytz.timezone('UTC')
    today = datetime.now(mexico_tz).date()
    effective_end_date = min(today, max_date)
    start_date, end_date = None, None

    if period == "Hoy":
        start_date, end_date = effective_end_date, effective_end_date
    elif period == "Ayer":
        start_date = effective_end_date - timedelta(days=1)
        end_date = start_date
    elif period == "Últimos 7 días":
        start_date = effective_end_date - timedelta(days=6)
        end_date = effective_end_date
    elif period == "Últimos 30 días":
        start_date = effective_end_date - timedelta(days=29)
        end_date = effective_end_date
    elif period == "Esta semana":
        start_date = effective_end_date - timedelta(days=effective_end_date.weekday())
        end_date = effective_end_date
    elif period == "Este mes":
        start_date = effective_end_date.replace(day=1)
        end_date = effective_end_date
    elif period == "Mes pasado":
        last_month_end = effective_end_date.replace(day=1) - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        start_date, end_date = last_month_start, last_month_end
    elif period == "Todo el tiempo":
        start_date, end_date = min_date, max_date
    
    if start_date and start_date < min_date:
        start_date = min_date
    if period == "Manual":
        return None, None
    return start_date, end_date

def create_sparkline(data, date_col, metric_col):
    data_cleaned = data.dropna(subset=[date_col])
    if data_cleaned.empty:
        fig = go.Figure()
    else:
        daily_data = data_cleaned.set_index(date_col).resample('D')[metric_col].sum()
        fig = go.Figure(go.Scatter(
            x=daily_data.index, y=daily_data, mode='lines',
            line=dict(color=CONFIG['colores']['principal'], width=2),
            fill='tozeroy'
        ))
    fig.update_layout(
        width=150, height=50, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

# --- Título y Panel Lateral ---
st.title("📊 Analista de Ventas IA")
st.markdown("### Dashboard de Mando Interactivo para Grúas Móviles del Golfo")
st.sidebar.title("Acciones")
if st.sidebar.button("Recargar Leads 🔄"):
    st.cache_data.clear()
    st.success("Cache limpiado. Recargando los datos...")
    st.rerun()

# --- Carga de Datos ---
df_master = cargar_y_procesar_datos()

# --- Lógica Principal del Dashboard ---
if df_master is None or df_master.empty:
    st.warning("No se pudieron cargar los datos o no hay leads disponibles.")
    st.stop()
else:
    st.success(f"✔ Datos cargados correctamente. Total de leads: {len(df_master)}")
    st.markdown("---")
    # --- FILTROS GLOBALES ---
    st.header("Filtros Globales")
    col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
    with col1:
        min_date = df_master['created_at'].min().date()
        max_date = df_master['created_at'].max().date()
        date_options = ["Manual", "Hoy", "Ayer", "Últimos 7 días", "Últimos 30 días", "Esta semana", "Este mes", "Mes pasado", "Todo el tiempo"]
        selected_period = st.selectbox("Selecciona un periodo", options=date_options, index=3)
        is_manual = selected_period == "Manual"
        
        if is_manual:
            default_start = max(max_date - timedelta(days=6), min_date)
            value = [default_start, max_date]
        else:
            start_date, end_date = get_date_range(selected_period, min_date, max_date)
            value = [start_date, end_date]

        selected_start, selected_end = st.date_input("Rango de Fechas", value=value, min_value=min_date, max_value=max_date, format="YYYY-MM-DD", disabled=not is_manual)
    
    with col2:
        ejecutivos = sorted(df_master['responsable_nombre'].unique())
        selected_executives = st.multiselect("Ejecutivos", options=ejecutivos, default=ejecutivos)
    with col3:
        estados = sorted(df_master['estado'].unique())
        selected_statuses = st.multiselect("Estado del Lead", options=estados, default=estados)
    with col4:
        search_query = st.text_input("Buscar por Nombre/Folio", placeholder="Escribe para buscar...")

    # --- Filtrado de Datos ---
    if not selected_executives or not selected_statuses:
        st.warning("Por favor, selecciona al menos un ejecutivo y un estado.")
        st.stop()
    start_datetime, end_datetime = pd.to_datetime(selected_start), pd.to_datetime(selected_end)
    df_filtered = df_master[
        (df_master['created_at'] >= start_datetime) & (df_master['created_at'] <= end_datetime + timedelta(days=1)) &
        (df_master['responsable_nombre'].isin(selected_executives)) & (df_master['estado'].isin(selected_statuses))
    ]
    if search_query:
        df_filtered = df_filtered[df_filtered['name'].str.contains(search_query, case=False, na=False)]
    if df_filtered.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        st.stop()

    # --- KPIs ---
    st.markdown("---")
    st.header("Indicadores Clave de Rendimiento (KPIs)")
    kpi_cols = st.columns(5)
    total_leads = len(df_filtered)
    ventas_concluidas_df = df_filtered[df_filtered['estado'].isin(['Ganado', 'Proceso de Cobro'])]
    total_ventas_concluidas = len(ventas_concluidas_df)
    en_cobro_df = df_filtered[df_filtered['estado'] == 'Proceso de Cobro']
    total_en_cobro, valor_en_cobro = len(en_cobro_df), en_cobro_df['price'].sum()
    tasa_conversion = (total_ventas_concluidas / total_leads * 100) if total_leads > 0 else 0
    ciclo_venta_promedio = ventas_concluidas_df.dropna(subset=['dias_para_cerrar'])['dias_para_cerrar'].mean()
    
    df_filtered_copy = df_filtered.copy()
    df_filtered_copy['leads_count'] = 1
    spark_leads = create_sparkline(df_filtered_copy, 'created_at', 'leads_count')
    with kpi_cols[0]:
        st.metric(label="Leads Generados", value=f"{total_leads}")
        st.plotly_chart(spark_leads, use_container_width=True, key="spark_leads")
    
    ventas_concluidas_df_copy = ventas_concluidas_df.copy()
    ventas_concluidas_df_copy['ventas_count'] = 1
    spark_ventas = create_sparkline(ventas_concluidas_df_copy, 'closed_at', 'ventas_count')
    with kpi_cols[1]:
        st.metric(label="Ventas Concluidas", value=f"{total_ventas_concluidas}")
        st.plotly_chart(spark_ventas, use_container_width=True, key="spark_ventas")
    
    with kpi_cols[2]:
        st.metric(label="En Proceso de Cobro", value=f"{total_en_cobro}")
        st.markdown(f"**Valor:** `${valor_en_cobro:,.2f}`")
    
    kpi_cols[3].metric(label="Tasa de Conversión", value=f"{tasa_conversion:.2f}%")
    kpi_cols[4].metric(label="Ciclo de Venta Promedio (días)", value=f"{ciclo_venta_promedio:.1f}" if pd.notna(ciclo_venta_promedio) else "N/A")

    # --- Actividad Reciente ---
    st.markdown("---")
    st.header("Actividad Reciente")
    df_reciente = df_master.sort_values('updated_at', ascending=False).head(10)
    st.dataframe(df_reciente[['name', 'responsable_nombre', 'estado', 'updated_at']], use_container_width=True)

    # --- Visualizaciones ---
    st.markdown("---")
    st.header("Visualizaciones Interactivas")
    viz_col1, viz_col2 = st.columns(2)
    
    colores_config = CONFIG.get('colores', {})
    color_map = {
        'Ganado': colores_config.get('ganado', '#28a745'),
        'En Trámite': colores_config.get('en_tramite', '#ffc107'),
        'Perdido': colores_config.get('perdido', '#dc3545'),
        'Proceso de Cobro': colores_config.get('proceso_cobro', '#0d6efd')
    }

    with viz_col1:
        funnel_data = df_filtered.groupby(['responsable_nombre', 'estado']).size().reset_index(name='counts')
        fig_funnel = px.bar(funnel_data, x='counts', y='responsable_nombre', color='estado', orientation='h', title='Funnel de Conversión por Ejecutivo', labels={'counts': 'Cantidad de Leads', 'responsable_nombre': 'Ejecutivo'}, color_discrete_map=color_map)
        fig_funnel.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_funnel, use_container_width=True, key="funnel_chart")

    with viz_col2:
        health_colors = {'Saludable': '#28a745', 'En Riesgo': '#ffc107', 'Crítico': '#dc3545'}
        health_counts = df_filtered[df_filtered['salud_lead'] != 'N/A']['salud_lead'].value_counts().reset_index()
        health_counts.columns = ['salud_lead', 'counts']
        fig_health = px.pie(health_counts, values='counts', names='salud_lead', title='Salud de la Cartera de Leads Activos', hole=0.4, color='salud_lead', color_discrete_map=health_colors)
        st.plotly_chart(fig_health, use_container_width=True, key="health_chart")

    # --- Tablas Detalladas ---
    st.markdown("---")
    st.header("Datos Detallados")
    tab1, tab2 = st.tabs(["🚨 Leads Críticos que Requieren Atención", "🏆 Detalle de Ventas Concluidas"])
    with tab1:
        leads_criticos = df_filtered[df_filtered['salud_lead'] == 'Crítico']
        st.data_editor(
            leads_criticos[['name', 'responsable_nombre', 'created_at', 'updated_at', 'dias_sin_actualizar']],
            column_config={"dias_sin_actualizar": st.column_config.ProgressColumn("Días sin Actualizar", help="Días desde la última actualización", format="%f días", min_value=0, max_value=int(leads_criticos['dias_sin_actualizar'].max()) if not leads_criticos.empty else 100)},
            hide_index=True, use_container_width=True
        )
    with tab2:
        st.data_editor(
            ventas_concluidas_df[['name', 'responsable_nombre', 'estado', 'price', 'closed_at', 'dias_para_cerrar']],
            column_config={"price": st.column_config.NumberColumn("Valor", format="$ %d")},
            hide_index=True, use_container_width=True
        )
        
    # --- ANÁLISIS DE MOTIVOS DE PÉRDIDA (MEJORADO) ---
    st.markdown("---")
    st.header("Análisis de Motivos de Pérdida")
    
    df_perdidos = df_filtered[df_filtered['estado'] == 'Perdido']
    
    if df_perdidos.empty:
        st.info("No hay leads perdidos en el periodo seleccionado para analizar.")
    else:
        loss_reason_counts = df_perdidos['motivo_perdida_nombre'].value_counts().reset_index()
        loss_reason_counts.columns = ['motivo', 'cantidad']
        
        fig_loss = px.bar(
            loss_reason_counts, x='cantidad', y='motivo', orientation='h',
            title='Principales Motivos de Pérdida',
            labels={'cantidad': 'Cantidad de Leads', 'motivo': 'Motivo de Pérdida'}
        )
        fig_loss.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_loss, use_container_width=True)
        
        # Ayudante de diagnóstico
        with st.expander("Ver todos los motivos de pérdida detectados"):
            st.dataframe(loss_reason_counts)
            
        st.markdown("#### Análisis Detallado por Etiquetas")
        
        def create_loss_reason_analysis(df_perdidos, reason_text, expander_title, column_title):
            with st.expander(expander_title):
                # Búsqueda flexible (contiene el texto, ignora mayúsculas/minúsculas)
                df_reason = df_perdidos[df_perdidos['motivo_perdida_nombre'].str.contains(reason_text, case=False, na=False)]
                if df_reason.empty:
                    st.write("No se perdieron leads por este motivo en el periodo seleccionado.")
                else:
                    tags_count = df_reason.explode('tags')['tags'].value_counts().reset_index()
                    tags_count.columns = ['Unidad (Etiqueta)', column_title]
                    st.dataframe(tags_count, use_container_width=True)

        # Define los motivos de pérdida a analizar
        motivos_a_analizar = {
            'Unidad Ocupada': 'Veces Solicitada',
            'Unidad Sin Operador': 'Veces sin Operador',
            'Unidad fuera de servicio': 'Veces Fuera de Servicio'
        }
        
        cols = st.columns(len(motivos_a_analizar))
        for i, (motivo, col_title) in enumerate(motivos_a_analizar.items()):
            with cols[i]:
                create_loss_reason_analysis(df_perdidos, motivo, f"Análisis de '{motivo}'", col_title)
