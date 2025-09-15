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

# Cargar el archivo de kits automáticamente
try:
    kit_data = pd.read_excel("Kits.xlsx")
    st.success("✅ Archivo de kits cargado correctamente.")
except FileNotFoundError:
    st.error("❌ Archivo 'Kits.xlsx' no encontrado en la misma carpeta.")
    kit_data = None


# ---
## Registro Manual de Ítems
# Formulario para agregar un registro
with st.form("form_registro", clear_on_submit=True):
    st.subheader("📝 Registro Manual")
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
## Registro por Kit
if kit_data is not None:
    st.subheader("📦 Registro por Kit")
    kit_options = kit_data['Kit'].unique()
    selected_kit = st.selectbox("Selecciona un kit para entregar", kit_options)

    col_kit1, col_kit2 = st.columns(2)
    with col_kit1:
        id_entrega_kit = st.text_input("ID Entrega (Kit)", key="id_entrega_kit")
    with col_kit2:
        id_recibe_kit = st.text_input("ID Recibe (Kit)", key="id_recibe_kit")

    if st.button("➕ Agregar kit al registro", key="add_kit_button"):
        if selected_kit:
            items_to_add = kit_data[kit_data['Kit'] == selected_kit]
            
            nuevos_registros = []
            for _, row in items_to_add.iterrows():
                nuevo = {
                    "ID Entrega": id_entrega_kit,
                    "ID Recibe": id_recibe_kit,
                    "Orden": "ORDEN_KIT",
                    "Tipo": "Materia prima",
                    "Item": row['Item'],
                    "Cantidad": row['Cantidad'],
                    "Unidad": row['Unidad'],
                    "Observación": f"Consumo de kit: {selected_kit}",
                    "Fecha": datetime.today().date()
                }
                nuevos_registros.append(nuevo)

            st.session_state.data = pd.concat(
                [st.session_state.data, pd.DataFrame(nuevos_registros)],
                ignore_index=True
            )
            st.success(f"✅ Se agregaron todos los ítems del kit '{selected_kit}' al registro.")

# ---
## Registros Acumulados
st.subheader("📑 Registros acumulados")
st.dataframe(st.session_state.data, use_container_width=True)

# ---
## Firma y Descargas
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

# Descargar en Excel y PDF
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
        on_click=clear_data
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
        # Ajusta los anchos de columna para que quepan los datos
        col_widths = [2.5, 2.5, 2, 2, 2, 2, 1.5, 3] # Anchos relativos
        
        # Alinear encabezados de las columnas
        x_offsets = [margin]
        for i in range(len(dataframe.columns) - 1):
            x_offsets.append(x_offsets[-1] + col_widths[i])
        
        for i, header in enumerate(dataframe.columns):
            c.drawString(x_offsets[i]*cm, y_pos, header)
        
        # Datos de la tabla
        c.setFont("Helvetica", 8)
        y_pos -= 0.5*cm
        for _, row in dataframe.iterrows():
            if y_pos < margin + 5*cm: # Verificar para una nueva página
                c.showPage()
                y_pos = height - margin
                c.setFont("Helvetica-Bold", 9)
                for i, header in enumerate(dataframe.columns):
                    c.drawString(x_offsets[i]*cm, y_pos, header)
                c.setFont("Helvetica", 8)
                y_pos -= 0.5*cm
            
            for i, val in enumerate(row.values):
                c.drawString(x_offsets[i]*cm, y_pos, str(val))
            y_pos -= 0.5*cm
            
        # Firma
        if firma.image_data is not None:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, margin + 4.5*cm, "Firma de Recibido:")
            
            img_stream = BytesIO()
            Image.fromarray(signature_image.astype("uint8")).save(img_stream, format="PNG")
            img_stream.seek(0)
            
            c.drawImage(
                "signature.png", 
                img_stream,
                x=margin,
                y=margin + 1*cm,
                width=5*cm,
                height=3*cm
            )
            c.line(margin, margin + 1*cm, margin + 5*cm, margin + 1*cm)
        
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
            on_click=clear_data
        )