# -*- coding: utf-8 -*-
# =============================================================================
# MÓDULO DE CONEXIÓN CON KOMMO API
# =============================================================================
# Responsabilidad: Manejar toda la comunicación con la API de Kommo,
# incluyendo la paginación y la gestión de caché de datos.
# =============================================================================

import requests
import time
import os
import pickle
from datetime import datetime, timedelta
import streamlit as st

from config import CONFIG

class KommoAPI:
    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers

    def _make_request(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Error en la petición a {url}: {e}")
            return None

    def get_all_pages(self, endpoint, params=None):
        all_data = []
        url = f"{self.base_url}/{endpoint}"
        if params: url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])
        page_num = 1
        while url:
            data = self._make_request(url)
            if data and '_embedded' in data:
                item_key = list(data['_embedded'].keys())[0]
                all_data.extend(data['_embedded'][item_key])
                url = data.get('_links', {}).get('next', {}).get('href')
                page_num += 1
                time.sleep(0.2)
            else:
                url = None
        return all_data

def get_api_data(base_url, headers):
    cache_file = 'kommo_api_cache.pkl'
    cache_duration = timedelta(hours=CONFIG['cache_duration_hours'])
    
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            cached_data = pickle.load(f)
        if datetime.now() - cached_data['timestamp'] < cache_duration:
            st.sidebar.info("Usando datos desde caché.")
            return cached_data['data']
    
    with st.spinner('Obteniendo datos frescos desde la API de Kommo...'):
        api = KommoAPI(base_url, headers)
        st.sidebar.text("Cargando leads...")
        leads = api.get_all_pages('leads', params={'with': 'loss_reason,contacts'})
        st.sidebar.text("Cargando pipelines...")
        pipelines = api.get_all_pages('leads/pipelines')
        st.sidebar.text("Cargando usuarios...")
        users = api.get_all_pages('users')
        st.sidebar.text("Cargando motivos de pérdida...")
        loss_reasons = api.get_all_pages('leads/loss_reasons')
        
        data = {
            'leads': leads,
            'pipelines': pipelines,
            'users': users,
            'loss_reasons': loss_reasons
        }

    with open(cache_file, 'wb') as f:
        pickle.dump({'timestamp': datetime.now(), 'data': data}, f)
    
    return data
