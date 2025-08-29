from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from models import obtener_usuario, crear_usuario, actualizar_usuario, obtener_tema

app = Flask(__name__)

# ============================
# CONFIGURACIÓN DE CORS
# ============================
CORS(app, resources={r"/*": {"origins": "*"}})

# ============================
# RUTAS API
# ============================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "🚀 Bienvenido a la API del Chatbot de Inducción",
        "endpoints": {"chat": "POST /chat"}
    })

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_id = request.json.get("usuario_id") or request.remote_addr
        pregunta = request.json.get("pregunta", "").strip().lower()

        # Verificar si el usuario existe
        user = obtener_usuario(user_id)
        if not user:
            # Primera vez que escribe → registrar
            crear_usuario(user_id)
            nombre_limpio = pregunta.title()
            actualizar_usuario(user_id, "nombre", nombre_limpio)
            actualizar_usuario(user_id, "estado", "pidiendo_documento")
            return jsonify({"respuesta": f"📄 Perfecto {nombre_limpio}. Ahora, por favor, ingresa tu *número de documento*."})

        # Mapeo de columnas de la tabla usuarios
        (_, _, nombre, documento, fecha, estado, tema_actual, indice, contador,
         temas_completados, respuestas_correctas, respuestas_incorrectas) = user

        temas_disponibles = ["riesgos", "aspectos", "impacto", "procedimientos", "comites", "emergencias", "responsabilidades"]
        temas_completados = temas_completados.split(",") if temas_completados else []

        # =======================
        # FLUJO DE REGISTRO
        # =======================
        if estado == "pidiendo_nombre":
            actualizar_usuario(user_id, "nombre", pregunta.title())
            actualizar_usuario(user_id, "estado", "pidiendo_documento")
            return jsonify({"respuesta": f"📄 Perfecto {pregunta.title()}. Ahora, por favor, ingresa tu *número de documento*."})

        if estado == "pidiendo_documento":
            actualizar_usuario(user_id, "documento", pregunta)
            actualizar_usuario(user_id, "estado", "pidiendo_fecha")
            return jsonify({"respuesta": "📅 Perfecto. Ingresa la *fecha de esta conversación* (AAAA-MM-DD)."})

        if estado == "pidiendo_fecha":
            try:
                fecha_valida = datetime.strptime(pregunta, "%Y-%m-%d").date()
                actualizar_usuario(user_id, "fecha", str(fecha_valida))
            except ValueError:
                return jsonify({"respuesta": "⚠️ Formato de fecha inválido. Usa AAAA-MM-DD (ejemplo: 2025-08-22)"})

            actualizar_usuario(user_id, "estado", "registrado")

            mensaje_registro = (
                f"✅ Registro completado.\n"
                f"👤 Nombre: {nombre or pregunta.title()}\n"
                f"🆔 Documento: {documento or 'N/A'}\n"
                f"📅 Fecha: {fecha or str(fecha_valida)}\n\n"
                "✍️ Escribe 'tema' para ver los temas disponibles."
            )

            mensaje_intro = (
                "🌱 **Quiénes Somos**\n\n"
                "Ambipar ofrece servicios y productos para la gestión ambiental, "
                "cumpliendo con la ética y la responsabilidad socioambiental. "
                "Nuestro compromiso es apoyar a los clientes con soluciones inteligentes "
                "que superen los desafíos de sostenibilidad. "
                "Para nosotros, la sostenibilidad no es un discurso, es nuestro día a día."
            )

            return jsonify({"respuesta": mensaje_registro, "siguiente": mensaje_intro})

        # =======================
        # SELECCIÓN DE TEMAS
        # =======================
        if pregunta == "tema":
            pendientes = [t for t in temas_disponibles if t not in temas_completados]
            if not pendientes:
                total = respuestas_correctas + respuestas_incorrectas
                nota = round((respuestas_correctas * 5) / total, 2) if total > 0 else 0
                return jsonify({
                    "respuesta": f"🎓 Has finalizado la inducción.\n✅ Correctas: {respuestas_correctas}\n❌ Incorrectas: {respuestas_incorrectas}\n📊 Nota final: {nota}/5"
                })
            return jsonify({
                "respuesta": "📚 Temas disponibles. ✍️ Escribe el nombre del tema que quieras iniciar:",
                "temas": pendientes
            })

        if pregunta in temas_disponibles:
            # 🚫 Validación: no dejar cambiar si ya hay un tema en curso
            if tema_actual and tema_actual != pregunta:
                return jsonify({"respuesta": f"⚠️ Ya estás trabajando en el tema **{tema_actual}**. Debes terminarlo antes de iniciar otro."})

            if pregunta in temas_completados:
                return jsonify({"respuesta": f"✅ El tema **{pregunta}** ya fue completado. Escribe 'tema' para ver los que faltan."})

            actualizar_usuario(user_id, "tema_actual", pregunta)
            actualizar_usuario(user_id, "indice", 0)
            actualizar_usuario(user_id, "contador", 0)
            preguntas = obtener_tema(pregunta)
            if not preguntas:
                return jsonify({"respuesta": f"⚠️ No encontré contenido para el tema {pregunta}."})
            tipo, contenido, _ = preguntas[0]
            siguiente = preguntas[1][1] if len(preguntas) > 1 else "📌 Fin del tema."
            return jsonify({"respuesta": f"💡 {contenido}", "siguiente": siguiente})

        # =======================
        # MANEJO DE CONTENIDO
        # =======================
        if tema_actual:
            preguntas = obtener_tema(tema_actual)
            idx = indice
            cont = contador

            if idx >= len(preguntas):
                temas_completados.append(tema_actual)
                actualizar_usuario(user_id, "temas_completados", ",".join(temas_completados))
                actualizar_usuario(user_id, "tema_actual", None)
                return jsonify({"respuesta": f"✅ Has completado el tema **{tema_actual}**.\n\n✍️ Escribe 'tema' para continuar con otro tema."})

            tipo, contenido, respuesta_correcta = preguntas[idx]

            if tipo == "info":
                actualizar_usuario(user_id, "indice", idx + 1)
                siguiente = preguntas[idx+1][1] if idx+1 < len(preguntas) else "📌 Fin del tema."
                return jsonify({"respuesta": f"💡 {contenido}", "siguiente": siguiente})

            # Preguntas tipo quiz
            opciones = contenido.split(";") if ";" in contenido else [contenido]
            opciones_ordenadas = "\n".join([f"• {op.strip()}" for op in opciones])

            if pregunta.strip().lower() == respuesta_correcta.strip().lower():
                actualizar_usuario(user_id, "indice", idx + 1)
                actualizar_usuario(user_id, "contador", 0)
                actualizar_usuario(user_id, "respuestas_correctas", respuestas_correctas + 1)
                siguiente = preguntas[idx+1][1] if idx+1 < len(preguntas) else "📌 Fin del tema."
                return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}", "siguiente": siguiente})
            else:
                cont += 1
                if cont >= 3:
                    actualizar_usuario(user_id, "indice", idx + 1)
                    actualizar_usuario(user_id, "contador", 0)
                    actualizar_usuario(user_id, "respuestas_incorrectas", respuestas_incorrectas + 1)
                    siguiente = preguntas[idx+1][1] if idx+1 < len(preguntas) else "📌 Fin del tema."
                    return jsonify({"respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}", "siguiente": siguiente})
                else:
                    actualizar_usuario(user_id, "contador", cont)
                    return jsonify({"respuesta": f"⚠️ Incorrecto. Intento {cont}/3\n\nOpciones:\n{opciones_ordenadas}"})

        return jsonify({"respuesta": "⚠️ No entendí tu mensaje. Escribe 'tema' para continuar."})

    except Exception as e:
        print("💥 Error en /chat:", e)
        return jsonify({"respuesta": "❌ Ocurrió un error en el servidor"}), 500


# Para producción con Gunicorn (Render no usa app.run)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
