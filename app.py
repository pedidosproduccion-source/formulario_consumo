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