from flask import Flask, request, jsonify
import sqlite3
from flask_cors import CORS
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# Ruta de la base de datos
DB_PATH = os.environ.get("DB_PATH") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "induccion.db")

# ============================
# FUNCIONES DE APOYO
# ============================

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                documento TEXT,
                fecha TEXT,
                tema_actual TEXT,
                correctas INTEGER DEFAULT 0,
                incorrectas INTEGER DEFAULT 0,
                nota REAL DEFAULT 0
            )
        """)
        conn.commit()

def obtener_usuario():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM usuarios ORDER BY id DESC LIMIT 1")
        return cursor.fetchone()

def crear_usuario(nombre, documento, fecha):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO usuarios (nombre, documento, fecha) VALUES (?, ?, ?)
        """, (nombre, documento, fecha))
        conn.commit()

def actualizar_usuario(campo, valor):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE usuarios SET {campo} = ? WHERE id = (SELECT id FROM usuarios ORDER BY id DESC LIMIT 1)
        """, (valor,))
        conn.commit()

def obtener_tema():
    user = obtener_usuario()
    if user:
        return user[4]  # campo tema_actual
    return None

# ============================
# TEMAS Y QUIZ
# ============================

temas = {
    "riesgos": {
        "contenido": "📌 Riesgos en el trabajo:\n1. Físicos\n2. Químicos\n3. Biológicos\n4. Ergonómicos\n5. Psicosociales",
        "quiz": {
            "pregunta": "❓ ¿Cuál de estos es un riesgo ergonómico?\n\na) Posturas inadecuadas\nb) Ruidos fuertes\nc) Productos químicos",
            "respuesta": "a"
        }
    },
    "convivencia": {
        "contenido": "🤝 Convivencia laboral:\n- Respeto\n- Comunicación asertiva\n- Trabajo en equipo",
        "quiz": {
            "pregunta": "❓ ¿Qué valor hace parte de la convivencia laboral?\n\na) Gritos\nb) Respeto\nc) Individualismo",
            "respuesta": "b"
        }
    }
}

# ============================
# API PRINCIPAL
# ============================

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    mensaje = data.get("mensaje", "").strip().lower()
    user = obtener_usuario()

    # ============================
    # REGISTRO DE USUARIO
    # ============================
    if not user:
        return jsonify({"respuesta": "👋 ¡Hola! Bienvenido a la inducción. Por favor dime tu *nombre completo*."})

    if not user[1]:  # Nombre
        actualizar_usuario("nombre", mensaje)
        return jsonify({"respuesta": f"✅ Gracias {mensaje}. Ahora dime tu *documento de identidad*."})

    if not user[2]:  # Documento
        actualizar_usuario("documento", mensaje)
        return jsonify({"respuesta": "📅 Perfecto. Ingresa la *fecha de esta conversación* (AAAA-MM-DD)."})

    if not user[3]:  # Fecha
        try:
            datetime.strptime(mensaje, "%Y-%m-%d")
            actualizar_usuario("fecha", mensaje)
            return jsonify({"respuesta": f"✅ Registro completado. 👤 Nombre: {user[1]} 🆔 Documento: {user[2]} 📅 Fecha: {mensaje}\n\nEscribe 'tema' para ver los disponibles."})
        except ValueError:
            return jsonify({"respuesta": "⚠️ Formato inválido. Usa AAAA-MM-DD."})

    tema_actual = obtener_tema()

    # ============================
    # LISTAR TEMAS
    # ============================
    if mensaje == "tema":
        if tema_actual:  # ya está en un tema
            return jsonify({"respuesta": "⚠️ Debes terminar el tema actual antes de elegir otro."})

        lista = "\n".join([f"- {t}" for t in temas.keys()])
        return jsonify({"respuesta": f"📚 Temas disponibles:\n{lista}\n\nEscribe el nombre del tema para iniciar."})

    # ============================
    # SELECCIONAR TEMA
    # ============================
    if mensaje in temas.keys():
        if tema_actual:
            return jsonify({"respuesta": "⚠️ Ya estás en un tema. Debes terminarlo antes de cambiar."})

        actualizar_usuario("tema_actual", mensaje)
        return jsonify({"respuesta": f"{temas[mensaje]['contenido']}\n\n{temas[mensaje]['quiz']['pregunta']}"})

    # ============================
    # RESPUESTA A QUIZ
    # ============================
    if tema_actual:
        quiz = temas[tema_actual]["quiz"]
        if mensaje == quiz["respuesta"]:
            actualizar_usuario("correctas", user[5] + 1)
            actualizar_usuario("tema_actual", None)
            return jsonify({"respuesta": "✅ ¡Correcto! Has terminado este tema.\n\nEscribe 'tema' para continuar con otro."})
        else:
            actualizar_usuario("incorrectas", user[6] + 1)
            return jsonify({"respuesta": "❌ Incorrecto. Intenta de nuevo."})

    return jsonify({"respuesta": "🤔 No entendí. Escribe 'tema' para comenzar."})

# ============================
# INICIO
# ============================

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
