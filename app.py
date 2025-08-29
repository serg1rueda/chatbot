from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========================
# Sesiones de usuarios
# ========================
sessions = {}

# ========================
# Temas disponibles
# ========================
temas = {
    "riesgos": {
        "descripcion": "💡 Riesgos y peligros: análisis de trabajo seguro, uso adecuados de EPP, ejercicios de estiramiento, reporte de actos y condiciones inseguras, y reportes de estado de salud.",
        "preguntas": [
            {
                "pregunta": "¿Qué debe hacer un trabajador para prevenir riesgos?",
                "opciones": [
                    "a) No reportar actos inseguros",
                    "b) Hacer ejercicios de estiramiento y usar EPP",
                    "c) Ignorar el estado de salud",
                    "d) Ninguna de las anteriores"
                ],
                "respuesta": "b"
            }
        ]
    }
}

# ========================
# Rutas del chatbot
# ========================
@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_id = str(data.get("user_id"))
    user_message = data.get("message", "").strip()

    if not user_id:
        return jsonify({"response": "❌ Error: falta el user_id"}), 400

    # Crear sesión si no existe
    if user_id not in sessions:
        sessions[user_id] = {
            "estado": "nombre",
            "nombre": "",
            "documento": "",
            "fecha": "",
            "tema": None,
            "pregunta_actual": 0,
            "mostro_descripcion": False
        }
        return jsonify({"response": "👋 ¡Hola! Bienvenido a la inducción. Por favor dime tu *nombre completo*."})

    session = sessions[user_id]

    # ========================
    # Flujo de registro
    # ========================
    if session["estado"] == "nombre":
        session["nombre"] = user_message
        session["estado"] = "documento"
        return jsonify({"response": f"✅ Gracias {session['nombre']}. Ahora dime tu *número de documento*."})

    elif session["estado"] == "documento":
        session["documento"] = user_message
        session["estado"] = "fecha"
        return jsonify({"response": "📅 Perfecto. Ingresa la *fecha de esta conversación* (AAAA-MM-DD)."})

    elif session["estado"] == "fecha":
        session["fecha"] = user_message
        session["estado"] = "tema"
        return jsonify({
            "response": f"✅ Registro completado. 👤 Nombre: {session['nombre']} 🆔 Documento: {session['documento']} 📅 Fecha: {session['fecha']}\n✍️ Escribe 'tema' para ver los temas disponibles."
        })

    # ========================
    # Flujo de selección de temas
    # ========================
    elif session["estado"] == "tema":
        if user_message.lower() == "tema":
            lista_temas = "📌 Temas disponibles:\n" + "\n".join([f"- {t}" for t in temas.keys()])
            return jsonify({"response": lista_temas})

        elif user_message.lower() in temas:
            session["tema"] = user_message.lower()
            session["estado"] = "preguntas"
            session["pregunta_actual"] = 0
            session["mostro_descripcion"] = False

            descripcion = temas[session["tema"]]["descripcion"]
            return jsonify({"response": f"📌 {session['tema'].capitalize()}\n{descripcion}\n\n👉 Escribe 'continuar' para empezar las preguntas."})

        else:
            return jsonify({"response": "❌ Tema no válido. Escribe 'tema' para ver los disponibles."})

    # ========================
    # Flujo de preguntas
    # ========================
    elif session["estado"] == "preguntas":
        tema = temas.get(session["tema"])

        # Si aún no mostró la descripción, espera a "continuar"
        if not session["mostro_descripcion"]:
            if user_message.lower() == "continuar":
                session["mostro_descripcion"] = True
            else:
                return jsonify({"response": "👉 Escribe 'continuar' para empezar con las preguntas."})

        # Obtener pregunta actual
        idx = session["pregunta_actual"]
        if idx < len(tema["preguntas"]):
            pregunta = tema["preguntas"][idx]
            texto = f"{idx+1}. {pregunta['pregunta']}\n" + "\n".join(pregunta["opciones"])
            session["estado"] = "responder"
            return jsonify({"response": texto})
        else:
            session["estado"] = "tema"
            return jsonify({"response": "🎉 Has terminado este tema. Escribe 'tema' para elegir otro."})

    # ========================
    # Flujo de respuestas
    # ========================
    elif session["estado"] == "responder":
        tema = temas.get(session["tema"])
        idx = session["pregunta_actual"]
        pregunta = tema["preguntas"][idx]

        if user_message.lower() == pregunta["respuesta"]:
            respuesta = "✅ Correcto"
        else:
            respuesta = f"❌ Incorrecto. La respuesta correcta era: {pregunta['respuesta']}"

        session["pregunta_actual"] += 1
        session["estado"] = "preguntas"
        return jsonify({"response": respuesta + "\n👉 Escribe 'continuar' para la siguiente pregunta."})

    return jsonify({"response": "⚠️ No entendí tu mensaje."})


if __name__ == "__main__":
    app.run(debug=True)
