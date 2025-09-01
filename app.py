from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
from models import obtener_usuario, crear_usuario, actualizar_usuario, obtener_tema

app = Flask(__name__)
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
            crear_usuario(user_id)
            actualizar_usuario(user_id, "estado", "pidiendo_nombre")
             # 👇 solo el mensaje de bienvenida inicial
            return jsonify({"respuesta": "👋 ¡Hola! Soy tu asistente de inducción. Escribe tu *nombre completo* para continuar."})


        # desempaquetar columnas
        (_, _, nombre, documento, fecha, estado, tema_actual, indice, contador,
         temas_completados, respuestas_correctas, respuestas_incorrectas) = user

        temas_completados = temas_completados.split(",") if temas_completados else []

        # ---------- flujo de registro ----------
        if estado == "pidiendo_nombre":
            # ✅ validación: solo letras y espacios
            if not pregunta_raw.replace(" ", "").isalpha():
                return jsonify({"respuesta": "⚠️ El nombre solo puede contener letras. Inténtalo de nuevo."})

            nombre_actualizado = pregunta_raw.strip().title()
            actualizar_usuario(user_id, "nombre", nombre_actualizado)
            actualizar_usuario(user_id, "estado", "pidiendo_documento")

            return jsonify({"respuesta": f"📄 Perfecto {nombre_actualizado}. Ahora ingresa tu *número de documento*."})


        if estado == "pidiendo_documento":
            actualizar_usuario(user_id, "documento", pregunta_raw.strip())
            fecha_valida = datetime.now().date()
            actualizar_usuario(user_id, "fecha", str(fecha_valida))
            actualizar_usuario(user_id, "estado", "registrado")

            mensaje_registro = (
                f"✅ Registro completado.\n"
                f"👤 Nombre: {nombre or pregunta_raw.strip().title()}\n"   # <-- aquí corriges
                f"🆔 Documento: {pregunta_raw.strip()}\n"
                f"📅 Fecha: {fecha_valida}\n\n"
                "✍️ Escribe 'tema' para ver los temas disponibles."
            )

            mensaje_intro = (
                "🌱 **Quiénes Somos**\n\n"
                "Ambipar ofrece servicios y productos para la gestión ambiental, "
                "cumpliendo con la ética y la responsabilidad socioambiental. "
                "Nuestro compromiso es apoyar a los clientes con soluciones inteligentes "
                "que superen los desafíos de sostenibilidad. "
                "Para nosotros, la sostenibilidad no es un discurso, es nuestro día a día.\n\n"
                "➡️ A continuación selecciona los temas de la inducción para continuar con el proceso de evaluación."
            )

            return jsonify({"respuesta": mensaje_registro, "siguiente": mensaje_intro})

        # ---------- mostrar lista de temas ----------
        if pregunta == "tema":
            if tema_actual and estado in ("en_curso", "confirmar_responder"):
                return jsonify({"respuesta": f"⚠️ Debes terminar el tema **{tema_actual}** antes de elegir otro."})

            pendientes = [t for t in temas_disponibles if t not in temas_completados]
            if not pendientes:
                total = (respuestas_correctas or 0) + (respuestas_incorrectas or 0)
                nota = round(((respuestas_correctas or 0) * 5) / total, 2) if total > 0 else 0
                return jsonify({
                    "respuesta": f"🎓 Has finalizado la inducción.\n"
                                 f"✅ Correctas: {respuestas_correctas}\n"
                                 f"❌ Incorrectas: {respuestas_incorrectas}\n"
                                 f"📊 Nota final: {nota}/5"
                })
            return jsonify({
                "respuesta": "📚 Temas disponibles. ✍️ Escribe el nombre del tema que quieras iniciar:",
                "temas": pendientes
            })

        # ---------- seleccionar tema ----------
        if pregunta in temas_disponibles:
            if tema_actual and tema_actual != pregunta and estado == "en_curso":
                return jsonify({"respuesta": f"⚠️ Ya estás trabajando en el tema **{tema_actual}**. Debes terminarlo antes de iniciar otro."})
            if pregunta in temas_completados:
                return jsonify({"respuesta": f"✅ El tema **{pregunta}** ya fue completado. Escribe 'tema' para ver los que faltan."})

            preguntas_tema = obtener_tema(pregunta)
            if not preguntas_tema:
                return jsonify({"respuesta": f"⚠️ No encontré contenido para el tema {pregunta}."})

            actualizar_usuario(user_id, "tema_actual", pregunta)
            actualizar_usuario(user_id, "estado", "en_curso")
            actualizar_usuario(user_id, "indice", 0)
            actualizar_usuario(user_id, "contador", 0)

            # 👉 lógica mejorada: mostrar info y luego la primera pregunta
            respuestas = {}

            idx = 0
            if preguntas_tema[0][0] == "info":
                tipo0, contenido0, _ = preguntas_tema[0]
                respuestas["respuesta"] = f"💡 {contenido0}"
                idx = 1  # pasamos a la primera pregunta

            if idx < len(preguntas_tema):
                tipo1, contenido1, _ = preguntas_tema[idx]
                if tipo1 == "info":
                # si hubiera dos infos seguidas
                    respuestas["siguiente"] = f"💡 {contenido1}"
                    actualizar_usuario(user_id, "indice", idx + 1)
                else:
                # es pregunta
                    lines = contenido1.splitlines()
                    if len(lines) > 1:
                        pregunta_text = lines[0]
                        opciones = lines[1:]
                    else:
                        parts = contenido1.split(";")
                        pregunta_text = parts[0]
                        opciones = parts[1:] if len(parts) > 1 else []
                    respuestas["pregunta"] = pregunta_text
                    respuestas["opciones"] = opciones
                    actualizar_usuario(user_id, "indice", idx)

            return jsonify(respuestas)

        # ---------- confirmación (sí/no) ----------
        if estado == "confirmar_responder":
            if pregunta in ("si", "sí", "s"):
                preguntas_tema = obtener_tema(tema_actual)
                if not preguntas_tema:
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")
                    return jsonify({"respuesta": "⚠️ Error: no hay contenido para el tema seleccionado."})

                start_idx = 1 if preguntas_tema[0][0] == "info" else 0
                if start_idx >= len(preguntas_tema):
                    lista = temas_completados
                    if tema_actual not in lista:
                        lista.append(tema_actual)
                        actualizar_usuario(user_id, "temas_completados", ",".join(lista))
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")
                    return jsonify({"respuesta": f"✅ El tema **{tema_actual}** no contiene preguntas. Marcado como completado."})

                actualizar_usuario(user_id, "indice", start_idx)
                actualizar_usuario(user_id, "contador", 0)
                actualizar_usuario(user_id, "estado", "en_curso")

                tipo, contenido, _ = preguntas_tema[start_idx]
                if tipo == "info":
                    actualizar_usuario(user_id, "indice", start_idx + 1)
                    return jsonify({"respuesta": f"💡 {contenido}"})
                else:
                    lines = contenido.splitlines()
                    if len(lines) > 1:
                        pregunta_text = lines[0]
                        opciones = lines[1:]
                    else:
                        parts = contenido.split(";")
                        pregunta_text = parts[0]
                        opciones = parts[1:] if len(parts) > 1 else []
                    return jsonify({"pregunta": pregunta_text, "opciones": opciones})

            elif pregunta in ("no", "n"):
                actualizar_usuario(user_id, "tema_actual", None)
                actualizar_usuario(user_id, "estado", "registrado")
                pendientes = [t for t in temas_disponibles if t not in temas_completados]
                return jsonify({"respuesta": "👍 Perfecto. Aquí están los temas disponibles otra vez:", "temas": pendientes})
            else:
                return jsonify({"respuesta": "✍️ Por favor responde 'sí' o 'no'."})

        # ---------- preguntas en curso ----------
        if tema_actual and estado == "en_curso":
            preguntas_tema = obtener_tema(tema_actual)
            idx = int(indice or 0)
            cont = int(contador or 0)

            if idx >= len(preguntas_tema):
                lista = temas_completados
                if tema_actual not in lista:
                    lista.append(tema_actual)
                    actualizar_usuario(user_id, "temas_completados", ",".join(lista))
                actualizar_usuario(user_id, "tema_actual", None)
                actualizar_usuario(user_id, "estado", "registrado")

                pendientes = [t for t in temas_disponibles if t not in lista]
                if not pendientes:
                    total = (respuestas_correctas or 0) + (respuestas_incorrectas or 0)
                    nota = round(((respuestas_correctas or 0) * 5) / total, 2) if total > 0 else 0
                    return jsonify({
                        "respuesta": f"🎓 Has finalizado la inducción.\n"
                                     f"✅ Correctas: {respuestas_correctas}\n"
                                     f"❌ Incorrectas: {respuestas_incorrectas}\n"
                                     f"📊 Nota final: {nota}/5"
                    })

                return jsonify({"respuesta": f"✅ Has completado el tema **{tema_actual}**.\n\n✍️ Escribe 'tema' para continuar con otro tema.", "temas": pendientes})

            tipo, contenido, respuesta_correcta = preguntas_tema[idx]

            if tipo == "info":
                actualizar_usuario(user_id, "indice", idx + 1)
                return jsonify({"respuesta": f"💡 {contenido}"})

            lines = contenido.splitlines()
            if len(lines) > 1:
                pregunta_text = lines[0]
                opciones = lines[1:]
            else:
                parts = contenido.split(";")
                pregunta_text = parts[0]
                opciones = parts[1:] if len(parts) > 1 else []

            if (pregunta.strip().lower() == (respuesta_correcta or "").strip().lower()):
                actualizar_usuario(user_id, "indice", idx + 1)
                actualizar_usuario(user_id, "contador", 0)
                actualizar_usuario(user_id, "respuestas_correctas", (respuestas_correctas or 0) + 1)

                if idx + 1 < len(preguntas_tema):
                    tipo_next, contenido_next, _ = preguntas_tema[idx + 1]
                    if tipo_next == "info":
                        actualizar_usuario(user_id, "indice", idx + 2)
                        return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}", "siguiente": f"💡 {contenido_next}"})
                    else:
                        lines_n = contenido_next.splitlines()
                        if len(lines_n) > 1:
                            pregunta_next = lines_n[0]
                            opciones_next = lines_n[1:]
                        else:
                            parts_n = contenido_next.split(";")
                            pregunta_next = parts_n[0]
                            opciones_next = parts_n[1:] if len(parts_n) > 1 else []
                        actualizar_usuario(user_id, "indice", idx + 1)
                        return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}", "pregunta": pregunta_next, "opciones": opciones_next})
                else:
                    lista = temas_completados
                    if tema_actual not in lista:
                        lista.append(tema_actual)
                        actualizar_usuario(user_id, "temas_completados", ",".join(lista))
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")

                    pendientes = [t for t in temas_disponibles if t not in lista]
                    if not pendientes:
                        total = (respuestas_correctas or 0) + (respuestas_incorrectas or 0)
                        nota = round(((respuestas_correctas or 0) * 5) / total, 2) if total > 0 else 0
                        return jsonify({
                            "respuesta": f"🎉 ¡Correcto! {respuesta_correcta}\n\n"
                                         f"🎓 Has finalizado la inducción.\n"
                                         f"✅ Correctas: {respuestas_correctas+1}\n"
                                         f"❌ Incorrectas: {respuestas_incorrectas}\n"
                                         f"📊 Nota final: {nota}/5"
                        })

                    return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}\n\n📌 Fin del tema.", "temas": pendientes})

            else:
                cont = (cont or 0) + 1
                if cont >= 3:
                    actualizar_usuario(user_id, "indice", idx + 1)
                    actualizar_usuario(user_id, "contador", 0)
                    actualizar_usuario(user_id, "respuestas_incorrectas", (respuestas_incorrectas or 0) + 1)

                    if idx + 1 < len(preguntas_tema):
                        tipo_next, contenido_next, _ = preguntas_tema[idx + 1]
                        if tipo_next == "info":
                            actualizar_usuario(user_id, "indice", idx + 2)
                            return jsonify({"respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}\n\n💡 {contenido_next}"})
                        else:
                            lines_n = contenido_next.splitlines()
                            pregunta_next = lines_n[0] if len(lines_n) > 1 else contenido_next
                            opciones_next = lines_n[1:] if len(lines_n) > 1 else (contenido_next.split(";")[1:] if ";" in contenido_next else [])
                            actualizar_usuario(user_id, "indice", idx + 1)
                            return jsonify({"respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}", "pregunta": pregunta_next, "opciones": opciones_next})
                    else:
                        lista = temas_completados
                        if tema_actual not in lista:
                            lista.append(tema_actual)
                            actualizar_usuario(user_id, "temas_completados", ",".join(lista))
                        actualizar_usuario(user_id, "tema_actual", None)
                        actualizar_usuario(user_id, "estado", "registrado")

                        pendientes = [t for t in temas_disponibles if t not in lista]
                        if not pendientes:
                            total = (respuestas_correctas or 0) + (respuestas_incorrectas or 0)
                            nota = round(((respuestas_correctas or 0) * 5) / total, 2) if total > 0 else 0
                            return jsonify({
                                "respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}\n\n"
                                             f"🎓 Has finalizado la inducción.\n"
                                             f"✅ Correctas: {respuestas_correctas}\n"
                                             f"❌ Incorrectas: {respuestas_incorrectas+1}\n"
                                             f"📊 Nota final: {nota}/5"
                            })

                        return jsonify({"respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}\n\n📌 Fin del tema.", "temas": pendientes})
                else:
                    actualizar_usuario(user_id, "contador", cont)
                    return jsonify({"respuesta": f"⚠️ Incorrecto. Intento {cont}/3", "opciones": opciones})

        return jsonify({"respuesta": "⚠️ No entendí tu mensaje. Escribe 'tema' para continuar."})

    except Exception as e:
        print("💥 Error en /chat:", e)
        return jsonify({"respuesta": "❌ Ocurrió un error en el servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
