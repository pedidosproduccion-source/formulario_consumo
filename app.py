import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from reportlab.lib.utils import ImageReader

# 📋 Título y configuración inicial
st.set_page_config(layout="wide")
st.title("📋 Registro de consumo de materia prima")

# --- CONEXIÓN Y CONFIGURACIÓN DE LA BASE DE DATOS SQLite ---
# Conectar a la base de datos (se crea si no existe)
conn = sqlite3.connect("registros.db")
c = conn.cursor()

# Crear la tabla si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS registros (
        "ID Entrega" TEXT,
        "ID Recibe" TEXT,
        "Orden" TEXT,
        "Tipo" TEXT,
        "Item" TEXT,
        "Cantidad" INTEGER,
        "Unidad" TEXT,
        "Observación" TEXT,
        "Fecha" TEXT
    )
''')
conn.commit()

# Cargar los datos desde la base de datos al DataFrame de la sesión
def load_data_from_db():
    df = pd.read_sql_query("SELECT * FROM registros", conn)
    # Convertir la columna de fecha a formato de fecha
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    st.session_state.data = df

# Inicializar las variables de estado al inicio de la aplicación
if "data" not in st.session_state:
    load_data_from_db()
if "edited_kit_data" not in st.session_state:
    st.session_state.edited_kit_data = None
if "selected_record" not in st.session_state:
    st.session_state.selected_record = None

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
        
        # Insertar datos en la base de datos
        c.execute("INSERT INTO registros VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(nuevo.values()))
        conn.commit()
        
        load_data_from_db() # Recargar los datos desde la BD a la sesión
        st.success("✅ Registro agregado correctamente")
        st.rerun()

# ---
## Registro por Kit
if kit_data is not None:
    st.subheader("📦 Registro por Kit")
    
    try:
        kit_data['Kit'] = kit_data['Kit'].str.strip()
        kit_options = kit_data['Kit'].unique()
        
        # Unificamos los campos en un solo selectbox
        selected_kit = st.selectbox(
            "Selecciona o digita un kit", 
            options=kit_options, 
            key="selectbox_kit"
        )
        
        # Campos de orden y observación para el módulo de kits
        col_kit_info1, col_kit_info2 = st.columns(2)
        with col_kit_info1:
            orden_kit = st.text_input("Orden de Producción (Kit)")
        with col_kit_info2:
            observacion_kit = st.text_area("Observación (Kit)")

        if st.button("🔍 Ver y editar kit"):
            items_to_add = kit_data[kit_data['Kit'] == selected_kit].copy()
            if items_to_add.empty:
                st.warning(f"El kit '{selected_kit}' no se encontró en el archivo.")
                st.session_state.edited_kit_data = None
            else:
                st.session_state.edited_kit_data = items_to_add.reset_index(drop=True)

        if st.session_state.edited_kit_data is not None:
            st.write(f"Editando ítems para el kit: **{selected_kit}**")
            # Usa st.data_editor para hacer la tabla editable
            edited_df = st.data_editor(st.session_state.edited_kit_data, 
                                       column_config={
                                           "Cantidad": st.column_config.NumberColumn(
                                               "Cantidad",
                                               help="Puedes editar las cantidades de cada ítem",
                                               min_value=0
                                           )
                                       },
                                       key="data_editor_kit")

            col_kit1, col_kit2 = st.columns(2)
            with col_kit1:
                id_entrega_kit = st.text_input("ID Entrega (Kit)", key="id_entrega_kit")
            with col_kit2:
                id_recibe_kit = st.text_input("ID Recibe (Kit)", key="id_recibe_kit")

            if st.button("➕ Agregar kit al registro", key="add_kit_button"):
                nuevos_registros = []
                for _, row in edited_df.iterrows():
                    nuevo = {
                        "ID Entrega": id_entrega_kit,
                        "ID Recibe": id_recibe_kit,
                        "Orden": orden_kit,  # Usar el campo de orden digitado
                        "Tipo": "Materia prima",
                        "Item": row['Item'],
                        "Cantidad": row['Cantidad'],
                        "Unidad": row['Unidad'],
                        "Observación": observacion_kit, # Usar el campo de observación digitado
                        "Fecha": datetime.today().date()
                    }
                    nuevos_registros.append(nuevo)

                # Insertar los registros del kit en la base de datos
                for registro in nuevos_registros:
                    c.execute("INSERT INTO registros VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(registro.values()))
                conn.commit()

                load_data_from_db() # Recargar los datos desde la BD a la sesión
                st.success(f"✅ Se agregaron los ítems modificados del kit '{selected_kit}' al registro.")
                st.session_state.edited_kit_data = None # Limpiar la tabla editable
                
                st.rerun()
                
    except KeyError:
        st.error("❌ El archivo 'Kits.xlsx' no contiene una columna llamada 'Kit', 'Item', 'Cantidad' o 'Unidad'. Por favor, verifica y corrige los nombres de las columnas.")

---

## ⚙️ Administración de Registros
with st.expander("Gestionar Registros (Eliminar / Editar)"):
    st.subheader("Buscar y Modificar Registro")
    
    col_search, col_action = st.columns([3, 1])
    with col_search:
        search_orden = st.text_input("Buscar por Orden de Producción", key="search_orden_input")
    with col_action:
        st.markdown(" ") # Espacio para alinear el botón
        if st.button("🔍 Buscar"):
            st.session_state.selected_record = None
            c.execute("SELECT * FROM registros WHERE Orden = ?", (search_orden,))
            result = c.fetchone()
            if result:
                st.session_state.selected_record = {
                    "ID Entrega": result[0],
                    "ID Recibe": result[1],
                    "Orden": result[2],
                    "Tipo": result[3],
                    "Item": result[4],
                    "Cantidad": result[5],
                    "Unidad": result[6],
                    "Observación": result[7],
                    "Fecha": result[8]
                }
                st.success(f"Registro encontrado para la Orden: {search_orden}")
            else:
                st.warning(f"No se encontró ningún registro para la Orden: {search_orden}")
                st.session_state.selected_record = None
    
    if st.session_state.selected_record:
        st.write("---")
        st.subheader("Datos del Registro Seleccionado")
        
        with st.form("edit_form", clear_on_submit=False):
            # Campos para editar
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                edit_id_entrega = st.text_input("ID Entrega", value=st.session_state.selected_record["ID Entrega"])
                edit_id_recibe = st.text_input("ID Recibe", value=st.session_state.selected_record["ID Recibe"])
                edit_tipo = st.selectbox("Tipo", ["Parte fabricada", "Materia prima"], index=["Parte fabricada", "Materia prima"].index(st.session_state.selected_record["Tipo"]))
                edit_item = st.text_input("ID Item", value=st.session_state.selected_record["Item"])
            with col_edit2:
                edit_cantidad = st.number_input("Cantidad", value=st.session_state.selected_record["Cantidad"], min_value=0, step=1)
                edit_unidad = st.selectbox("Unidad", ["m", "und", "kg"], index=["m", "und", "kg"].index(st.session_state.selected_record["Unidad"]))
                edit_observacion = st.text_area("Observación", value=st.session_state.selected_record["Observación"])
                # La fecha no se edita en este ejemplo para simplificar
            
            col_btns = st.columns(2)
            with col_btns[0]:
                if st.form_submit_button("✅ Actualizar Registro"):
                    c.execute("""
                        UPDATE registros SET
                        "ID Entrega" = ?, "ID Recibe" = ?, "Tipo" = ?, "Item" = ?, "Cantidad" = ?, "Unidad" = ?, "Observación" = ?
                        WHERE "Orden" = ?
                    """, (edit_id_entrega, edit_id_recibe, edit_tipo, edit_item, edit_cantidad, edit_unidad, edit_observacion, st.session_state.selected_record["Orden"]))
                    conn.commit()
                    st.success("Registro actualizado exitosamente.")
                    load_data_from_db()
                    st.session_state.selected_record = None # Limpiar el formulario
                    st.rerun()

            with col_btns[1]:
                if st.form_submit_button("❌ Eliminar Registro"):
                    c.execute("DELETE FROM registros WHERE Orden = ?", (st.session_state.selected_record["Orden"],))
                    conn.commit()
                    st.success("Registro eliminado exitosamente.")
                    load_data_from_db()
                    st.session_state.selected_record = None # Limpiar el formulario
                    st.rerun()

---

## 📑 Registros Acumulados
st.subheader("📑 Registros acumulados")
st.dataframe(st.session_state.data, use_container_width=True)

---

## ✍️ Firma y Descargas
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

# Ya no se borran los datos, solo se generan los archivos con la info de la BD
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
        col_widths = [2.5, 2.5, 2, 2, 2, 2, 1.5, 3] 
        
        x_offsets = [margin]
        for i in range(len(dataframe.columns) - 1):
            x_offsets.append(x_offsets[-1] + col_widths[i])
        
        for i, header in enumerate(dataframe.columns):
            c.drawString(x_offsets[i]*cm, y_pos, header)
        
        # Datos de la tabla
        c.setFont("Helvetica", 8)
        y_pos -= 0.5*cm
        for _, row in dataframe.iterrows():
            if y_pos < margin + 5*cm: 
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
        if signature_image is not None:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, margin + 4.5*cm, "Firma de Recibido:")
            
            img_stream = BytesIO()
            Image.fromarray(signature_image.astype("uint8")).save(img_stream, format="PNG")
            img_stream.seek(0)
            
            c.drawImage(
                ImageReader(img_stream),
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
        )

# Cerrar la conexión cuando la aplicación termina
conn.close()