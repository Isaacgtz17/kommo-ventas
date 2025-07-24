# -*- coding: utf-8 -*-
import requests
import time
import streamlit as st
from config import CONFIG

class KommoAPI:
    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers

    def _make_request(self, url):
        """Hace una petición a la API y maneja los errores."""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # Lanza un error para respuestas 4xx/5xx
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            st.error(f"Error de HTTP en la petición a {url}: {http_err}")
            # Específicamente para errores de autenticación
            if response.status_code == 401:
                st.error("Error de autenticación (401). Verifica que tus 'secrets' en Streamlit Cloud sean correctos.")
        except requests.exceptions.RequestException as e:
            st.error(f"Error en la petición a {url}: {e}")
        return None

    def get_all_pages(self, endpoint, params=None):
        """Obtiene datos de todos las páginas de un endpoint de la API."""
        all_data = []
        url = f"{self.base_url}/{endpoint}"
        if params:
            url += "?" + "&".join([f"{k}={v}" for k, v in params.items()])

        page_num = 1
        with st.spinner(f"Cargando datos desde el endpoint '{endpoint}'..."):
            while url:
                data = self._make_request(url)
                if data and '_embedded' in data:
                    # La clave de los items puede variar (e.g., 'leads', 'users')
                    item_key = list(data['_embedded'].keys())[0]
                    all_data.extend(data['_embedded'][item_key])
                    
                    # Obtener la URL de la siguiente página
                    url = data.get('_links', {}).get('next', {}).get('href')
                    page_num += 1
                    time.sleep(0.2) # Pequeña pausa para no saturar la API
                else:
                    # Si no hay más datos o hubo un error, detenemos el bucle
                    url = None
        return all_data

def get_api_data(base_url, headers):
    """
    Función principal para obtener todos los datos necesarios de la API.
    Esta función es la que será cacheada por @st.cache_data en la página principal.
    """
    api = KommoAPI(base_url, headers)
    
    # Realizar todas las llamadas a la API
    data = {
        'leads': api.get_all_pages('leads', params={'with': 'loss_reason,contacts'}),
        'pipelines': api.get_all_pages('leads/pipelines'),
        'users': api.get_all_pages('users'),
        'loss_reasons': api.get_all_pages('leads/loss_reasons')
    }
    
    # Verificar si alguna de las llamadas falló
    if not all(data.values()):
        st.error("Fallo al obtener algunos de los datos de la API. La aplicación podría no funcionar correctamente.")
        return None

    return data
