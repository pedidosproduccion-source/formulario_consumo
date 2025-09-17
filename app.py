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


# Cargar el archivo de kits automáticamente
try:
    kit_data = pd.read_excel("Kits.xlsx")
    st.success("Archivo de kits cargado correctamente.")
except FileNotFoundError:
    st.error("Archivo 'Kits.xlsx' no encontrado en la misma carpeta.")
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


# Registro Manual de Ítems
with st.form("form_registro", clear_on_submit=False): 
    st.subheader("Registro Manual")
    col1, col2 = st.columns(2)
    with col1:
        id_entrega = st.text_input("ID Entrega")
        id_recibe = st.text_input("ID Recibe")
        orden = st.text_input("Orden de Producción")
    with col2:
        tipo = st.selectbox("Tipo", ["Parte fabricada", "Materia prima"], index=1)
        item = st.text_input("ID Item", key="item_input")
        
        # Normalizar el valor ingresado por el usuario a string y mayúsculas
        item_normalizado = item.strip().upper()
        
        # Buscar la unidad y la descripción en tiempo real
        unidad = ""
        descripcion = "" # Nuevo campo para la descripción
        if siesa_items is not None and item_normalizado:
            # Filtrar el DataFrame donde el 'ID Item' coincida con el valor normalizado
            matching_row = siesa_items[siesa_items['ID Item'] == item_normalizado]
            if not matching_row.empty:
                # Si se encuentra una coincidencia, obtener la unidad y la descripción
                unidad = matching_row['Unidad'].iloc[0]
                descripcion = matching_row['Descripción Item'].iloc[0]
            elif item_normalizado:
                st.warning(f"El ID de ítem '{item}' no se encontró en el listado de Siesa. La unidad y la descripción no se llenarán automáticamente.")
        
        st.text_input("Unidad", value=unidad, disabled=True)
        st.text_area("Descripción del Ítem", value=descripcion, disabled=True) # Nuevo campo de texto para la descripción
        cantidad = st.number_input("Cantidad", min_value=0, step=1)
    
    col3, col4 = st.columns(2)
    with col3:
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
        
        if not id_entrega or not id_recibe or not orden or not item or cantidad is None or not unidad:
            st.warning("Por favor, complete todos los campos requeridos (ID Entrega, ID Recibe, Orden, ID Item, Cantidad y Unidad).")
        else:
            c.execute("INSERT INTO registros (\"ID Entrega\", \"ID Recibe\", \"Orden\", \"Tipo\", \"Item\", \"Cantidad\", \"Unidad\", \"Observación\", \"Fecha\") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", tuple(nuevo.values()))
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
                
    except KeyError:
        st.error("El archivo 'Kits.xlsx' no contiene una columna llamada 'Kit', 'Item', 'Cantidad' o 'Unidad'. Por favor, verifica y corrige los nombres de las columnas.")

# --- Sección de Registros Acumulados actualizada para manejar el filtrado ---
st.subheader("Registros acumulados")

# Lógica para el nuevo indicador de total de registros
try:
    total_registros_query = c.execute("SELECT COUNT(*) FROM registros").fetchone()[0]
    st.metric(label="Total de Registros", value=total_registros_query)
except Exception as e:
    st.error(f"No se pudo obtener el total de registros: {e}")

# Ahora cargamos todos los datos para poder filtrar correctamente
try:
    df_all_data = pd.read_sql_query("SELECT * FROM registros", conn)
    if not df_all_data.empty:
        df_all_data["Fecha"] = pd.to_datetime(df_all_data["Fecha"])
    else:
        st.write("No hay registros en la base de datos.")
except Exception as e:
    st.error(f"Error al cargar todos los datos de la base de datos: {e}")
    df_all_data = pd.DataFrame()

# Solo mostramos el filtro si hay datos
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
    
    # Aplicar el filtro directamente sobre los datos cargados
    df_filtered = df_all_data[
        (df_all_data['Fecha'] >= start_date) &
        (df_all_data['Fecha'] <= end_date)
    ]
    
    st.dataframe(df_filtered, use_container_width=True)
# --- Fin de la sección de Registros Acumulados ---


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

# Ahora la descarga de Excel y PDF usa todos los datos filtrados
if not df_all_data.empty:
    fecha_hoy = datetime.today().strftime("%Y-%m-%d")

    # Descargar en Excel
    excel_buffer = BytesIO()
    df_filtered.to_excel(excel_buffer, index=False, engine="openpyxl")
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
        col_widths = [1, 2.5, 2.5, 2, 2, 2, 2, 1.5, 3]
        
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
        pdf_buffer = generate_pdf(df_filtered, firma.image_data)
        st.download_button(
            label="Descargar PDF con firma",
            data=pdf_buffer,
            file_name=f"informe_consumo_{fecha_hoy}.pdf",
            mime="application/pdf",
        )

# Cerrar la conexión cuando la aplicación termina
conn.close()