import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from PIL import Image
import tempfile
from streamlit_drawable_canvas import st_canvas  # 👈 componente para la firma

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

# Formulario para agregar un registro
with st.form("form_registro", clear_on_submit=True):
    id_entrega = st.text_input("ID Entrega")
    id_recibe = st.text_input("ID Recibe")
    orden = st.text_input("Orden de Producción")
    tipo = st.selectbox("Tipo", ["Parte fabricada", "Materia prima"], index=1)
    item = st.text_input("ID Item")
    cantidad = st.number_input("Cantidad", min_value=0, step=1)
    unidad = st.selectbox("Unidad", ["m", "und", "kg"], index=1)
    observacion = st.text_area("Observación")
    fecha = st.date_input("Fecha de diligenciamiento", datetime.today())

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

# Mostrar registros guardados
st.subheader("📑 Registros acumulados")
st.dataframe(st.session_state.data, use_container_width=True)

# Firma dibujada
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

# Guardar en Excel y PDF
if not st.session_state.data.empty:
    # Definir fecha para nombres de archivo
    fecha_hoy = datetime.today().strftime("%Y-%m-%d")

    # -----------------------
    # 📌 Descargar en Excel
    # -----------------------
    buffer_excel = BytesIO()
    st.session_state.data.to_excel(buffer_excel, index=False, engine="openpyxl")
    buffer_excel.seek(0)

    if st.download_button(
        label="⬇️ Descargar Excel",
        data=buffer_excel,
        file_name=f"registros_consumo_{fecha_hoy}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        st.session_state.data = pd.DataFrame(columns=st.session_state.data.columns)
        st.success("✅ Registros guardados en Excel y limpiados correctamente")

    # -----------------------
    # 📌 Descargar en PDF
    # -----------------------
    buffer_pdf = BytesIO()
    c = canvas.Canvas(buffer_pdf, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 14)
    c.drawString(2*cm, height-2*cm, "Informe de Consumo de Materia Prima")

    # Dibujar tabla simple
    text = c.beginText(2*cm, height-3*cm)
    text.setFont("Helvetica", 10)

    for i, row in st.session_state.data.iterrows():
        fila = " | ".join([str(x) for x in row.values])
        text.textLine(fila)

    c.drawText(text)

    # Guardar firma (si existe)
    if firma.image_data is not None:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
            img = Image.fromarray(firma.image_data.astype("uint8"))
            img.save(tmpfile.name)
            c.drawImage(tmpfile.name, 2*cm, 2*cm, width=5*cm, height=3*cm)

    c.showPage()
    c.save()
    buffer_pdf.seek(0)

    if st.download_button(
        label="⬇️ Descargar PDF con firma",
        data=buffer_pdf,
        file_name=f"informe_consumo_{fecha_hoy}.pdf",
        mime="application/pdf"
    ):
        st.session_state.data = pd.DataFrame(columns=st.session_state.data.columns)
        st.success("✅ Registros guardados en PDF y limpiados correctamente")