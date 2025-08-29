# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from models import obtener_usuario, crear_usuario, actualizar_usuario, obtener_tema

app = Flask(__name__)
# permitir CORS desde cualquier origen (útil en pruebas / frontend local)
CORS(app, resources={r"/*": {"origins": "*"}})

temas_disponibles = ["riesgos", "aspectos", "impacto", "procedimientos", "comites", "emergencias", "responsabilidades"]

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
        pregunta_raw = request.json.get("pregunta", "")
        pregunta = pregunta_raw.strip().lower()

        # obtener usuario
        user = obtener_usuario(user_id)
        if not user:
            # primer mensaje: creamos el registro y tomamos esa entrada como nombre
            crear_usuario(user_id)
            nombre_limpio = pregunta_raw.strip().title() if pregunta_raw else "Usuario"
            actualizar_usuario(user_id, "nombre", nombre_limpio)
            actualizar_usuario(user_id, "estado", "pidiendo_documento")
            return jsonify({"respuesta": f"📄 Perfecto {nombre_limpio}. Ahora, por favor, ingresa tu *número de documento*."})

        # Desempaquetar columnas (según schema)
        (_, _, nombre, documento, fecha, estado, tema_actual, indice, contador,
         temas_completados, respuestas_correctas, respuestas_incorrectas) = user

        temas_completados = temas_completados.split(",") if temas_completados else []

        # ------------- Flujo de registro -------------
        if estado == "pidiendo_nombre":
            actualizar_usuario(user_id, "nombre", pregunta_raw.strip().title())
            actualizar_usuario(user_id, "estado", "pidiendo_documento")
            return jsonify({"respuesta": f"📄 Perfecto {pregunta_raw.strip().title()}. Ahora, por favor, ingresa tu *número de documento*."})

        if estado == "pidiendo_documento":
            actualizar_usuario(user_id, "documento", pregunta_raw.strip())
            actualizar_usuario(user_id, "estado", "pidiendo_fecha")
            return jsonify({"respuesta": "📅 Perfecto. Ingresa la *fecha de esta conversación* (AAAA-MM-DD)."})

        if estado == "pidiendo_fecha":
            try:
                fecha_valida = datetime.strptime(pregunta_raw.strip(), "%Y-%m-%d").date()
                actualizar_usuario(user_id, "fecha", str(fecha_valida))
            except ValueError:
                return jsonify({"respuesta": "⚠️ Formato de fecha inválido. Usa AAAA-MM-DD (ejemplo: 2025-08-22)"})
            actualizar_usuario(user_id, "estado", "registrado")
            mensaje_registro = (
                f"✅ Registro completado.\n"
                f"👤 Nombre: {nombre or pregunta_raw.strip().title()}\n"
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

        # ------------- Mostrar lista de temas -------------
        if pregunta == "tema":
            # si ya hay un tema en curso (en progreso o confirmación) bloquear listado
            if tema_actual and estado in ("en_curso", "confirmar_responder"):
                return jsonify({"respuesta": f"⚠️ Debes terminar el tema **{tema_actual}** antes de elegir otro."})
            pendientes = [t for t in temas_disponibles if t not in temas_completados]
            if not pendientes:
                total = (respuestas_correctas or 0) + (respuestas_incorrectas or 0)
                nota = round(((respuestas_correctas or 0) * 5) / total, 2) if total > 0 else 0
                return jsonify({
                    "respuesta": f"🎓 Has finalizado la inducción.\n✅ Correctas: {respuestas_correctas}\n❌ Incorrectas: {respuestas_incorrectas}\n📊 Nota final: {nota}/5"
                })
            return jsonify({
                "respuesta": "📚 Temas disponibles. ✍️ Escribe el nombre del tema que quieras iniciar:",
                "temas": pendientes
            })

        # ------------- Selección de tema (se muestra descripción + confirmación) -------------
        if pregunta in temas_disponibles:
            # si hay tema distinto en curso
            if tema_actual and tema_actual != pregunta and estado == "en_curso":
                return jsonify({"respuesta": f"⚠️ Ya estás trabajando en el tema **{tema_actual}**. Debes terminarlo antes de iniciar otro."})

            if pregunta in temas_completados:
                return jsonify({"respuesta": f"✅ El tema **{pregunta}** ya fue completado. Escribe 'tema' para ver los que faltan."})

            # Obtener contenido del tema: esperamos que el primer registro sea 'info'
            preguntas_tema = obtener_tema(pregunta)
            if not preguntas_tema:
                return jsonify({"respuesta": f"⚠️ No encontré contenido para el tema {pregunta}."})

            # Mostrar descripción (info) y pedir confirmación para iniciar preguntas
            # Guardamos el tema en tema_actual y estado a 'confirmar_responder'
            actualizar_usuario(user_id, "tema_actual", pregunta)
            actualizar_usuario(user_id, "estado", "confirmar_responder")
            actualizar_usuario(user_id, "indice", 0)
            actualizar_usuario(user_id, "contador", 0)

            # buscar la primera fila tipo info (normalmente es la primera)
            tipo0, contenido0, _ = preguntas_tema[0]
            # devolver descripción y la pregunta de confirmación
            return jsonify({
                "respuesta": f"💡 {contenido0}",
                "siguiente": f"❓ ¿Quieres responder las preguntas del tema **{pregunta}**? (sí / no)"
            })

        # ------------- Confirmación para iniciar quiz -------------
        if estado == "confirmar_responder":
            # pregunta debe ser sí/no
            if pregunta in ("si", "sí", "s"):
                # arrancar quiz: colocar indice en la primera pregunta (si el primer elem es info, empezamos en 1)
                preguntas_tema = obtener_tema(tema_actual)
                if not preguntas_tema:
                    # seguridad
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")
                    return jsonify({"respuesta": "⚠️ Error: no hay contenido para el tema seleccionado."})

                start_idx = 1 if preguntas_tema and preguntas_tema[0][0] == "info" else 0
                # si no hay preguntas (p.e. solo info), marcar como completado
                if start_idx >= len(preguntas_tema):
                    # marcar completado y liberar tema
                    temas_completados_list = temas_completados
                    if tema_actual not in temas_completados_list:
                        temas_completados_list.append(tema_actual)
                        actualizar_usuario(user_id, "temas_completados", ",".join(temas_completados_list))
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")
                    return jsonify({"respuesta": f"✅ El tema **{tema_actual}** no contiene preguntas. Marcado como completado."})

                actualizar_usuario(user_id, "indice", start_idx)
                actualizar_usuario(user_id, "contador", 0)
                actualizar_usuario(user_id, "estado", "en_curso")

                # enviar la primera pregunta (o info si por alguna razón)
                tipo, contenido, _ = preguntas_tema[start_idx]
                if tipo == "info":
                    # enviamos info y avanzamos indice
                    actualizar_usuario(user_id, "indice", start_idx + 1)
                    siguiente = preguntas_tema[start_idx+1][1] if start_idx+1 < len(preguntas_tema) else "📌 Fin del tema."
                    return jsonify({"respuesta": f"💡 {contenido}", "siguiente": siguiente})
                else:
                    # pregunta tipo quiz
                    opciones = contenido.split(";") if ";" in contenido else [contenido]
                    opciones_ordenadas = "\n".join([f"• {op.strip()}" for op in opciones])
                    return jsonify({"respuesta": contenido, "siguiente": f"Opciones:\n{opciones_ordenadas}"})

            elif pregunta in ("no", "n"):
                # cancelar: quitar tema_actual y volver a lista
                actualizar_usuario(user_id, "tema_actual", None)
                actualizar_usuario(user_id, "estado", "registrado")
                pendientes = [t for t in temas_disponibles if t not in temas_completados]
                return jsonify({
                    "respuesta": "👍 Perfecto. Aquí están los temas disponibles otra vez:",
                    "temas": pendientes
                })
            else:
                return jsonify({"respuesta": "✍️ Por favor responde 'sí' o 'no'."})

        # ------------- Manejo del contenido cuando hay un tema en curso -------------
        if tema_actual and estado == "en_curso":
            preguntas_tema = obtener_tema(tema_actual)
            idx = indice or 0
            cont = contador or 0

            # seguridad: si idx fuera >= len -> marcar completado
            if idx >= len(preguntas_tema):
                # marcar completado
                temas_completados_list = temas_completados
                if tema_actual not in temas_completados_list:
                    temas_completados_list.append(tema_actual)
                    actualizar_usuario(user_id, "temas_completados", ",".join(temas_completados_list))
                actualizar_usuario(user_id, "tema_actual", None)
                actualizar_usuario(user_id, "estado", "registrado")
                return jsonify({"respuesta": f"✅ Has completado el tema **{tema_actual}**.\n\n✍️ Escribe 'tema' para continuar con otro tema."})

            tipo, contenido, respuesta_correcta = preguntas_tema[idx]

            # Si el item es info (poco probable dentro en_curso) mostramos y avanzamos
            if tipo == "info":
                actualizar_usuario(user_id, "indice", idx + 1)
                siguiente = preguntas_tema[idx+1][1] if idx+1 < len(preguntas_tema) else "📌 Fin del tema."
                return jsonify({"respuesta": f"💡 {contenido}", "siguiente": siguiente})

            # Si es pregunta -> comparar
            # Si el usuario envía la opción correcta:
            if (pregunta.strip().lower() == (respuesta_correcta or "").strip().lower()):
                actualizar_usuario(user_id, "indice", idx + 1)
                actualizar_usuario(user_id, "contador", 0)
                actualizar_usuario(user_id, "respuestas_correctas", (respuestas_correctas or 0) + 1)
                # preparar siguiente texto
                siguiente = preguntas_tema[idx+1][1] if idx+1 < len(preguntas_tema) else "📌 Fin del tema."
                return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}", "siguiente": siguiente})
            else:
                # respuesta incorrecta
                cont = (cont or 0) + 1
                if cont >= 3:
                    # mostrar la respuesta y avanzar
                    actualizar_usuario(user_id, "indice", idx + 1)
                    actualizar_usuario(user_id, "contador", 0)
                    actualizar_usuario(user_id, "respuestas_incorrectas", (respuestas_incorrectas or 0) + 1)
                    siguiente = preguntas_tema[idx+1][1] if idx+1 < len(preguntas_tema) else "📌 Fin del tema."
                    return jsonify({"respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}", "siguiente": siguiente})
                else:
                    # guardar contador y pedir reintento, mostrar opciones
                    actualizar_usuario(user_id, "contador", cont)
                    opciones = contenido.split(";") if ";" in contenido else [contenido]
                    opciones_ordenadas = "\n".join([f"• {op.strip()}" for op in opciones])
                    return jsonify({"respuesta": f"⚠️ Incorrecto. Intento {cont}/3\n\nOpciones:\n{opciones_ordenadas}"})

        # ------------- Mensaje por defecto -------------
        return jsonify({"respuesta": "⚠️ No entendí tu mensaje. Escribe 'tema' para continuar."})

    except Exception as e:
        print("💥 Error en /chat:", e)
        return jsonify({"respuesta": "❌ Ocurrió un error en el servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
