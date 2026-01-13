# -*- coding: utf-8 -*-

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
from kommo_api import get_api_data
from data_processor import procesar_datos
from config import CONFIG

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Dashboard de Ventas",
    page_icon="📈",
    layout="wide"
)

# --- Constante de Zona Horaria ---
LOCAL_TIMEZONE = pytz.timezone('America/Mexico_City')

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
        api_data = get_api_data(base_url=f"https://{subdomain}.kommo.com/api/v4", headers={'Authorization': f"Bearer {access_token}"})
        if not api_data or not api_data.get('leads'):
            st.warning("No se obtuvieron datos de leads desde la API.")
            return pd.DataFrame()
        df = procesar_datos(api_data)
    return df

def get_date_range(period, min_date, max_date):
    today = datetime.now(LOCAL_TIMEZONE).date()
    effective_end_date = min(today, max_date)
    start_date, end_date = None, None
    if period == "Hoy": start_date, end_date = effective_end_date, effective_end_date
    elif period == "Ayer": start_date, end_date = effective_end_date - timedelta(days=1), effective_end_date - timedelta(days=1)
    elif period == "Últimos 7 días": start_date, end_date = effective_end_date - timedelta(days=6), effective_end_date
    elif period == "Últimos 30 días": start_date, end_date = effective_end_date - timedelta(days=29), effective_end_date
    elif period == "Esta semana": start_date, end_date = effective_end_date - timedelta(days=effective_end_date.weekday()), effective_end_date
    elif period == "Este mes": start_date, end_date = effective_end_date.replace(day=1), effective_end_date
    elif period == "Mes pasado":
        last_month_end = effective_end_date.replace(day=1) - timedelta(days=1)
        start_date, end_date = last_month_end.replace(day=1), last_month_end
    elif period == "Todo el tiempo": start_date, end_date = min_date, max_date
    if start_date and start_date < min_date: start_date = min_date
    if period == "Manual": return None, None
    return start_date, end_date

def create_sparkline(data, date_col, metric_col):
    data_cleaned = data.dropna(subset=[date_col])
    if data_cleaned.empty:
        fig = go.Figure()
    else:
        data_cleaned[date_col] = data_cleaned[date_col].dt.tz_convert(LOCAL_TIMEZONE)
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
st.title("📈 Dashboard de Ventas y Operaciones")
st.markdown("### Grúas Móviles del Golfo")
st.sidebar.title("Acciones")
if st.sidebar.button("Recargar Datos 🔄"):
    st.cache_data.clear()
    st.success("Cache limpiado. Recargando los datos...")
    st.rerun()

# --- Carga de Datos ---
df_master = cargar_y_procesar_datos()

if df_master is None or df_master.empty:
    st.warning("No se pudieron cargar los datos o no hay leads disponibles.")
    st.stop()

# --- SECCIÓN: MONITOR DEL DÍA ---
st.header(f"Monitor del Día - {datetime.now(LOCAL_TIMEZONE).strftime('%A, %d de %B de %Y')}")

with st.container(border=True):
    today_date = datetime.now(LOCAL_TIMEZONE).date()
    df_today_created = df_master[df_master['created_at'].dt.tz_convert(LOCAL_TIMEZONE).dt.date == today_date]
    df_today_updated = df_master[df_master['updated_at'].dt.tz_convert(LOCAL_TIMEZONE).dt.date == today_date]

    leads_creados_hoy = len(df_today_created)
    ganados_hoy_df = df_today_updated[df_today_updated['estado'] == 'Ganado']
    valor_ganado_hoy = ganados_hoy_df['price'].sum()
    ventas_hoy = len(df_today_updated[df_today_updated['estado'] == 'Ganado'])
    perdidos_hoy = len(df_today_updated[df_today_updated['estado'] == 'Perdido'])

    kpi_today_cols = st.columns(4)
    with kpi_today_cols[0]:
        with st.container(border=True):
            st.metric("➕ Leads Creados Hoy", leads_creados_hoy)
    with kpi_today_cols[1]:
        with st.container(border=True):
            st.metric("✅ Ventas Ganadas Hoy", ventas_hoy)
    with kpi_today_cols[2]:
        with st.container(border=True):
            st.metric("❌ Leads Perdidos Hoy", perdidos_hoy)
    with kpi_today_cols[3]:
        with st.container(border=True):
            st.metric("💰 Valor Ganado Hoy", f"${valor_ganado_hoy:,.2f}", help="Suma del valor de los leads que cambiaron a 'Ganado' hoy.")

    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### 📊 Rendimiento de Ejecutivos (Hoy)")
        if not df_today_created.empty:
            rendimiento_hoy = df_today_created.groupby('responsable_nombre')['id'].count().reset_index()
            rendimiento_hoy.columns = ['Ejecutivo', 'Leads Creados Hoy']
            fig_rendimiento = px.bar(rendimiento_hoy, x='Leads Creados Hoy', y='Ejecutivo', orientation='h', text_auto=True)
            fig_rendimiento.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'}, height=250)
            st.plotly_chart(fig_rendimiento, use_container_width=True)
        else:
            st.info("Aún no hay leads creados hoy.")
    st.markdown("<br>", unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("#### ⚡ Actividad Reciente del Día")
        df_master['fecha_evento'] = df_master['updated_at'].dt.tz_convert(LOCAL_TIMEZONE)
        df_eventos_hoy = df_master[df_master['fecha_evento'].dt.date == today_date].copy()
        df_eventos_hoy['evento'] = "Actualizado: " + df_eventos_hoy['estado']
        df_eventos_hoy.loc[df_eventos_hoy['created_at'].dt.tz_convert(LOCAL_TIMEZONE).dt.date == today_date, 'evento'] = 'Creado'
        df_eventos_hoy.loc[df_eventos_hoy['closed_at'].dt.tz_convert(LOCAL_TIMEZONE).dt.date == today_date, 'evento'] = 'Cerrado: ' + df_eventos_hoy['estado']
        df_eventos_hoy['etiquetas'] = df_eventos_hoy['tags'].apply(lambda x: ', '.join(x) if isinstance(x, list) and x else 'N/A')
        df_eventos_hoy = df_eventos_hoy.sort_values('fecha_evento', ascending=False)
        st.dataframe(
            df_eventos_hoy[['name', 'responsable_nombre', 'price', 'etiquetas', 'evento', 'fecha_evento']],
            column_config={
                "name": "Lead", "responsable_nombre": "Ejecutivo",
                "price": st.column_config.NumberColumn("Precio", format="$%d"),
                "etiquetas": "Etiquetas", "evento": "Última Actividad",
                "fecha_evento": st.column_config.TimeColumn("Hora", format="h:mm a")
            }, use_container_width=True
        )

# --- SECCIÓN DE ANÁLISIS HISTÓRICO ---
st.markdown("---")
st.header("Análisis Histórico y Búsqueda")

col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1.5])
with col1:
    min_date_hist = df_master['created_at'].dt.date.min()
    max_date_hist = df_master['created_at'].dt.date.max()
    date_options = ["Manual", "Ayer", "Últimos 7 días", "Últimos 30 días", "Esta semana", "Este mes", "Mes pasado", "Todo el tiempo"]
    selected_period = st.selectbox("Selecciona un periodo", options=date_options, index=2)
    is_manual = selected_period == "Manual"
    
    if is_manual:
        default_start = max(max_date_hist - timedelta(days=6), min_date_hist)
        value = [default_start, max_date_hist]
    else:
        start_date, end_date = get_date_range(selected_period, min_date_hist, max_date_hist)
        value = [start_date, end_date]

    selected_start, selected_end = st.date_input("Rango de Fechas", value=value, min_value=min_date_hist, max_value=max_date_hist, format="YYYY-MM-DD", disabled=not is_manual)

with col2:
    ejecutivos = sorted(df_master['responsable_nombre'].unique())
    selected_executives = st.multiselect("Ejecutivos", options=ejecutivos, default=ejecutivos)
with col3:
    estados = sorted(df_master['estado'].unique())
    selected_statuses = st.multiselect("Estado del Lead", options=estados, default=estados)
with col4:
    search_query = st.text_input("Buscar por Nombre/Folio", placeholder="Escribe para buscar...")

if not selected_executives or not selected_statuses:
    st.warning("Por favor, selecciona al menos un ejecutivo y un estado para el análisis histórico.")
    st.stop()

# --- CORRECCIÓN DEL TypeError ---
# Comparamos la parte de la fecha (.dt.date) de la columna con las fechas seleccionadas
df_filtered = df_master[
    (df_master['created_at'].dt.tz_convert(LOCAL_TIMEZONE).dt.date >= selected_start) & 
    (df_master['created_at'].dt.tz_convert(LOCAL_TIMEZONE).dt.date <= selected_end) &
    (df_master['responsable_nombre'].isin(selected_executives)) & 
    (df_master['estado'].isin(selected_statuses))
]
if search_query:
    df_filtered = df_filtered[df_filtered['name'].str.contains(search_query, case=False, na=False)]

if df_filtered.empty:
    st.warning("No hay datos para los filtros seleccionados en el análisis histórico.")
    st.stop()

st.markdown("---")
st.header("Indicadores Clave del Periodo Seleccionado")
kpi_cols = st.columns(5)
total_leads = len(df_filtered)
ventas_ganadas_df = df_filtered[df_filtered['estado'] == 'Ganado']
total_ventas_ganadas = len(ventas_ganadas_df)
tasa_conversion = (total_ventas_ganadas / total_leads * 100) if total_leads > 0 else 0
ciclo_venta_promedio = ventas_ganadas_df.dropna(subset=['dias_para_cerrar'])['dias_para_cerrar'].mean()
valor_total_ganado = ventas_ganadas_df['price'].sum()

df_filtered_copy = df_filtered.copy()
df_filtered_copy['leads_count'] = 1
spark_leads = create_sparkline(df_filtered_copy, 'created_at', 'leads_count')
with kpi_cols[0]:
    st.metric(label="Leads Generados", value=f"{total_leads}")
    st.plotly_chart(spark_leads, use_container_width=True, key="spark_leads_hist")

ventas_ganadas_df_copy = ventas_ganadas_df.copy()
ventas_ganadas_df_copy['ventas_count'] = 1
spark_ventas = create_sparkline(ventas_ganadas_df_copy, 'closed_at', 'ventas_count')
with kpi_cols[1]:
    st.metric(label="Ventas Ganadas", value=f"{total_ventas_ganadas}")
    st.plotly_chart(spark_ventas, use_container_width=True, key="spark_ventas_hist")

kpi_cols[2].metric(label="Tasa de Conversión", value=f"{tasa_conversion:.2f}%")
kpi_cols[3].metric(label="Valor Total Ganado", value=f"${valor_total_ganado:,.2f}")
kpi_cols[4].metric(label="Ciclo de Venta Promedio (días)", value=f"{ciclo_venta_promedio:.1f}" if pd.notna(ciclo_venta_promedio) else "N/A")

st.markdown("---")
st.header("Visualizaciones del Periodo")
viz_col1, viz_col2 = st.columns(2)
colores_config = CONFIG.get('colores', {})
color_map = {
    'Ganado': colores_config.get('ganado', '#28a745'),
    'En Trámite': colores_config.get('en_tramite', '#ffc107'),
    'Perdido': colores_config.get('perdido', '#dc3545')
}
with viz_col1:
    funnel_data = df_filtered.groupby(['responsable_nombre', 'estado']).size().reset_index(name='counts')
    fig_funnel = px.bar(funnel_data, x='counts', y='responsable_nombre', color='estado', orientation='h', title='Funnel de Conversión por Ejecutivo', labels={'counts': 'Cantidad de Leads', 'responsable_nombre': 'Ejecutivo'}, color_discrete_map=color_map)
    fig_funnel.update_layout(yaxis={'categoryorder':'total ascending'})
    st.plotly_chart(fig_funnel, use_container_width=True, key="funnel_chart_hist")
with viz_col2:
    health_colors = {'Saludable': '#28a745', 'En Riesgo': '#ffc107', 'Crítico': '#dc3545'}
    health_counts = df_filtered[df_filtered['salud_lead'] != 'N/A']['salud_lead'].value_counts().reset_index()
    health_counts.columns = ['salud_lead', 'counts']
    fig_health = px.pie(health_counts, values='counts', names='salud_lead', title='Salud de la Cartera de Leads Activos', hole=0.4, color='salud_lead', color_discrete_map=health_colors)
    st.plotly_chart(fig_health, use_container_width=True, key="health_chart_hist")

st.markdown("---")
st.header("Datos Detallados del Periodo")
tab1, tab2 = st.tabs(["🚨 Leads Críticos", "🏆 Ventas Ganadas"])
with tab1:
    leads_criticos = df_filtered[df_filtered['salud_lead'] == 'Crítico']
    st.data_editor(leads_criticos[['name', 'responsable_nombre', 'created_at', 'updated_at', 'dias_sin_actualizar']],
                   column_config={"dias_sin_actualizar": st.column_config.ProgressColumn("Días sin Actualizar", help="Días desde la última actualización", format="%f días", min_value=0, max_value=int(leads_criticos['dias_sin_actualizar'].max()) if not leads_criticos.empty else 100)},
                   hide_index=True, use_container_width=True)
with tab2:
    st.data_editor(ventas_ganadas_df[['name', 'responsable_nombre', 'estado', 'price', 'closed_at', 'dias_para_cerrar']],
                   column_config={"price": st.column_config.NumberColumn("Valor", format="$ %d")},
                   hide_index=True, use_container_width=True)

st.markdown("---")
st.header("Análisis de Motivos de Pérdida del Periodo")
df_perdidos = df_filtered[df_filtered['estado'] == 'Perdido']
if df_perdidos.empty:
    st.info("No hay leads perdidos en el periodo seleccionado para analizar.")
else:
    # --- FILA 1: Gráfica de Barras y Pie de Impacto ---
    col_loss1, col_loss2 = st.columns([1.5, 1])
    
    with col_loss1:
        # Gráfica de barras de principales motivos
        loss_reason_counts = df_perdidos['motivo_perdida_nombre'].value_counts().reset_index()
        loss_reason_counts.columns = ['motivo', 'cantidad']
        fig_loss = px.bar(
            loss_reason_counts, 
            x='cantidad', 
            y='motivo', 
            orientation='h', 
            title='Principales Motivos de Pérdida',
            labels={'cantidad': 'Cantidad de Leads', 'motivo': 'Motivo de Pérdida'},
            text='cantidad'
        )
        fig_loss.update_layout(yaxis={'categoryorder':'total ascending'})
        fig_loss.update_traces(textposition='outside', marker_color='#1f77b4')
        st.plotly_chart(fig_loss, use_container_width=True)
    
    with col_loss2:
        # Clasificar motivos en Operativos vs Factores Externos
        motivos_operativos = ['Unidad ocupada', 'Unidad sin operador', 'Unidad fuera de servicio', 'Sin unidades disponibles']
        
        df_perdidos_copy = df_perdidos.copy()
        def clasificar_impacto(motivo):
            if pd.isna(motivo):
                return 'Factores del Cliente\n/ Mercado'
            motivo_lower = motivo.lower()
            for m in motivos_operativos:
                if m.lower() in motivo_lower:
                    return 'Capacidad Operativa\n(Flota/Personal)'
            return 'Factores del Cliente\n/ Mercado'
        
        df_perdidos_copy['impacto'] = df_perdidos_copy['motivo_perdida_nombre'].apply(clasificar_impacto)
        impacto_counts = df_perdidos_copy['impacto'].value_counts().reset_index()
        impacto_counts.columns = ['impacto', 'cantidad']
        
        fig_impacto = px.pie(
            impacto_counts, 
            values='cantidad', 
            names='impacto', 
            title='Clasificación de Pérdidas',
            color='impacto',
            color_discrete_map={
                'Capacidad Operativa\n(Flota/Personal)': '#ff9999',
                'Factores del Cliente\n/ Mercado': '#66b3ff'
            }
        )
        fig_impacto.update_traces(textposition='inside', textinfo='percent+label', textfont_size=11)
        fig_impacto.update_layout(showlegend=False)
        st.plotly_chart(fig_impacto, use_container_width=True)
    
    # --- FILA 2: Unidades Críticas (Demanda Insatisfecha) ---
    st.markdown("#### Unidades Críticas: Demanda Insatisfecha")
    
    # Filtrar pérdidas por "Unidad ocupada" para ver qué unidades tienen más demanda insatisfecha
    df_ocupada = df_perdidos[df_perdidos['motivo_perdida_nombre'].str.contains('ocupada', case=False, na=False)]
    
    if not df_ocupada.empty:
        # Explotar tags para contar qué unidades se solicitaron más
        tags_ocupada = df_ocupada.explode('tags')['tags'].value_counts().reset_index()
        tags_ocupada.columns = ['unidad', 'cantidad']
        tags_ocupada = tags_ocupada[tags_ocupada['unidad'].notna()].head(10)
        
        if not tags_ocupada.empty:
            fig_criticas = px.bar(
                tags_ocupada,
                x='cantidad',
                y='unidad',
                orientation='h',
                title='Unidades Críticas: Demanda Insatisfecha ("Unidad Ocupada")',
                labels={'cantidad': 'Cantidad de Ventas Perdidas', 'unidad': ''},
                text='cantidad'
            )
            fig_criticas.update_layout(
                yaxis={'categoryorder':'total ascending'},
                xaxis=dict(showgrid=True, gridcolor='lightgray', gridwidth=1, dtick=1)
            )
            fig_criticas.update_traces(textposition='outside', marker_color='#d62728')
            st.plotly_chart(fig_criticas, use_container_width=True)
            
            st.info("💡 **Insight:** Estas unidades tienen alta demanda pero no pudieron atender al cliente. Considera aumentar la disponibilidad o adquirir más unidades de este tipo.")
        else:
            st.write("No hay datos de unidades específicas para este análisis.")
    else:
        st.write("No hay pérdidas por 'Unidad ocupada' en este periodo.")
    
    # --- FILA 3: Mapa de Calor - Motivos por Vendedor ---
    st.markdown("#### Mapa de Calor: Motivos de Pérdida por Vendedor")
    
    # Crear tabla pivote para el mapa de calor
    df_heatmap = df_perdidos.copy()
    df_heatmap['motivo_corto'] = df_heatmap['motivo_perdida_nombre'].apply(lambda x: 
        'Unidad ocupada' if pd.notna(x) and 'ocupada' in x.lower() else
        'Sin respuesta' if pd.notna(x) and 'respuesta' in x.lower() else
        'Cuadro comparativo' if pd.notna(x) and 'comparativo' in x.lower() else
        'Descuento' if pd.notna(x) and 'descuento' in x.lower() else
        'Fuera de servicio' if pd.notna(x) and 'fuera' in x.lower() else
        'Sin operador' if pd.notna(x) and 'operador' in x.lower() else
        'Baja demanda' if pd.notna(x) and 'demanda' in x.lower() else
        'No especificado' if pd.isna(x) or x == '' else
        x[:15] if len(str(x)) > 15 else x
    )
    
    # Acortar nombres de vendedores
    df_heatmap['vendedor_corto'] = df_heatmap['responsable_nombre'].apply(lambda x: 
        ' '.join(str(x).split()[:2]) if pd.notna(x) else 'Sin asignar'
    )
    
    pivot_table = pd.crosstab(df_heatmap['motivo_corto'], df_heatmap['vendedor_corto'])
    
    if not pivot_table.empty and pivot_table.shape[0] > 1 and pivot_table.shape[1] > 1:
        fig_heatmap = px.imshow(
            pivot_table.values,
            x=pivot_table.columns.tolist(),
            y=pivot_table.index.tolist(),
            title='Mapa de Calor: Motivos de Pérdida por Vendedor',
            labels=dict(x="Vendedor", y="Motivo", color="Cantidad"),
            color_continuous_scale='Blues',
            text_auto=True,
            aspect='auto'
        )
        fig_heatmap.update_layout(
            xaxis_title="",
            yaxis_title="Motivo"
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        # Insights automáticos
        max_perdidas_vendedor = pivot_table.sum(axis=0).idxmax()
        max_perdidas_motivo = pivot_table.sum(axis=1).idxmax()
        st.info(f"📊 **Análisis Rápido:** El vendedor con más pérdidas es **{max_perdidas_vendedor}** y el motivo más frecuente es **{max_perdidas_motivo}**.")
    else:
        st.write("No hay suficientes datos para generar el mapa de calor.")
    
    # --- FILA 4: Análisis Detallado por Etiquetas (Tablas) ---
    st.markdown("#### Análisis Detallado por Etiquetas")
    
    def create_loss_reason_analysis(df_perdidos, reason_text, expander_title, column_title):
        with st.expander(expander_title, expanded=True):
            df_reason = df_perdidos[df_perdidos['motivo_perdida_nombre'].str.contains(reason_text, case=False, na=False)]
            if df_reason.empty:
                st.write("No se perdieron leads por este motivo en el periodo seleccionado.")
                return None
            else:
                tags_count = df_reason.explode('tags')['tags'].value_counts().reset_index()
                tags_count.columns = ['Unidad (Etiqueta)', column_title]
                tags_count = tags_count[tags_count['Unidad (Etiqueta)'].notna()]
                st.dataframe(tags_count, use_container_width=True, hide_index=True)
                return tags_count

    motivos_a_analizar = {
        'Unidad Ocupada': 'Veces Solicitada',
        'Unidad Sin Operador': 'Veces sin Operador',
        'Unidad fuera de servicio': 'Veces Fuera de Servicio'
    }
    cols = st.columns(len(motivos_a_analizar))
    for i, (motivo, col_title) in enumerate(motivos_a_analizar.items()):
        with cols[i]:
            create_loss_reason_analysis(df_perdidos, motivo, f"Análisis de '{motivo}'", col_title)
    
    # --- Resumen Ejecutivo de Pérdidas ---
    with st.expander("📋 Ver Resumen Ejecutivo de Pérdidas", expanded=False):
        total_perdidos = len(df_perdidos)
        valor_perdido = df_perdidos['price'].sum()
        
        col_resumen1, col_resumen2, col_resumen3 = st.columns(3)
        col_resumen1.metric("Total Leads Perdidos", total_perdidos)
        col_resumen2.metric("Valor Total Perdido", f"${valor_perdido:,.2f}")
        col_resumen3.metric("Promedio por Lead", f"${valor_perdido/total_perdidos:,.2f}" if total_perdidos > 0 else "$0")
        
        st.markdown("**Detalle completo de motivos:**")
        st.dataframe(loss_reason_counts, use_container_width=True, hide_index=True)

