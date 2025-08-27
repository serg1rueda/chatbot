import psycopg2
import os

# ========================
# CONFIGURACIÓN DE CONEXIÓN
# ========================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "induccion")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "nacionalrey17")

def get_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

# ========================
# FUNCIONES DE APOYO
# ========================

def obtener_tema(tema):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT tipo, contenido, respuesta_correcta FROM temas WHERE LOWER(tema)=LOWER(%s)",
        (tema.lower(),)
    )
    datos = cur.fetchall()
    cur.close()
    conn.close()
    return datos

def obtener_usuario(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE usuario_id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def crear_usuario(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO usuarios (usuario_id, estado, respuestas_correctas, respuestas_incorrectas)
        VALUES (%s, 'pidiendo_nombre', 0, 0) ON CONFLICT (usuario_id) DO NOTHING""",
        (user_id,)
    )
    conn.commit()
    cur.close()
    conn.close()

def actualizar_usuario(user_id, campo, valor):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE usuarios SET {campo}=%s WHERE usuario_id=%s", (valor, user_id))
    conn.commit()
    cur.close()
    conn.close()
