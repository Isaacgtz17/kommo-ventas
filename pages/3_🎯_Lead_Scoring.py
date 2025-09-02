# -*- coding: utf-8 -*-

import streamlit as st
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from PaginaPrincipal import cargar_y_procesar_datos # Reutilizamos la función de carga

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Lead Scoring Predictivo",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Lead Scoring Predictivo")
st.markdown("### Prioriza tus leads para enfocar tus esfuerzos donde más importan.")

# --- Funciones de Scoring ---

def get_contact_name(row):
    """Función segura para obtener el nombre del contacto de un lead."""
    try:
        # Usamos .get() para un acceso seguro, evitando KeyErrors
        if row['_embedded'] and row['_embedded'].get('contacts'):
            return row['_embedded']['contacts'][0].get('name', 'Cliente Desconocido')
    except (KeyError, IndexError):
        # Captura cualquier otro error de estructura inesperado
        return 'Cliente Desconocido'
    return 'Cliente Desconocido'

@st.cache_data
def prepare_scoring_data(df):
    """Prepara los datos históricos para el cálculo de puntuaciones."""
    df_historico = df[df['estado'].isin(['Ganado', 'Perdido'])].copy()
    
    # 1. Historial de Clientes (con obtención de nombre segura)
    df_historico['nombre_cliente'] = df_historico.apply(get_contact_name, axis=1)
    
    client_history = df_historico.groupby('nombre_cliente').agg(
        total_deals=('id', 'count'),
        deals_won=('estado', lambda x: (x == 'Ganado').sum())
    )
    client_history['win_rate'] = client_history['deals_won'] / client_history['total_deals']
    
    # 2. Historial de Servicios (Tags)
    df_tags = df_historico.explode('tags').dropna(subset=['tags'])
    tag_history = df_tags.groupby('tags').agg(
        total_requests=('id', 'count'),
        requests_won=('estado', lambda x: (x == 'Ganado').sum())
    )
    tag_history['win_rate'] = tag_history['requests_won'] / tag_history['total_requests']
    
    return client_history, tag_history

def calculate_lead_score(lead, client_history, tag_history):
    """Calcula la puntuación para un único lead basado en reglas de negocio."""
    score = 0
    reasons = []

    # Factor 1: Historial del Cliente (con obtención de nombre segura)
    client_name = get_contact_name(lead)
    if client_name in client_history.index and client_name != 'Cliente Desconocido':
        hist = client_history.loc[client_name]
        if hist['deals_won'] > 0:
            score += 25
            reasons.append(f"+25 pts: Cliente recurrente con {int(hist['deals_won'])} venta(s) previa(s).")
        else:
            score += 10
            reasons.append("+10 pts: Cliente conocido, pero sin ventas previas.")
    else:
        reasons.append("+0 pts: Cliente nuevo.")

    # Factor 2: Valor del Lead (Price)
    price = lead['price']
    if price > 20000:
        score += 20
        reasons.append(f"+20 pts: Valor alto (${price:,.0f}).")
    elif price > 5000:
        score += 10
        reasons.append(f"+10 pts: Valor medio (${price:,.0f}).")
    else:
        reasons.append(f"+0 pts: Valor bajo (${price:,.0f}).")
        
    # Factor 3: Tipo de Servicio (Tags)
    lead_tags = lead['tags']
    tag_score = 0
    if lead_tags:
        max_tag_win_rate = 0
        best_tag = ""
        for tag in lead_tags:
            if tag in tag_history.index:
                win_rate = tag_history.loc[tag, 'win_rate']
                if win_rate > max_tag_win_rate:
                    max_tag_win_rate = win_rate
                    best_tag = tag
        
        if max_tag_win_rate > 0.75:
            tag_score = 25
        elif max_tag_win_rate > 0.50:
            tag_score = 15
        elif max_tag_win_rate > 0.25:
            tag_score = 5
            
        if tag_score > 0:
            score += tag_score
            reasons.append(f"+{tag_score} pts: El servicio '{best_tag}' tiene una tasa de éxito histórica del {max_tag_win_rate:.0%}.")

    return score, reasons


# --- Carga y Procesamiento de Datos ---
df_master = cargar_y_procesar_datos()

if df_master is None or df_master.empty:
    st.warning("No se pudieron cargar los datos o no hay leads disponibles.")
    st.stop()

# Preparar datos para el scoring
client_history, tag_history = prepare_scoring_data(df_master)

# Filtrar solo leads activos
df_active = df_master[df_master['estado'] == 'En Trámite'].copy()

if df_active.empty:
    st.info("No hay leads activos para puntuar en este momento.")
    st.stop()

# Calcular puntuación para cada lead activo
scores_data = [calculate_lead_score(row, client_history, tag_history) for index, row in df_active.iterrows()]
df_active['raw_score'] = [item[0] for item in scores_data]
df_active['score_reasons'] = [item[1] for item in scores_data]

# Normalizar la puntuación a una escala de 0-100
# Asegurarse de que hay más de un valor para escalar, si no, asignar 50
if df_active['raw_score'].nunique() > 1:
    scaler = MinMaxScaler(feature_range=(1, 100))
    df_active['puntuacion'] = scaler.fit_transform(df_active[['raw_score']])
else:
    df_active['puntuacion'] = 50 

df_active['puntuacion'] = df_active['puntuacion'].astype(int)


# --- Interfaz de Usuario ---
st.markdown("---")
st.header("Leads Activos por Puntuación")

# Filtro por puntuación
if not df_active.empty:
    min_score = int(df_active['puntuacion'].min())
    max_score = int(df_active['puntuacion'].max())
    
    # Asegurarse de que min y max no sean iguales para el slider
    if min_score == max_score:
        score_range = (min_score, max_score)
    else:
        score_range = st.slider(
            "Filtrar por rango de puntuación:",
            min_value=min_score,
            max_value=max_score,
            value=(min_score, max_score)
        )

    df_display = df_active[
        (df_active['puntuacion'] >= score_range[0]) &
        (df_active['puntuacion'] <= score_range[1])
    ].sort_values('puntuacion', ascending=False)

    # Tabla de leads con puntuación
    st.data_editor(
        df_display[['name', 'responsable_nombre', 'estado', 'price', 'puntuacion']],
        column_config={
            "name": "Nombre del Lead",
            "responsable_nombre": "Ejecutivo",
            "estado": "Estado Actual",
            "price": st.column_config.NumberColumn("Valor", format="$ %d"),
            "puntuacion": st.column_config.ProgressColumn(
                "Puntuación",
                help="Probabilidad de cierre estimada (1-100)",
                min_value=1,
                max_value=100,
            ),
        },
        use_container_width=True,
        hide_index=True,
        key='lead_scorer_table'
    )

    # Mostrar detalles de la puntuación
    if not df_display.empty:
        selected_lead_name = st.selectbox(
            "Selecciona un lead para ver el detalle de su puntuación:",
            options=df_display['name'].unique()
        )

        if selected_lead_name:
            lead_details = df_display[df_display['name'] == selected_lead_name].iloc[0]
            st.markdown(f"#### Desglose de Puntuación para: **{selected_lead_name}**")
            
            with st.container(border=True):
                for reason in lead_details['score_reasons']:
                    st.markdown(f"- {reason}")
                st.markdown(f"**Puntuación Final: {lead_details['puntuacion']} / 100**")
