import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# 📋 Título y configuración inicial
st.set_page_config(layout="wide")
st.title("📋 Registro de consumo de materia prima")

# Inicializar DataFrame en sesión
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(
        columns=[
            "ID Entrega",
            "ID Recibe",
            "Orden",
            "Tipo",
            "Item",
            "Cantidad",
            "Unidad",
            "Observación",
            "Fecha"
        ]
    )

# ---
## Agregar un nuevo registro
# Formulario para agregar un registro
with st.form("form_registro", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        id_entrega = st.text_input("ID Entrega")
        id_recibe = st.text_input("ID Recibe")
        orden = st.text_input("Orden de Producción")
    with col2:
        tipo = st.selectbox("Tipo", ["Parte fabricada", "Materia prima"], index=1)
        item = st.text_input("ID Item")
        cantidad = st.number_input("Cantidad", min_value=0, step=1)
    
    col3, col4 = st.columns(2)
    with col3:
        unidad = st.selectbox("Unidad", ["m", "und", "kg"], index=1)
        fecha = st.date_input("Fecha de diligenciamiento", datetime.today())
    with col4:
        observacion = st.text_area("Observación")

    submitted = st.form_submit_button("➕ Agregar registro")

    if submitted:
        nuevo = {
            "ID Entrega": id_entrega,
            "ID Recibe": id_recibe,
            "Orden": orden,
            "Tipo": tipo,
            "Item": item,
            "Cantidad": cantidad,
            "Unidad": unidad,
            "Observación": observacion,
            "Fecha": fecha
        }
        st.session_state.data = pd.concat(
            [st.session_state.data, pd.DataFrame([nuevo])],
            ignore_index=True
        )
        st.success("✅ Registro agregado correctamente")

# ---
## Registros acumulados
# Mostrar registros guardados
st.subheader("📑 Registros acumulados")
st.dataframe(st.session_state.data, use_container_width=True)

# ---
## Firma y Descarga
st.subheader("✍️ Firma de recibido")
firma = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=2,
    stroke_color="black",
    background_color="white",
    height=150,
    drawing_mode="freedraw",
    key="canvas"
)

# Función auxiliar para borrar los datos
def clear_data():
    st.session_state.data = pd.DataFrame(columns=st.session_state.data.columns)
    st.success("✅ Registros guardados y limpiados correctamente")

# ---
### Descargas
if not st.session_state.data.empty:
    fecha_hoy = datetime.today().strftime("%Y-%m-%d")

    # 📌 Descargar en Excel
    excel_buffer = BytesIO()
    st.session_state.data.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)
    
    st.download_button(
        label="⬇️ Descargar Excel",
        data=excel_buffer,
        file_name=f"registros_consumo_{fecha_hoy}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        on_click=clear_data # La forma correcta de borrar datos
    )

    # 📌 Descargar en PDF
    def generate_pdf(dataframe, signature_image):
        buffer_pdf = BytesIO()
        c = canvas.Canvas(buffer_pdf, pagesize=A4)
        width, height = A4
        margin = 2*cm
        
        # Título
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, height - margin, "Informe de Consumo de Materia Prima")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - margin - 0.7*cm, f"Fecha: {datetime.today().strftime('%Y-%m-%d')}")
        
        # Cabeceras de la tabla
        c.setFont("Helvetica-Bold", 9)
        y_pos = height - 4*cm
        column_widths = [1.5, 1.5, 2, 1.5, 1.5, 1.5, 1, 3] # Anchos relativos
        col_names = st.session_state.data.columns[:-2] # Excluir 'Observación' y 'Fecha' para la tabla
        x_offsets = [margin]
        current_x = margin
        for i in range(len(col_names) - 1):
            current_x += column_widths[i] * cm
            x_offsets.append(current_x)
            
        for i, header in enumerate(col_names):
            c.drawString(x_offsets[i], y_pos, header)
        
        # Datos de la tabla
        c.setFont("Helvetica", 8)
        y_pos -= 0.5*cm
        for _, row in dataframe.iterrows():
            if y_pos < margin + 5*cm: # Verificar para una nueva página
                c.showPage()
                y_pos = height - margin
                c.setFont("Helvetica-Bold", 9)
                for i, header in enumerate(col_names):
                    c.drawString(x_offsets[i], y_pos, header)
                c.setFont("Helvetica", 8)
                y_pos -= 0.5*cm
            
            for i, val in enumerate(row.values[:-2]):
                c.drawString(x_offsets[i], y_pos, str(val))
            y_pos -= 0.5*cm
            
        # Firma
        if signature_image is not None:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, margin + 4.5*cm, "Firma de Recibido:")
            
            # Convertir los datos de la imagen a un formato que ReportLab pueda usar
            img_stream = BytesIO()
            Image.fromarray(signature_image.astype("uint8")).save(img_stream, format="PNG")
            img_stream.seek(0)
            c.drawImage(
                img_stream,
                x=margin,
                y=margin + 1*cm,
                width=5*cm,
                height=3*cm
            )
            c.line(margin, margin + 1*cm, margin + 5*cm, margin + 1*cm) # Línea para la firma
        
        c.save()
        buffer_pdf.seek(0)
        return buffer_pdf

    if firma.image_data is not None:
        pdf_buffer = generate_pdf(st.session_state.data, firma.image_data)
        st.download_button(
            label="⬇️ Descargar PDF con firma",
            data=pdf_buffer,
            file_name=f"informe_consumo_{fecha_hoy}.pdf",
            mime="application/pdf",
            on_click=clear_data # La forma correcta de borrar datos
        )