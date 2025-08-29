from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from models import obtener_usuario, crear_usuario, actualizar_usuario, obtener_tema

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "🚀 API de Inducción funcionando"})

@app.route("/chat", methods=["POST"])
def chat():
    try:
        user_id = request.json.get("usuario_id") or request.remote_addr
        pregunta = request.json.get("pregunta", "").strip().lower()

        # Obtener o crear usuario
        user = obtener_usuario(user_id)
        if not user:
            crear_usuario(user_id)
            return jsonify({"respuesta": "👋 Bienvenido, dime tu *nombre completo* para empezar."})

        (id, usuario_id, nombre, documento, fecha, estado, tema_actual,
         indice, contador, temas_completados, correctas, incorrectas) = user

        temas_disponibles = ["riesgos", "aspectos", "impacto", "procedimientos", "comites", "emergencias", "responsabilidades"]
        temas_completados = temas_completados.split(",") if temas_completados else []

        # =======================
        # FLUJO DE REGISTRO
        # =======================
        if estado == "pidiendo_nombre":
            actualizar_usuario(user_id, "nombre", pregunta.title())
            actualizar_usuario(user_id, "estado", "pidiendo_documento")
            return jsonify({"respuesta": f"✅ Gracias {pregunta.title()}. Ahora dime tu *documento*."})

        if estado == "pidiendo_documento":
            actualizar_usuario(user_id, "documento", pregunta)
            actualizar_usuario(user_id, "estado", "pidiendo_fecha")
            return jsonify({"respuesta": "📅 Perfecto. Ingresa la *fecha de hoy* (AAAA-MM-DD)."})

        if estado == "pidiendo_fecha":
            try:
                fecha_valida = datetime.strptime(pregunta, "%Y-%m-%d").date()
                actualizar_usuario(user_id, "fecha", str(fecha_valida))
            except ValueError:
                return jsonify({"respuesta": "⚠️ Fecha inválida. Usa AAAA-MM-DD."})

            actualizar_usuario(user_id, "estado", "registrado")
            return jsonify({
                "respuesta": "✅ Registro completado. Escribe 'tema' para ver los disponibles."
            })

        # =======================
        # LISTAR TEMAS
        # =======================
        if pregunta == "tema":
            if tema_actual:
                return jsonify({"respuesta": f"⚠️ Debes terminar el tema **{tema_actual}** antes de elegir otro."})

            pendientes = [t for t in temas_disponibles if t not in temas_completados]
            if not pendientes:
                total = correctas + incorrectas
                nota = round((correctas * 5) / total, 2) if total > 0 else 0
                return jsonify({
                    "respuesta": f"🎓 Has finalizado la inducción.\n✅ Correctas: {correctas}\n❌ Incorrectas: {incorrectas}\n📊 Nota: {nota}/5"
                })
            return jsonify({
                "respuesta": "📚 Temas disponibles:\n" + "\n".join([f"- {t}" for t in pendientes])
            })

        # =======================
        # SELECCIONAR TEMA
        # =======================
        if pregunta in temas_disponibles:
            if tema_actual and tema_actual != pregunta:
                return jsonify({"respuesta": f"⚠️ Ya estás en el tema **{tema_actual}**. Termínalo antes de cambiar."})

            if pregunta in temas_completados:
                return jsonify({"respuesta": f"✅ El tema **{pregunta}** ya fue completado."})

            actualizar_usuario(user_id, "tema_actual", pregunta)
            actualizar_usuario(user_id, "indice", 0)
            actualizar_usuario(user_id, "contador", 0)

            preguntas = obtener_tema(pregunta)
            if not preguntas:
                return jsonify({"respuesta": f"⚠️ No hay contenido para {pregunta}."})

            tipo, contenido, _ = preguntas[0]
            return jsonify({"respuesta": f"💡 {contenido}"})

        # =======================
        # MANEJO DEL TEMA ACTUAL
        # =======================
        if tema_actual:
            preguntas = obtener_tema(tema_actual)
            idx = indice
            cont = contador

            if idx >= len(preguntas):
                temas_completados.append(tema_actual)
                actualizar_usuario(user_id, "temas_completados", ",".join(temas_completados))
                actualizar_usuario(user_id, "tema_actual", None)
                return jsonify({"respuesta": f"✅ Has completado **{tema_actual}**.\nEscribe 'tema' para continuar."})

            tipo, contenido, respuesta_correcta = preguntas[idx]

            if tipo == "info":
                actualizar_usuario(user_id, "indice", idx + 1)
                return jsonify({"respuesta": f"💡 {contenido}"})

            if tipo == "pregunta":
                if pregunta == respuesta_correcta.lower():
                    actualizar_usuario(user_id, "indice", idx + 1)
                    actualizar_usuario(user_id, "contador", 0)
                    actualizar_usuario(user_id, "respuestas_correctas", correctas + 1)
                    return jsonify({"respuesta": "🎉 ¡Correcto!"})
                else:
                    cont += 1
                    if cont >= 3:
                        actualizar_usuario(user_id, "indice", idx + 1)
                        actualizar_usuario(user_id, "contador", 0)
                        actualizar_usuario(user_id, "respuestas_incorrectas", incorrectas + 1)
                        return jsonify({"respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}"})
                    else:
                        actualizar_usuario(user_id, "contador", cont)
                        return jsonify({"respuesta": f"⚠️ Incorrecto. Intento {cont}/3"})

        return jsonify({"respuesta": "🤔 No entendí. Escribe 'tema' para continuar."})

    except Exception as e:
        print("💥 Error en /chat:", e)
        return jsonify({"respuesta": "❌ Error interno en el servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
