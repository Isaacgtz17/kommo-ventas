import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Script para debuggear fechas reales
def debug_fechas_reales():
    st.title("🔍 Debug de Fechas Reales")
    
    try:
        # Cargar datos reales
        from PaginaPrincipal import cargar_y_procesar_datos
        df = cargar_y_procesar_datos()
        
        if df is not None and not df.empty:
            st.success(f"✅ Datos cargados: {len(df)} leads")
            
            # Información básica de fechas
            st.subheader("📅 Información de Fechas")
            st.write(f"**Fecha más antigua:** {df['created_at'].min()}")
            st.write(f"**Fecha más reciente:** {df['created_at'].max()}")
            st.write(f"**Fecha actual del sistema:** {datetime.now()}")
            
            # Contar leads por año
            st.subheader("📊 Distribución por Año")
            df['year'] = df['created_at'].dt.year
            year_counts = df['year'].value_counts().sort_index()
            st.bar_chart(year_counts)
            
            # Mostrar algunos ejemplos de fechas
            st.subheader("🔍 Ejemplos de Fechas")
            sample_data = df[['id', 'name', 'created_at']].head(10)
            st.dataframe(sample_data)
            
            # Filtro de últimos 30 días
            st.subheader("⏰ Filtro de Últimos 30 Días")
            today = datetime.now().date()
            start_date = today - timedelta(days=29)
            
            st.write(f"**Filtro aplicado:** desde {start_date} hasta {today}")
            
            df_filtered = df[
                (df['created_at'].dt.date >= start_date) &
                (df['created_at'].dt.date <= today)
            ]
            
            st.write(f"**Leads encontrados en últimos 30 días:** {len(df_filtered)}")
            
            if not df_filtered.empty:
                st.write("**Fechas de estos leads:**")
                dates_only = df_filtered['created_at'].dt.date.unique()
                st.write(sorted(dates_only))
            else:
                st.warning("No hay leads en los últimos 30 días")
                
        else:
            st.error("❌ No se pudieron cargar los datos")
            
    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    debug_fechas_reales()
