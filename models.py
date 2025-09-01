# models.py
import psycopg2
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_cxKm4qaU1DNl@ep-blue-field-admkxy2t-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

def get_connection():
    return psycopg2.connect(DATABASE_URL)

def obtener_tema(tema):
    conn = get_connection()
    cur = conn.cursor()
    # ORDER BY id para mantener el orden: info luego preguntas
    cur.execute(
        "SELECT tipo, contenido, respuesta_correcta FROM temas WHERE LOWER(tema)=LOWER(%s) ORDER BY id",
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
    allowed = {"nombre","documento","fecha","estado","tema_actual","indice","contador","temas_completados","respuestas_correctas","respuestas_incorrectas"}
    if campo not in allowed:
        raise ValueError("Campo no permitido para actualizar")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE usuarios SET {campo}=%s WHERE usuario_id=%s", (valor, user_id))
    conn.commit()
    cur.close()
    conn.close()
