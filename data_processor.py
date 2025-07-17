# -*- coding: utf-8 -*-
# =============================================================================
# MÓDULO DE PROCESAMIENTO DE DATOS
# =============================================================================
# Responsabilidad: Tomar los datos crudos de la API y transformarlos
# en un DataFrame de pandas limpio, enriquecido y listo para el análisis.
# =============================================================================

import pandas as pd
import numpy as np
import unicodedata
from datetime import datetime
import streamlit as st

from config import CONFIG

def normalizar_texto(texto):
    if not isinstance(texto, str): return texto
    s = ''.join(c for c in unicodedata.normalize('NFD', texto.lower()) if unicodedata.category(c) != 'Mn')
    return s.title()

def procesar_datos(api_data):
    if not api_data or not api_data.get('leads'):
        st.error("No se encontraron leads para procesar.")
        return pd.DataFrame()
    
    df = pd.DataFrame(api_data['leads'])
    user_map = {user['id']: user['name'] for user in api_data['users']}
    loss_reason_map = {reason['id']: reason['name'] for reason in api_data['loss_reasons']}
    pipeline_map, status_map = {}, {}
    for p in api_data['pipelines']:
        pipeline_map[p['id']] = p['name']
        for s in p['_embedded']['statuses']: status_map[s['id']] = {'name': s['name'], 'pipeline_id': p['id']}
    
    df['responsable_nombre'] = df['responsible_user_id'].map(user_map).fillna('No asignado')
    df['etapa_nombre'] = df['status_id'].apply(lambda x: status_map.get(x, {}).get('name', 'Etapa Desconocida')).apply(normalizar_texto)
    df['pipeline_nombre'] = df['status_id'].apply(lambda x: status_map.get(x, {}).get('pipeline_id')).map(pipeline_map)
    df['motivo_perdida_nombre'] = df['loss_reason_id'].map(loss_reason_map).fillna('No especificado')
    df['tags'] = df.apply(lambda lead: [tag['name'] for tag in lead.get('_embedded', {}).get('tags', [])], axis=1)
    
    for col in ['created_at', 'updated_at', 'closed_at']:
        df[col] = pd.to_datetime(df[col], unit='s', errors='coerce')
    
    df = df[df['pipeline_nombre'] != CONFIG['pipeline_a_excluir']]
    
    df['estado'] = np.where(df['status_id'] == 142, 'Ganado', np.where(df['status_id'] == 143, 'Perdido', 'En Trámite'))
    df['dias_para_cerrar'] = (df['closed_at'] - df['created_at']).dt.days
    df['dias_sin_actualizar'] = (datetime.now() - df['updated_at']).dt.days
    
    def get_lead_health(row):
        if row['estado'] != 'En Trámite': return 'N/A'
        if row['dias_sin_actualizar'] >= CONFIG['dias_lead_critico']: return 'Crítico'
        if row['dias_sin_actualizar'] >= CONFIG['dias_lead_en_riesgo']: return 'En Riesgo'
        return 'Saludable'
    df['salud_lead'] = df.apply(get_lead_health, axis=1)
    
    return df
