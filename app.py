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

# --- Llama al script de persistencia al inicio ---
import persist
persist.restore_db()

# Configuración inicial y título de la aplicación
st.set_page_config(layout="wide")
st.title("Registro de consumo de materia prima")

# --- CONEXIÓN Y CONFIGURACIÓN DE LA BASE DE DATOS SQLite ---
conn = sqlite3.connect("registros.db")
c = conn.cursor()

# Crear la tabla con una columna de ID única
c.execute('''
    CREATE TABLE IF NOT EXISTS registros (
        "ID" INTEGER PRIMARY KEY AUTOINCREMENT,
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
        # Cargar solo los últimos 50 registros, ordenados por ID descendente
        df = pd.read_sql_query("SELECT * FROM registros ORDER BY ID DESC LIMIT 50", conn)
        
        # Invertir el orden para que los más recientes aparezcan al final de la tabla en la interfaz
        df = df.iloc[::-1]

        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame()
        if not df.empty:
            df["Fecha"] = pd.to_datetime(df["Fecha"])
        st.session_state.data = df
    except Exception as e:
        st.error(f"Error al cargar datos de la base de datos: {e}")
        st.session_state.data = pd.DataFrame()

# Inicializar las variables de estado al inicio de la aplicación
if "data" not in st.session_state:
    load_data_from_db()
if "edited_kit_data" not in st.session_state:
    st.session_state.edited_kit_data = None
if "show_all_records" not in st.session_state:
    st.session_state.show_all_records = False

# Cargar el archivo de kits automáticamente
try:
    kit_data = pd.read_excel("Kits.xlsx")
    st.success("Archivo de kits cargado correctamente.")

    # Verificación de columnas
    required_columns = ['Kit', 'Item', 'Cantidad', 'Unidad']
    if not all(col in kit_data.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in kit_data.columns]
        st.error(f"El archivo 'Kits.xlsx' no contiene las siguientes columnas requeridas: {', '.join(missing_cols)}")
        kit_data = None
    else:
        st.write("Columnas de kit encontradas y listas para usar.")
except FileNotFoundError:
    st.error("Archivo 'Kits.xlsx' no encontrado en la misma carpeta.")
    kit_data = None
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo 'Kits.xlsx': {e}")
    kit_data = None

# Cargar el archivo de Siesa para buscar la unidad y la descripción
try:
    siesa_items = pd.read_excel("listado de items Siesa.xlsx")
    # Verificar que las columnas existan antes de procesar
    if 'ID Item' in siesa_items.columns and 'Unidad' in siesa_items.columns and 'Descripción Item' in siesa_items.columns:
        # Limpiar ambas columnas de texto (espacios y mayúsculas) y convertirlas a string
        siesa_items['ID Item'] = siesa_items['ID Item'].astype(str).str.strip().str.upper()
        siesa_items['Unidad'] = siesa_items['Unidad'].astype(str).str.strip().str.upper()
        siesa_items['Descripción Item'] = siesa_items['Descripción Item'].astype(str).str.strip()
        st.success("Archivo 'listado de items Siesa' cargado correctamente.")
    else:
        st.error("El archivo 'listado de items Siesa.xlsx' no contiene las columnas requeridas ('ID Item', 'Unidad' y/o 'Descripción Item').")
        siesa_items = None
except FileNotFoundError:
    st.error("Archivo 'listado de items Siesa.xlsx' no encontrado. La unidad y la descripción no se llenarán automáticamente.")
    siesa_items = None
except Exception as e:
    st.error(f"Ocurrió un error al procesar el archivo 'listado de items Siesa.xlsx': {e}")
    siesa_items = None


# --- Registro Manual de Ítems (ORGANIZADO) ---
with st.form("form_registro", clear_on_submit=False): 
    st.subheader("Registro Manual")

    # Sección 1: Datos de la Orden
    st.markdown("**Datos de la Orden**")
    col1, col2, col3 = st.columns(3)
    with col1:
        id_entrega = st.text_input("ID Entrega")
    with col2:
        id_recibe = st.text_input("ID Recibe")
    with col3:
        orden = st.text_input("Orden de Producción")

    # Sección 2: Información del Ítem
    st.markdown("**Información del Ítem**")
    col4, col5 = st.columns(2)
    with col4:
        tipo = st.selectbox("Tipo", ["Parte fabricada", "Materia prima"], index=1)
        item = st.text_input("ID Item", key="item_input")
        cantidad = st.number_input("Cantidad", min_value=0, step=1)
    with col5:
        # Lógica para buscar unidad y descripción
        item_normalizado = item.strip().upper()
        unidad = ""
        descripcion = ""
        if siesa_items is not None and item_normalizado:
            matching_row = siesa_items[siesa_items['ID Item'] == item_normalizado]
            if not matching_row.empty:
                unidad = matching_row['Unidad'].iloc[0]
                descripcion = matching_row['Descripción Item'].iloc[0]
            elif item_normalizado:
                st.warning(f"El ID de ítem '{item}' no se encontró. La unidad y la descripción no se llenarán.")
        
        st.text_input("Unidad", value=unidad, disabled=True)
        st.text_area("Descripción del Ítem", value=descripcion, disabled=True)
    
    # Sección 3: Observaciones y Fecha
    st.markdown("**Detalles del Registro**")
    col6, col7 = st.columns(2)
    with col6:
        fecha = st.date_input("Fecha de diligenciamiento", datetime.today())
    with col7:
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
        
        if not id_entrega or not id_recibe or not orden or not item or cantidad is None or not unidad:
            st.warning("Por favor, complete todos los campos requeridos (ID Entrega, ID Recibe, Orden, ID Item, Cantidad y Unidad).")
        else:
            c.execute("INSERT INTO registros (\"ID Entrega\", \"ID Recibe\", \"Orden\", \"Tipo\", \"Item\", \"Cantidad\", \"Unidad\", \"Observación\", \"Fecha\") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(nuevo.values()))
            conn.commit()
            
            load_data_from_db()
            st.success("Registro agregado correctamente")
            st.rerun()

# --- Registro por Kit (ORGANIZADO) ---
if kit_data is not None:
    st.subheader("Registro por Kit")
    
    # Sección 1: Selección de Kit y Datos de la Orden
    col_kit_info1, col_kit_info2, col_kit_info3 = st.columns(3)
    with col_kit_info1:
        selected_kit = st.selectbox(
            "Selecciona o digita un kit", 
            options=kit_data['Kit'].unique(), 
            key="selectbox_kit"
        )
    with col_kit_info2:
        orden_kit = st.text_input("Orden de Producción (Kit)")
    with col_kit_info3:
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

        col_kit_submit1, col_kit_submit2 = st.columns(2)
        with col_kit_submit1:
            id_entrega_kit = st.text_input("ID Entrega (Kit)", key="id_entrega_kit")
        with col_kit_submit2:
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
                    "Cantidad": int(row['Cantidad']),
                    "Unidad": row['Unidad'],
                    "Observación": observacion_kit,
                    "Fecha": datetime.today().date()
                }
                nuevos_registros.append(nuevo)

            for registro in nuevos_registros:
                c.execute("INSERT INTO registros (\"ID Entrega\", \"ID Recibe\", \"Orden\", \"Tipo\", \"Item\", \"Cantidad\", \"Unidad\", \"Observación\", \"Fecha\") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(registro.values()))
            conn.commit()

            load_data_from_db()
            st.success(f"Se agregaron los ítems modificados del kit '{selected_kit}' al registro.")
            st.session_state.edited_kit_data = None
            
            st.rerun()

# --- Registros Acumulados con filtro de fecha ---
st.subheader("Registros acumulados")

# Lógica para el nuevo indicador de total de registros
try:
    total_registros_query = c.execute("SELECT COUNT(*) FROM registros").fetchone()[0]
    st.metric(label="Total de Registros", value=total_registros_query)
except Exception as e:
    st.error(f"No se pudo obtener el total de registros: {e}")

# --- Nuevo botón para ver todos los registros ---
if st.button("Ver historial completo"):
    # Cambia el estado para que se carguen todos los registros
    st.session_state.show_all_records = True

# --- Lógica para cargar y mostrar los datos ---
if st.session_state.show_all_records:
    # Cargar todos los datos si el botón fue presionado
    try:
        df_all_data = pd.read_sql_query("SELECT * FROM registros", conn)
        if not df_all_data.empty:
            df_all_data["Fecha"] = pd.to_datetime(df_all_data["Fecha"])
        else:
            st.write("No hay registros en la base de datos.")
    except Exception as e:
        st.error(f"Error al cargar todos los datos de la base de datos: {e}")
        df_all_data = pd.DataFrame()

    if not df_all_data.empty:
        min_date = df_all_data['Fecha'].min().date()
        max_date = df_all_data['Fecha'].max().date()
        
        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            start_date = st.date_input(
                "Fecha de inicio", 
                min_value=min_date, 
                max_value=max_date, 
                value=min_date
            )
        with col_filter2:
            end_date = st.date_input(
                "Fecha de fin", 
                min_value=min_date, 
                max_value=max_date, 
                value=max_date
            )
            
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)
        
        df_filtered = df_all_data[
            (df_all_data['Fecha'] >= start_date) &
            (df_all_data['Fecha'] <= end_date)
        ]
        
        st.dataframe(df_filtered, use_container_width=True)
else:
    # Por defecto, mostrar solo los últimos 50 registros
    if not st.session_state.data.empty:
        st.dataframe(st.session_state.data, use_container_width=True)
    else:
        st.write("No hay registros en la base de datos.")

# --- Firma y Descargas ---
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

# Ahora la descarga de Excel y PDF usa todos los datos filtrados
if 'data' in st.session_state and not st.session_state.data.empty:
    fecha_hoy = datetime.today().strftime("%Y-%m-%d")

    # Si se han filtrado datos, usamos df_filtered, de lo contrario usamos los 50 últimos
    df_to_export = df_filtered if st.session_state.show_all_records and 'df_filtered' in locals() else st.session_state.data
    
    # Descargar en Excel
    excel_buffer = BytesIO()
    df_to_export.to_excel(excel_buffer, index=False, engine="openpyxl")
    excel_buffer.seek(0)
    
    st.download_button(
        label="Descargar Excel",
        data=excel_buffer,
        file_name=f"registros_consumo_{fecha_hoy}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",)
 
    # Descargar en PDF
    def generate_pdf(dataframe, signature_image):
        buffer_pdf = BytesIO()
        c = canvas.Canvas(buffer_pdf, pagesize=A4)
        width, height = A4
        margin = 2 * cm
        
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin, height - margin, "Informe de Consumo de Materia Prima")
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, height - margin - 0.7*cm, f"Fecha: {datetime.today().strftime('%Y-%m-%d')}")
        
        # Tamaño de fuente para encabezados
        c.setFont("Helvetica-Bold", 8)
        y_pos = height - 4 * cm

        # Nombres de las columnas del DataFrame
        columns = dataframe.columns.tolist()
        num_cols = len(columns)
        total_table_width = width - 2 * margin
        
        # --- Lógica de cálculo dinámico y proporcional de ancho de columnas ---
        # Anchos base por defecto para que la tabla sea legible
        base_widths = [1.5, 2.5, 2.5, 2.0, 2.0, 2.5, 1.5, 2.0, 2.5, 3.0]
        
        # Si el número de columnas cambia, distribuimos el ancho de forma equitativa
        if num_cols != len(base_widths):
            col_width = total_table_width / num_cols
            col_widths_cm = [col_width / cm] * num_cols
        else:
            col_widths_cm = base_widths
            total_base_width = sum(base_widths) * cm
            if total_base_width > total_table_width:
                # Si los anchos base son demasiado grandes, los escalamos
                scale_factor = total_table_width / total_base_width
                col_widths_cm = [w * scale_factor for w in base_widths]
        
        # Calcular los offsets (posiciones x) de las columnas
        x_offsets = [margin]
        for i in range(num_cols - 1):
            x_offsets.append(x_offsets[-1] + col_widths_cm[i] * cm)
        
        # Dibuja los encabezados
        for i, header in enumerate(columns):
            c.drawString(x_offsets[i], y_pos, str(header))
        
        # Tamaño de fuente para los datos (más pequeño para mejor legibilidad)
        c.setFont("Helvetica", 7)
        y_pos -= 0.5 * cm
        
        # Dibuja los datos de cada fila
        for _, row in dataframe.iterrows():
            if y_pos < margin + 5 * cm: 
                c.showPage()
                y_pos = height - margin
                c.setFont("Helvetica-Bold", 8)
                for i, header in enumerate(columns):
                    c.drawString(x_offsets[i], y_pos, str(header))
                c.setFont("Helvetica", 7)
                y_pos -= 0.5 * cm
            
            for i, val in enumerate(row.values):
                display_val = "" if pd.isna(val) else str(val)
                # Verifica que el valor no exceda el ancho de la columna
                max_width = col_widths_cm[i] * cm
                text_width = c.stringWidth(display_val, "Helvetica", 7)
                
                if text_width > max_width:
                    # Trunca el texto si es demasiado largo
                    truncated_text = c.set_font_and_get_string_width(display_val, "Helvetica", 7, max_width - 0.5*cm)
                    display_val = truncated_text + "..."
                
                c.drawString(x_offsets[i], y_pos, display_val)
            y_pos -= 0.5 * cm
            
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
        pdf_buffer = generate_pdf(df_to_export, firma.image_data)
        st.download_button(
            label="Descargar PDF con firma",
            data=pdf_buffer,
            file_name=f"informe_consumo_{fecha_hoy}.pdf",
            mime="application/pdf",
        )

# Cerrar la conexión cuando la aplicación termina
conn.close()