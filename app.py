import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import sqlite3
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Configuración inicial y título de la aplicación
st.set_page_config(layout="wide")
st.title("Registro de consumo de materia prima")

# --- CONEXIÓN Y CONFIGURACIÓN DE LA BASE DE DATOS SQLite ---
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
    try:
        df = pd.read_sql_query("SELECT * FROM registros", conn)
        if not df.empty:
            df["Fecha"] = pd.to_datetime(df["Fecha"])
        st.session_state.data = df
    except Exception as e:
        st.error(f"Error al cargar datos de la base de datos: {e}")
        st.session_state.data = pd.DataFrame() # Asegura que la variable sea siempre un DataFrame

# Inicializar las variables de estado al inicio de la aplicación
if "data" not in st.session_state:
    load_data_from_db()
if "edited_kit_data" not in st.session_state:
    st.session_state.edited_kit_data = None
if "selected_record" not in st.session_state:
    st.session_state.selected_record = None
if "found_records" not in st.session_state:
    st.session_state.found_records = pd.DataFrame()


# Cargar el archivo de kits automáticamente
try:
    kit_data = pd.read_excel("Kits.xlsx")
    st.success("Archivo de kits cargado correctamente.")
except FileNotFoundError:
    st.error("Archivo 'Kits.xlsx' no encontrado en la misma carpeta.")
    kit_data = None


# Registro Manual de Ítems
# Formulario para agregar un registro
with st.form("form_registro", clear_on_submit=True):
    st.subheader("Registro Manual")
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

    submitted = st.form_submit_button("Agregar registro")

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
        
        c.execute("INSERT INTO registros VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(nuevo.values()))
        conn.commit()
        
        load_data_from_db()
        st.success("Registro agregado correctamente")
        st.rerun()

# Registro por Kit
if kit_data is not None:
    st.subheader("Registro por Kit")
    
    try:
        kit_data['Kit'] = kit_data['Kit'].str.strip()
        kit_options = kit_data['Kit'].unique()
        
        selected_kit = st.selectbox(
            "Selecciona o digita un kit", 
            options=kit_options, 
            key="selectbox_kit"
        )
        
        col_kit_info1, col_kit_info2 = st.columns(2)
        with col_kit_info1:
            orden_kit = st.text_input("Orden de Producción (Kit)")
        with col_kit_info2:
            observacion_kit = st.text_area("Observación (Kit)")

        if st.button("Ver y editar kit"):
            items_to_add = kit_data[kit_data['Kit'] == selected_kit].copy()
            if items_to_add.empty:
                st.warning(f"El kit '{selected_kit}' no se encontró en el archivo.")
                st.session_state.edited_kit_data = None
            else:
                st.session_state.edited_kit_data = items_to_add.reset_index(drop=True)

        if st.session_state.edited_kit_data is not None:
            st.write(f"Editando ítems para el kit: **{selected_kit}**")
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

            if st.button("Agregar kit al registro", key="add_kit_button"):
                nuevos_registros = []
                for _, row in edited_df.iterrows():
                    nuevo = {
                        "ID Entrega": id_entrega_kit,
                        "ID Recibe": id_recibe_kit,
                        "Orden": orden_kit,
                        "Tipo": "Materia prima",
                        "Item": row['Item'],
                        "Cantidad": row['Cantidad'],
                        "Unidad": row['Unidad'],
                        "Observación": observacion_kit,
                        "Fecha": datetime.today().date()
                    }
                    nuevos_registros.append(nuevo)

                for registro in nuevos_registros:
                    c.execute("INSERT INTO registros VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(registro.values()))
                conn.commit()

                load_data_from_db()
                st.success(f"Se agregaron los ítems modificados del kit '{selected_kit}' al registro.")
                st.session_state.edited_kit_data = None
                
                st.rerun()
                
    except KeyError:
        st.error("El archivo 'Kits.xlsx' no contiene una columna llamada 'Kit', 'Item', 'Cantidad' o 'Unidad'. Por favor, verifica y corrige los nombres de las columnas.")


# Administración de Registros
with st.expander("Gestionar Registros (Eliminar / Editar)"):
    st.subheader("Buscar y Modificar Registro")
    
    col_search1, col_search2, col_action = st.columns([3, 3, 1])
    with col_search1:
        search_orden = st.text_input("Buscar por Orden de Producción", key="search_orden_input")
    with col_search2:
        search_item = st.text_input("Buscar por ID Item", key="search_item_input")
    with col_action:
        st.markdown(" ")
        if st.button("Buscar", key="search_button"):
            st.session_state.found_records = pd.DataFrame()
            st.session_state.selected_record = None

            query_parts = []
            params = []
            if search_orden:
                query_parts.append('"Orden" = ?')
                params.append(search_orden)
            if search_item:
                query_parts.append('"Item" = ?')
                params.append(search_item)
            
            if query_parts:
                query_string = "SELECT * FROM registros WHERE " + " AND ".join(query_parts)
                st.session_state.found_records = pd.read_sql_query(query_string, conn, params=params)
                
                if not st.session_state.found_records.empty:
                    st.success(f"Se encontraron {len(st.session_state.found_records)} registros.")
                    st.session_state.found_records['select_record'] = False
                else:
                    st.warning("No se encontraron registros con los criterios de búsqueda.")
            else:
                st.warning("Por favor, introduce una Orden de Producción o un ID de Item para buscar.")

    if not st.session_state.found_records.empty:
        st.write("Registros encontrados (puedes seleccionarlos para editar):")
        
        edited_df = st.data_editor(
            st.session_state.found_records,
            hide_index=True,
            column_config={
                "select_record": st.column_config.CheckboxColumn(
                    "Seleccionar",
                    help="Selecciona el registro que deseas editar o eliminar.",
                    default=False,
                )
            },
            num_rows="dynamic",
            use_container_width=True,
            key="found_records_editor"
        )
        
        selected_rows = edited_df[edited_df.select_record]
        
        if not selected_rows.empty:
            st.session_state.selected_record = selected_rows.iloc[0].to_dict()
            st.session_state.selected_record_original_orden = st.session_state.selected_record["Orden"]
            st.info(f"Registro seleccionado para editar: Orden {st.session_state.selected_record_original_orden}")
        else:
            st.session_state.selected_record = None
    
    if st.session_state.selected_record:
        st.write("---")
        st.subheader("Datos del Registro Seleccionado")
        
        with st.form("edit_form", clear_on_submit=False):
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                edit_id_entrega = st.text_input("ID Entrega", value=st.session_state.selected_record["ID Entrega"])
                edit_id_recibe = st.text_input("ID Recibe", value=st.session_state.selected_record["ID Recibe"])
                edit_orden = st.text_input("Orden de Producción", value=st.session_state.selected_record["Orden"])
                
                try:
                    tipo_index = ["Parte fabricada", "Materia prima"].index(st.session_state.selected_record["Tipo"])
                except ValueError:
                    tipo_index = 1
                edit_tipo = st.selectbox("Tipo", ["Parte fabricada", "Materia prima"], index=tipo_index)
                
            with col_edit2:
                edit_item = st.text_input("ID Item", value=st.session_state.selected_record["Item"])
                edit_cantidad = st.number_input("Cantidad", value=st.session_state.selected_record["Cantidad"], min_value=0, step=1)
                
                try:
                    unidad_index = ["m", "und", "kg"].index(st.session_state.selected_record["Unidad"])
                except ValueError:
                    unidad_index = 1
                edit_unidad = st.selectbox("Unidad", ["m", "und", "kg"], index=unidad_index)
                
                edit_observacion = st.text_area("Observación", value=st.session_state.selected_record["Observación"])
            
            col_btns = st.columns(2)
            with col_btns[0]:
                if st.form_submit_button("Actualizar Registro"):
                    c.execute("""
                        UPDATE registros SET
                        "ID Entrega" = ?, "ID Recibe" = ?, "Orden" = ?, "Tipo" = ?, "Item" = ?, "Cantidad" = ?, "Unidad" = ?, "Observación" = ?
                        WHERE "Orden" = ? AND "Item" = ?
                    """, (edit_id_entrega, edit_id_recibe, edit_orden, edit_tipo, edit_item, edit_cantidad, edit_unidad, edit_observacion, st.session_state.selected_record_original_orden, st.session_state.selected_record["Item"]))
                    conn.commit()
                    st.success("Registro actualizado exitosamente.")
                    load_data_from_db()
                    st.session_state.selected_record = None
                    st.session_state.found_records = pd.DataFrame()
                    st.rerun()

            with col_btns[1]:
                if st.form_submit_button("Eliminar Registro"):
                    if st.session_state.selected_record:
                        try:
                            c.execute("DELETE FROM registros WHERE Orden = ? AND Item = ?",
                                      (st.session_state.selected_record_original_orden, st.session_state.selected_record["Item"]))
                            conn.commit()
                            st.success("Registro eliminado exitosamente.")
                            load_data_from_db()
                            st.session_state.selected_record = None
                            st.session_state.found_records = pd.DataFrame()
                            st.rerun()
                        except sqlite3.Error as e:
                            st.error(f"Error al eliminar el registro: {e}")
                    else:
                        st.warning("Por favor, selecciona un registro para eliminar.")

# Registros Acumulados
st.subheader("Registros acumulados")
st.dataframe(st.session_state.data, use_container_width=True, filter=True)

# Firma y Descargas
st.subheader("Firma de recibido")
firma = st_canvas(
    fill_color="rgba(255, 255, 255, 0)",
    stroke_width=2,
    stroke_color="black",
    background_color="white",
    height=150,
    drawing_mode="freedraw",
    key="canvas"
)

if not st.session_state.data.empty:
    fecha_hoy = datetime.today().strftime("%Y-%m-%d")

    # Descargar en Excel
    excel_buffer = BytesIO()
    st.session_state.data.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)
    
    st.download_button(
        label="Descargar Excel",
        data=excel_buffer,
        file_name=f"registros_consumo_{fecha_hoy}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Descargar en PDF
    def generate_pdf(dataframe, signature_image):
        buffer_pdf = BytesIO()
        c = canvas.Canvas(buffer_pdf, pagesize=A4)
        width, height = A4
        margin = 2*cm
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, height - margin, "Informe de Consumo de Materia Prima")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - margin - 0.7*cm, f"Fecha: {datetime.today().strftime('%Y-%m-%d')}")
        
        c.setFont("Helvetica-Bold", 9)
        y_pos = height - 4*cm
        col_widths = [2.5, 2.5, 2, 2, 2, 2, 1.5, 3] 
        
        x_offsets = [margin]
        for i in range(len(dataframe.columns) - 1):
            x_offsets.append(x_offsets[-1] + col_widths[i])
        
        for i, header in enumerate(dataframe.columns):
            c.drawString(x_offsets[i]*cm, y_pos, header)
        
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
            label="Descargar PDF con firma",
            data=pdf_buffer,
            file_name=f"informe_consumo_{fecha_hoy}.pdf",
            mime="application/pdf",
        )

# Cerrar la conexión cuando la aplicación termina
conn.close()