# -*- coding: utf-8 -*-
# =============================================================================
# MÓDULO DE GENERACIÓN DE PDF Y ENVÍO DE CORREO
# =============================================================================
# Responsabilidad: Contener la clase PDF, las funciones que ensamblan
# los reportes y la lógica para enviar correos electrónicos.
# =============================================================================

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from PIL import Image
import streamlit as st
from datetime import datetime
import pandas as pd

from config import CONFIG
import visualizations as viz

# =============================================================================
# FUNCIÓN DE ENVÍO DE CORREO
# =============================================================================
def enviar_correo(asunto, cuerpo, archivo_adjunto):
    """Envía un correo electrónico con un archivo adjunto al destinatario configurado."""
    try:
        cfg = st.secrets['email_settings']
        destinatario = cfg['recipient_email']
        sender_email = cfg['sender_email']
        sender_password = cfg['sender_password']
    except (FileNotFoundError, KeyError):
        st.error("Error: Credenciales de correo no encontradas en .streamlit/secrets.toml")
        return

    if not all([sender_email, sender_password, destinatario]):
        st.warning("La función de envío de correo no está completamente configurada en secrets.toml.")
        return

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        with open(archivo_adjunto, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename= {os.path.basename(archivo_adjunto)}")
        msg.attach(part)

        server = smtplib.SMTP(CONFIG['email_settings']['smtp_server'], CONFIG['email_settings']['smtp_port'])
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, destinatario, text)
        server.quit()
        st.success(f"✅ Correo enviado exitosamente a {destinatario}")
    except FileNotFoundError:
        st.error(f"❌ Error: No se encontró el archivo adjunto '{archivo_adjunto}'")
    except smtplib.SMTPAuthenticationError:
        st.error("❌ Error de autenticación SMTP. Verifica tu correo y contraseña de aplicación.")
    except Exception as e:
        st.error(f"❌ Ocurrió un error al enviar el correo: {e}")


# =============================================================================
# CLASE PDF
# =============================================================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(int(CONFIG['colores']['texto'][1:3], 16), int(CONFIG['colores']['texto'][3:5], 16), int(CONFIG['colores']['texto'][5:7], 16))
        self.cell(0, 10, 'Reporte de Análisis de Ventas - Grúas Móviles del Golfo', 0, 1, 'C')
        self.set_font('Arial', 'I', 8)
        self.cell(0, 5, f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def _chapter_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.set_fill_color(int(CONFIG['colores']['fondo_claro'][1:3], 16), int(CONFIG['colores']['fondo_claro'][3:5], 16), int(CONFIG['colores']['fondo_claro'][5:7], 16))
        self.set_text_color(int(CONFIG['colores']['texto'][1:3], 16), int(CONFIG['colores']['texto'][3:5], 16), int(CONFIG['colores']['texto'][5:7], 16))
        self.cell(0, 10, f" {title}", 0, 1, 'L', 1)
        self.ln(5)

    def _draw_kpi_row(self, kpis):
        col_width = self.w / len(kpis) - 10 if len(kpis) > 0 else self.w - 20
        for title, value in kpis:
            self.set_draw_color(int(CONFIG['colores']['principal'][1:3], 16), int(CONFIG['colores']['principal'][3:5], 16), int(CONFIG['colores']['principal'][5:7], 16))
            self.set_line_width(1)
            self.line(self.get_x(), self.get_y(), self.get_x() + col_width, self.get_y())
            self.set_draw_color(int(CONFIG['colores']['borde'][1:3], 16), int(CONFIG['colores']['borde'][3:5], 16), int(CONFIG['colores']['borde'][5:7], 16))
            self.set_line_width(0.2)
            self.rect(self.get_x(), self.get_y(), col_width, 20)
            self.set_font('Arial', 'B', 10)
            self.cell(col_width, 8, title, 0, 2, 'C')
            self.set_font('Arial', 'B', 14)
            self.cell(col_width, 10, str(value), 0, 0, 'C')
            self.set_x(self.get_x() + 5)
        self.ln(25)

    def add_kpi_section(self, title, kpi_rows):
        self.check_page_break(20 + len(kpi_rows) * 25)
        self._chapter_title(title)
        for row in kpi_rows:
            self._draw_kpi_row(row)

    def add_image_section(self, title, image_path):
        if not os.path.exists(image_path):
            self.check_page_break(30)
            self._chapter_title(title)
            self.cell(0, 10, '(Gráfico no generado por falta de datos)', 0, 1, 'C')
            self.ln(5)
            return
        with Image.open(image_path) as img:
            img_w, img_h = img.size
        aspect_ratio = img_h / img_w
        pdf_image_w = self.w - 20
        pdf_image_h = pdf_image_w * aspect_ratio
        required_height = 15 + pdf_image_h
        self.check_page_break(required_height)
        self._chapter_title(title)
        self.image(image_path, x=self.get_x() + 10, w=pdf_image_w)
        self.ln(pdf_image_h + 5)

    def add_table_section(self, title, df, col_widths):
        title_h, header_h, row_h = 15, 10, 8
        table_h = header_h + (len(df) * row_h)
        required_height = title_h + table_h
        self.check_page_break(required_height)
        self._chapter_title(title)
        self.set_font("Arial", "B", 9)
        self.set_fill_color(int(CONFIG['colores']['fondo_claro'][1:3], 16), int(CONFIG['colores']['fondo_claro'][3:5], 16), int(CONFIG['colores']['fondo_claro'][5:7], 16))
        self.set_draw_color(int(CONFIG['colores']['borde'][1:3], 16), int(CONFIG['colores']['borde'][3:5], 16), int(CONFIG['colores']['borde'][5:7], 16))
        self.set_line_width(0.2)
        for i, header in enumerate(df.columns):
            self.cell(col_widths[i], header_h, header, 1, 0, "C", 1)
        self.ln()
        self.set_font("Arial", "", 8)
        for i, row in df.iterrows():
            fill = i % 2 != 0
            self.set_fill_color(int(CONFIG['colores']['fondo_claro'][1:3], 16), int(CONFIG['colores']['fondo_claro'][3:5], 16), int(CONFIG['colores']['fondo_claro'][5:7], 16)) if fill else self.set_fill_color(255, 255, 255)
            for j, item in enumerate(row):
                self.cell(col_widths[j], row_h, str(item), 1, 0, "C", fill)
            self.ln()
        self.ln(10)

    def add_comparison_kpi_table(self, title, kpi_data):
        self.check_page_break(20 + len(kpi_data) * 8)
        self._chapter_title(title)
        
        self.set_font("Arial", "B", 10)
        self.set_fill_color(int(CONFIG['colores']['fondo_claro'][1:3], 16), int(CONFIG['colores']['fondo_claro'][3:5], 16), int(CONFIG['colores']['fondo_claro'][5:7], 16))
        self.cell(60, 8, "Métrica", 1, 0, 'L', 1)
        self.cell(40, 8, "Periodo Actual", 1, 0, 'C', 1)
        self.cell(40, 8, "Periodo Anterior", 1, 0, 'C', 1)
        self.cell(40, 8, "Variación", 1, 1, 'C', 1)

        self.set_font('Arial', '', 10)
        for row in kpi_data:
            self.cell(60, 8, row['metric'], 1, 0, 'L')
            self.cell(40, 8, str(row['current']), 1, 0, 'C')
            self.cell(40, 8, str(row['previous']), 1, 0, 'C')
            
            change_str = f"{row['change']:.2f}%"
            if row['change'] > 0:
                self.set_text_color(int(CONFIG['colores']['aumento'][1:3], 16), int(CONFIG['colores']['aumento'][3:5], 16), int(CONFIG['colores']['aumento'][5:7], 16))
                change_str = f"+{change_str}"
            else:
                self.set_text_color(int(CONFIG['colores']['perdido'][1:3], 16), int(CONFIG['colores']['perdido'][3:5], 16), int(CONFIG['colores']['perdido'][5:7], 16))
            
            self.cell(40, 8, change_str, 1, 1, 'C')
            self.set_text_color(int(CONFIG['colores']['texto'][1:3], 16), int(CONFIG['colores']['texto'][3:5], 16), int(CONFIG['colores']['texto'][5:7], 16))
        self.ln(10)

    def check_page_break(self, required_height):
        if self.get_y() + required_height > self.h - self.b_margin:
            self.add_page()

# =============================================================================
# CLASE GENERADORA DE REPORTES
# =============================================================================
class ReportGenerator:
    def __init__(self, df_master):
        self.df = df_master

    def generar_reporte_por_fechas(self, df_periodo, filename, title_prefix):
        if df_periodo.empty: 
            st.warning(f"No se encontraron datos para el reporte '{title_prefix}'.")
            return None

        pdf = PDF('P', 'mm', 'A4')
        pdf.add_page()

        total_leads = len(df_periodo)
        leads_ganados = (df_periodo['estado'] == 'Ganado').sum()
        tasa_conversion = (leads_ganados / total_leads * 100) if total_leads > 0 else 0
        valor_ganado = df_periodo[df_periodo['estado'] == 'Ganado']['price'].sum()
        valor_en_cobro = df_periodo[df_periodo['etapa_nombre'] == 'Proceso De Cobro']['price'].sum()
        
        kpi_row1 = [("Leads Generados", total_leads), ("Leads Ganados", leads_ganados), ("Tasa Conversión", f"{tasa_conversion:.2f}%")]
        kpi_row2 = [("Valor Ventas Ganadas", f"${valor_ganado:,.2f}"), ("En Proceso de Cobro", f"${valor_en_cobro:,.2f}")]
        pdf.add_kpi_section(title_prefix, [kpi_row1, kpi_row2])

        files_to_clean = []

        if not df_periodo.empty:
            rendimiento = df_periodo.groupby('responsable_nombre').agg(
                Total=('id', 'count'),
                Ganados=('estado', lambda x: (x == 'Ganado').sum()),
                Perdidos=('estado', lambda x: (x == 'Perdido').sum()),
                En_Tramite=('estado', lambda x: (x == 'En Trámite').sum()),
                Valor_Ganado=('price', lambda x: df_periodo.loc[x.index][df_periodo.loc[x.index, 'estado'] == 'Ganado']['price'].sum())
            ).reset_index()
            if not rendimiento.empty:
                rendimiento['Conversión'] = (rendimiento['Ganados'] / rendimiento['Total'] * 100).apply(lambda x: f"{x:.1f}%")
                rendimiento['Valor_Ganado'] = rendimiento['Valor_Ganado'].apply(lambda x: f"${x:,.0f}")
                rendimiento.columns = ['Ejecutivo', 'Total', 'Ganados', 'Perdidos', 'Trámite', 'Valor Ganado', 'Conversión']
                pdf.add_table_section("Tabla de Rendimiento por Ejecutivo", rendimiento, col_widths=[65, 20, 20, 20, 20, 25, 25])

            delta_dias = (df_periodo['created_at'].max() - df_periodo['created_at'].min()).days
            freq = 'D' if delta_dias <= 15 else 'W' if delta_dias <= 90 else 'M'
            img_evolucion = "evolucion_periodo.png"; viz.crear_grafico_evolucion(df_periodo, img_evolucion, freq=freq, title='Creación de Leads'); files_to_clean.append(img_evolucion)
            pdf.add_image_section("Creación de Leads en el Periodo", img_evolucion)

            resp_data = df_periodo['responsable_nombre'].value_counts().sort_values()
            img_resp = "responsables_periodo.png"; viz.crear_grafico_barras_h(resp_data, 'Distribución de Leads por Responsable', 'Cantidad de Leads', 'Ejecutivo', img_resp); files_to_clean.append(img_resp)
            pdf.add_image_section("Distribución de Leads por Responsable", img_resp)

            etapa_data = df_periodo['etapa_nombre'].value_counts().sort_values()
            img_etapas = "etapas_periodo.png"; viz.crear_grafico_barras_h(etapa_data, 'Distribución de Leads por Etapa Actual', 'Cantidad de Leads', 'Etapa', img_etapas); files_to_clean.append(img_etapas)
            pdf.add_image_section("Distribución de Leads por Etapa Actual", img_etapas)
            
            img_salud = "salud_periodo.png"; viz.crear_grafico_salud_leads(df_periodo, img_salud); files_to_clean.append(img_salud)
            if os.path.exists(img_salud): pdf.add_image_section("Salud de Leads en Trámite", img_salud)

        img_funnel = "funnel_periodo.png"; viz.crear_funnel_ejecutivo(df_periodo, img_funnel); files_to_clean.append(img_funnel)
        if os.path.exists(img_funnel): pdf.add_image_section("Funnel de Conversión por Ejecutivo", img_funnel)
        
        tags_series = df_periodo.explode('tags')['tags'].dropna()
        if not tags_series.empty:
            top_tags = tags_series.value_counts().nlargest(10).sort_values()
            img_tags = "tags_periodo.png"; viz.crear_grafico_barras_h(top_tags, 'Servicios Más Solicitados (Top 10 Tags)', 'Cantidad de Leads', 'Servicio/Tag', img_tags); files_to_clean.append(img_tags)
            pdf.add_image_section("Servicios Más Solicitados (Basado en Etiquetas)", img_tags)

        loss_data = df_periodo[df_periodo['estado'] == 'Perdido']['motivo_perdida_nombre'].value_counts()
        if not loss_data.empty:
            img_perdida = "perdida_periodo.png"; viz.crear_grafico_dona(loss_data, 'Principales Motivos de Pérdida', img_perdida); files_to_clean.append(img_perdida)
            pdf.add_image_section("Análisis de Motivos de Pérdida", img_perdida)

        pdf.output(filename)
        st.success(f"✅ Reporte guardado como '{filename}'")
        for f in files_to_clean:
            if os.path.exists(f): os.remove(f)
        return filename

    def generar_reporte_comparativo(self, df_a, df_b, period_a_str, period_b_str, filename):
        pdf = PDF('P', 'mm', 'A4')
        pdf.add_page()

        def get_kpis(df):
            if df.empty:
                return {"Leads Generados": 0, "Leads Ganados": 0, "Tasa de Conversión (%)": 0, "Valor Ganado ($)": 0, "En Proceso de Cobro ($)": 0}
            total_leads = len(df)
            leads_ganados = (df['estado'] == 'Ganado').sum()
            tasa_conv = (leads_ganados / total_leads * 100) if total_leads > 0 else 0
            valor_ganado = df[df['estado'] == 'Ganado']['price'].sum()
            valor_en_cobro = df[df['etapa_nombre'] == 'Proceso De Cobro']['price'].sum()
            return {
                "Leads Generados": total_leads, "Leads Ganados": leads_ganados, 
                "Tasa de Conversión (%)": tasa_conv, "Valor Ganado ($)": valor_ganado,
                "En Proceso de Cobro ($)": valor_en_cobro
            }

        kpis_a = get_kpis(df_a)
        kpis_b = get_kpis(df_b)
        
        comparison_data = []
        for key in kpis_a:
            val_a, val_b = kpis_a[key], kpis_b[key]
            change = ((val_a - val_b) / val_b * 100) if val_b > 0 else (100.0 if val_a > 0 else 0)
            
            is_currency = '$' in key
            is_percent = '%' in key

            formatted_a = f"${val_a:,.2f}" if is_currency else (f"{val_a:.2f}" if is_percent else f"{val_a:,}")
            formatted_b = f"${val_b:,.2f}" if is_currency else (f"{val_b:.2f}" if is_percent else f"{val_b:,}")
            
            comparison_data.append({'metric': key, 'current': formatted_a, 'previous': formatted_b, 'change': change})
        
        pdf.add_comparison_kpi_table(f"Comparativo: {period_a_str} vs {period_b_str}", comparison_data)
        
        files_to_clean = []
        
        img_comp_evol = "comparativo_evolucion.png"; viz.crear_grafico_evolucion_comparativo(df_a, df_b, img_comp_evol); files_to_clean.append(img_comp_evol)
        if os.path.exists(img_comp_evol): pdf.add_image_section("Creación de Leads: Comparativo de Periodos", img_comp_evol)

        if not df_a.empty:
            rendimiento = df_a.groupby('responsable_nombre').agg(
                Total=('id', 'count'), Ganados=('estado', lambda x: (x == 'Ganado').sum()),
                Valor_Ganado=('price', lambda x: df_a.loc[x.index][df_a.loc[x.index, 'estado'] == 'Ganado']['price'].sum())
            ).reset_index()
            if not rendimiento.empty:
                rendimiento['Tasa_Conv.'] = (rendimiento['Ganados'] / rendimiento['Total'] * 100).apply(lambda x: f"{x:.1f}%")
                rendimiento['Valor_Ganado'] = rendimiento['Valor_Ganado'].apply(lambda x: f"${x:,.0f}")
                rendimiento.columns = ['Ejecutivo', 'Total', 'Ganados', 'Valor Ganado', 'Tasa Conv.']
                pdf.add_table_section(f"Rendimiento por Ejecutivo (Periodo Actual)", rendimiento, col_widths=[85, 25, 25, 30, 25])

        img_funnel = "funnel_comparativo.png"; viz.crear_funnel_ejecutivo(df_a, img_funnel); files_to_clean.append(img_funnel)
        if os.path.exists(img_funnel): pdf.add_image_section("Funnel de Conversión (Periodo Actual)", img_funnel)
        
        pdf.output(filename)
        st.success(f"✅ Reporte comparativo guardado como '{filename}'")
        for f in files_to_clean:
            if os.path.exists(f): os.remove(f)
        return filename