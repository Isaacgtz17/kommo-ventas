# -*- coding: utf-8 -*-

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import seaborn as sns
import textwrap
import pandas as pd
from config import CONFIG # Importar la configuración para usar los colores

def crear_grafico_evolucion(df, filename, freq='M', title='Evolución de Nuevos Leads'):
    fig, ax = plt.subplots(figsize=(12, 6))
    data = df.set_index('created_at').resample(freq).size()
    freq_map = {'D': 'Diario', 'W': 'Semanal', 'M': 'Mensual'}
    full_title = f"{title} ({freq_map.get(freq, '')})"
    data.plot(marker='o', linestyle='-', color=CONFIG['colores']['texto'], zorder=1, ax=ax)
    if freq == 'D':
        def date_formatter(x, pos):
            dt = mdates.num2date(x)
            return f"{dt:%d}" if pos != 0 else f"{dt:%d\n%b\n%Y}"
        ax.xaxis.set_major_formatter(FuncFormatter(date_formatter))
        ax.xaxis.set_major_locator(mdates.DayLocator())
    elif freq == 'W':
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
    if not data.empty and freq == 'M':
        last_date, last_value = data.index[-1], data.iloc[-1]
        ax.plot(last_date, last_value, 'o', markersize=12, color=CONFIG['colores']['secundario'], zorder=5)
        ax.annotate(f'{last_value}', (last_date, last_value), textcoords="offset points", xytext=(0, 15), ha='center', fontsize=12, fontweight='bold')
    ax.set_title(full_title, fontsize=16, color=CONFIG['colores']['texto'])
    ax.set_ylabel('Cantidad de Leads')
    ax.set_xlabel('Fecha de Creación')
    fig.tight_layout()
    fig.savefig(filename)
    plt.close()

def crear_grafico_evolucion_comparativo(df_a, df_b, filename):
    fig, ax = plt.subplots(figsize=(12, 6))
    if not df_a.empty:
        data_a = df_a.set_index('created_at').resample('D').size()
        dias_a = (data_a.index - data_a.index[0]).days
        ax.plot(dias_a, data_a.values, marker='o', linestyle='-', label='Periodo Actual', color=CONFIG['colores']['principal'])
    if not df_b.empty:
        data_b = df_b.set_index('created_at').resample('D').size()
        dias_b = (data_b.index - data_b.index[0]).days
        ax.plot(dias_b, data_b.values, marker='o', linestyle='--', label='Periodo Anterior', color=CONFIG['colores']['texto'])
    ax.set_title("Creación de Leads: Comparativo de Periodos", fontsize=16, color=CONFIG['colores']['texto'])
    ax.set_ylabel('Cantidad de Leads')
    ax.set_xlabel('Día del Periodo (iniciando en Día 0)')
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    fig.savefig(filename)
    plt.close()

def crear_grafico_barras_h(data, title, xlabel, ylabel, filename, color_key='principal'):
    plt.figure(figsize=(10, 8))
    sns.barplot(x=data.values, y=data.index, orient='h', color=CONFIG['colores'][color_key])
    plt.title(title, fontsize=16, color=CONFIG['colores']['texto'])
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    for index, value in enumerate(data):
        plt.text(value, index, f' {value}', va='center', fontweight='bold')
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()

def crear_grafico_dona(data, title, filename):
    if data.empty: return
    # Aumentar el tamaño de la figura para dar espacio a la leyenda
    plt.figure(figsize=(12, 8))

    # --- CORRECCIÓN PARA EVITAR TEXTO ENCIMADO ---
    # 1. Calcular porcentajes para usarlos en la leyenda
    total = data.sum()
    percentages = (data / total * 100)
    
    # 2. Crear etiquetas para la leyenda que incluyan el nombre y el porcentaje
    legend_labels = [f'{label} ({percent:.1f}%)' for label, percent in zip(data.index, percentages)]

    # 3. Usar una paleta de colores variada
    colores_config = CONFIG.get('colores', {})
    donut_colors = [
        colores_config.get('principal', '#A12D2D'),
        colores_config.get('secundario', '#F0B400'),
        colores_config.get('texto', '#333333'),
        '#8C8C8C', '#B0C4DE', '#6A5ACD', '#778899', '#D2B48C', '#BC8F8F'
    ]

    # 4. Dibujar el gráfico de dona SIN etiquetas de texto internas
    plt.pie(data, startangle=90, wedgeprops=dict(width=0.4), colors=donut_colors)
    
    plt.title(title, fontsize=16, color=CONFIG['colores']['texto'], y=1.05)
    plt.axis('equal')
    
    # 5. Añadir una leyenda fuera del gráfico
    plt.legend(
        legend_labels,
        title="Motivos de Pérdida",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1) # Posiciona la leyenda a la derecha del gráfico
    )
    
    plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
    plt.close()


def crear_funnel_ejecutivo(df, filename):
    funnel_data = df.groupby(['responsable_nombre', 'estado']).size().unstack(fill_value=0)
    if funnel_data.empty: return

    order = ['Ganado', 'Proceso de Cobro', 'En Trámite', 'Perdido']
    
    for col in order:
        if col not in funnel_data.columns:
            funnel_data[col] = 0
            
    funnel_data = funnel_data[order]

    funnel_colors = [
        CONFIG['colores'].get('ganado', '#28a745'),
        CONFIG['colores'].get('proceso_cobro', '#0d6efd'),
        CONFIG['colores'].get('en_tramite', '#ffc107'),
        CONFIG['colores'].get('perdido', '#dc3545')
    ]

    funnel_perc = funnel_data.div(funnel_data.sum(axis=1), axis=0) * 100

    funnel_perc.plot(kind='barh', stacked=True, color=funnel_colors, figsize=(12, 8), width=0.8)
    
    plt.title('Funnel de Conversión por Ejecutivo', fontsize=16, color=CONFIG['colores']['texto'])
    plt.xlabel('Porcentaje de Leads (%)')
    plt.ylabel('Ejecutivo')
    plt.legend(title='Estado', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.gca().xaxis.set_major_formatter(FuncFormatter('{:.0f}%'.format))
    plt.savefig(filename, bbox_inches='tight')
    plt.close()

def crear_grafico_salud_leads(df, filename):
    health_counts = df[df['salud_lead'] != 'N/A']['salud_lead'].value_counts()
    if health_counts.empty: return

    health_order = ['Saludable', 'En Riesgo', 'Crítico']
    health_counts = health_counts.reindex(health_order, fill_value=0)
    
    colors = [
        CONFIG['colores'].get('ganado', '#28a745'),
        CONFIG['colores'].get('en_tramite', '#ffc107'),
        CONFIG['colores'].get('perdido', '#dc3545')
    ]
    
    plt.figure(figsize=(10, 6))
    sns.barplot(x=health_counts.index, y=health_counts.values, palette=colors)
    plt.title('Puntuación de Salud de Leads en Trámite', fontsize=16, color=CONFIG['colores']['texto'])
    plt.ylabel('Cantidad de Leads')
    plt.xlabel('Estado de Salud')
    for index, value in enumerate(health_counts):
        plt.text(index, value, f' {value}', ha='center', va='bottom', fontweight='bold')
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
