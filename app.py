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
            nombre_limpio = pregunta_raw.strip().title() if pregunta_raw else "Usuario"
            actualizar_usuario(user_id, "nombre", nombre_limpio)
            actualizar_usuario(user_id, "estado", "pidiendo_documento")
            return jsonify({"respuesta": f"📄 Perfecto {nombre_limpio}. Ahora, por favor, ingresa tu *número de documento*."})

        # desempaquetar columnas de la tabla usuarios
        (_, _, nombre, documento, fecha, estado, tema_actual, indice, contador,
         temas_completados, respuestas_correctas, respuestas_incorrectas) = user

        temas_completados = temas_completados.split(",") if temas_completados else []

        # ---------- flujo de registro ----------
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

        # ---------- mostrar lista de temas ----------
        if pregunta == "tema":
            # bloquear si ya hay un tema activo
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

        # ---------- seleccionar tema: mostrar descripción y pedir confirmación ----------
        if pregunta in temas_disponibles:
            if tema_actual and tema_actual != pregunta and estado == "en_curso":
                return jsonify({"respuesta": f"⚠️ Ya estás trabajando en el tema **{tema_actual}**. Debes terminarlo antes de iniciar otro."})
            if pregunta in temas_completados:
                return jsonify({"respuesta": f"✅ El tema **{pregunta}** ya fue completado. Escribe 'tema' para ver los que faltan."})

            preguntas_tema = obtener_tema(pregunta)
            if not preguntas_tema:
                return jsonify({"respuesta": f"⚠️ No encontré contenido para el tema {pregunta}."})

            # guardamos tema elegido y ponemos estado a confirmar_responder
            actualizar_usuario(user_id, "tema_actual", pregunta)
            actualizar_usuario(user_id, "estado", "confirmar_responder")
            actualizar_usuario(user_id, "indice", 0)
            actualizar_usuario(user_id, "contador", 0)

            # buscamos la fila "info" (normalmente la primera)
            tipo0, contenido0, _ = preguntas_tema[0]
            return jsonify({
                "respuesta": f"💡 {contenido0}",
                "confirm": f"❓ ¿Quieres responder las preguntas del tema **{pregunta}**? (sí / no)"
            })

        # ---------- el usuario responde a la confirmación (sí/no) ----------
        if estado == "confirmar_responder":
            if pregunta in ("si", "sí", "s"):
                preguntas_tema = obtener_tema(tema_actual)
                if not preguntas_tema:
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")
                    return jsonify({"respuesta": "⚠️ Error: no hay contenido para el tema seleccionado."})

                # empezamos en la primera pregunta (si la fila 0 es info, la pregunta empieza en 1)
                start_idx = 1 if preguntas_tema[0][0] == "info" else 0
                if start_idx >= len(preguntas_tema):
                    # no hay preguntas -> marcar completado
                    lista = temas_completados
                    if tema_actual not in lista:
                        lista.append(tema_actual)
                        actualizar_usuario(user_id, "temas_completados", ",".join(lista))
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")
                    return jsonify({"respuesta": f"✅ El tema **{tema_actual}** no contiene preguntas. Marcado como completado."})

                # guardamos indice del primer ítem a responder (pregunta)
                actualizar_usuario(user_id, "indice", start_idx)
                actualizar_usuario(user_id, "contador", 0)
                actualizar_usuario(user_id, "estado", "en_curso")

                tipo, contenido, _ = preguntas_tema[start_idx]
                if tipo == "info":
                    # raro, pero enviamos info y avanzamos índice
                    actualizar_usuario(user_id, "indice", start_idx + 1)
                    return jsonify({"respuesta": f"💡 {contenido}"})
                else:
                    # parsear opciones separadas por líneas
                    lines = contenido.splitlines()
                    if len(lines) > 1:
                        pregunta_text = lines[0]
                        opciones = lines[1:]
                    else:
                        # fallback: si estaba con ';'
                        parts = contenido.split(";")
                        pregunta_text = parts[0]
                        opciones = parts[1:] if len(parts) > 1 else []
                    return jsonify({"pregunta": pregunta_text, "opciones": opciones})

            elif pregunta in ("no", "n"):
                # cancelar: liberar tema_actual y volver al listado
                actualizar_usuario(user_id, "tema_actual", None)
                actualizar_usuario(user_id, "estado", "registrado")
                pendientes = [t for t in temas_disponibles if t not in temas_completados]
                return jsonify({"respuesta": "👍 Perfecto. Aquí están los temas disponibles otra vez:", "temas": pendientes})
            else:
                return jsonify({"respuesta": "✍️ Por favor responde 'sí' o 'no'."})

        # ---------- manejo de preguntas cuando hay tema en curso ----------
        if tema_actual and estado == "en_curso":
            preguntas_tema = obtener_tema(tema_actual)
            idx = int(indice or 0)
            cont = int(contador or 0)

            # seguridad: si idx >= len -> marcar completado
            if idx >= len(preguntas_tema):
                lista = temas_completados
                if tema_actual not in lista:
                    lista.append(tema_actual)
                    actualizar_usuario(user_id, "temas_completados", ",".join(lista))
                actualizar_usuario(user_id, "tema_actual", None)
                actualizar_usuario(user_id, "estado", "registrado")
                pendientes = [t for t in temas_disponibles if t not in lista]
                return jsonify({"respuesta": f"✅ Has completado el tema **{tema_actual}**.\n\n✍️ Escribe 'tema' para continuar con otro tema.", "temas": pendientes})

            tipo, contenido, respuesta_correcta = preguntas_tema[idx]

            # si es info (raro en en_curso) -> mostrar y avanzar
            if tipo == "info":
                actualizar_usuario(user_id, "indice", idx + 1)
                siguiente = preguntas_tema[idx+1][1] if idx+1 < len(preguntas_tema) else None
                if siguiente:
                    return jsonify({"respuesta": f"💡 {contenido}", "siguiente": siguiente})
                return jsonify({"respuesta": f"💡 {contenido}"})

            # parsear pregunta y opciones
            lines = contenido.splitlines()
            if len(lines) > 1:
                pregunta_text = lines[0]
                opciones = lines[1:]
            else:
                parts = contenido.split(";")
                pregunta_text = parts[0]
                opciones = parts[1:] if len(parts) > 1 else []

            # comparar respuesta del usuario (pregunta contiene la letra correcta en DB)
            if (pregunta.strip().lower() == (respuesta_correcta or "").strip().lower()):
                # correcto: avanzar indice
                actualizar_usuario(user_id, "indice", idx + 1)
                actualizar_usuario(user_id, "contador", 0)
                actualizar_usuario(user_id, "respuestas_correctas", (respuestas_correctas or 0) + 1)

                # preparar siguiente pregunta (si hay)
                if idx + 1 < len(preguntas_tema):
                    tipo_next, contenido_next, _ = preguntas_tema[idx + 1]
                    if tipo_next == "info":
                        # enviar info como siguiente
                        actualizar_usuario(user_id, "indice", idx + 2)  # avanzamos por la info
                        return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}", "siguiente": f"💡 {contenido_next}"})
                    else:
                        # pregunta siguiente -> enviar pregunta + opciones
                        lines_n = contenido_next.splitlines()
                        if len(lines_n) > 1:
                            pregunta_next = lines_n[0]
                            opciones_next = lines_n[1:]
                        else:
                            parts_n = contenido_next.split(";")
                            pregunta_next = parts_n[0]
                            opciones_next = parts_n[1:] if len(parts_n) > 1 else []
                        # dejamos indice en idx+1 (la próxima pregunta) hasta que el usuario responda
                        actualizar_usuario(user_id, "indice", idx + 1)
                        return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}", "pregunta": pregunta_next, "opciones": opciones_next})
                else:
                    # no hay siguiente -> fin del tema
                    lista = temas_completados
                    if tema_actual not in lista:
                        lista.append(tema_actual)
                        actualizar_usuario(user_id, "temas_completados", ",".join(lista))
                    actualizar_usuario(user_id, "tema_actual", None)
                    actualizar_usuario(user_id, "estado", "registrado")
                    pendientes = [t for t in temas_disponibles if t not in lista]
                    return jsonify({"respuesta": f"🎉 ¡Correcto! {respuesta_correcta}\n\n📌 Fin del tema.", "temas": pendientes})

            else:
                # incorrecto: aumentar contador y permitir reintento hasta 3
                cont = (cont or 0) + 1
                if cont >= 3:
                    # mostrar la respuesta y avanzar
                    actualizar_usuario(user_id, "indice", idx + 1)
                    actualizar_usuario(user_id, "contador", 0)
                    actualizar_usuario(user_id, "respuestas_incorrectas", (respuestas_incorrectas or 0) + 1)
                    # siguiente pregunta si existe
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
                        return jsonify({"respuesta": f"❌ Incorrecto. La respuesta era: {respuesta_correcta}\n\n📌 Fin del tema.", "temas": pendientes})
                else:
                    actualizar_usuario(user_id, "contador", cont)
                    opciones_mostrar = opciones
                    return jsonify({"respuesta": f"⚠️ Incorrecto. Intento {cont}/3", "opciones": opciones_mostrar})

        # ---------- por defecto ----------
        return jsonify({"respuesta": "⚠️ No entendí tu mensaje. Escribe 'tema' para continuar."})

    except Exception as e:
        print("💥 Error en /chat:", e)
        return jsonify({"respuesta": "❌ Ocurrió un error en el servidor"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
