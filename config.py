# -*- coding: utf-8 -*-
# =============================================================================
# MÓDULO DE CONFIGURACIÓN
# =============================================================================
# Responsabilidad: Centralizar todas las configuraciones no sensibles 
# de la aplicación para facilitar su mantenimiento.
# =============================================================================

CONFIG = {
    'pipeline_a_excluir': "whatsapp",
    'cache_duration_hours': 4,
    'dias_lead_en_riesgo': 15,
    'dias_lead_critico': 30,
    'colores': {
        'principal': '#A12D2D',
        'secundario': '#F0B400',
        'texto': '#333333',
        'fondo_claro': '#F5F5F5',
        'borde': '#DCDCDC',
        'ganado': '#28a745',
        'en_tramite': '#ffc107',
        'perdido': '#dc3545',
        'aumento': '#28a745',
        'disminucion': '#dc3545'
    }
}
