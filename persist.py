import os
import shutil

# La carpeta que Streamlit usa para su caché (donde guarda los datos de la app)
data_dir = os.path.join(os.getcwd(), '.streamlit/state')

# Archivo de la base de datos
db_path = os.path.join(os.getcwd(), 'registros.db')

# Aseguramos que la carpeta de datos exista
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

def backup_db():
    """Copia la base de datos a un lugar seguro para su persistencia."""
    if os.path.exists(db_path):
        shutil.copyfile(db_path, os.path.join(data_dir, 'registros.db'))
        print("Base de datos copiada para persistencia.")

def restore_db():
    """Restaura la base de datos desde la copia persistente."""
    persistent_db_path = os.path.join(data_dir, 'registros.db')
    if os.path.exists(persistent_db_path):
        shutil.copyfile(persistent_db_path, db_path)
        print("Base de datos restaurada desde la copia persistente.")
    else:
        print("No se encontró una copia persistente. Se usará un archivo nuevo.")

if __name__ == "__main__":
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "backup":
        backup_db()
    else:
        restore_db()