# db_setup.py
import psycopg2
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_cxKm4qaU1DNl@ep-blue-field-admkxy2t-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)

def run_setup():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # Tabla usuarios
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id SERIAL PRIMARY KEY,
        usuario_id TEXT UNIQUE NOT NULL,
        nombre TEXT,
        documento TEXT,
        fecha TEXT,
        estado TEXT DEFAULT 'pidiendo_nombre',
        tema_actual TEXT,
        indice INTEGER DEFAULT 0,
        contador INTEGER DEFAULT 0,
        temas_completados TEXT DEFAULT '',
        respuestas_correctas INTEGER DEFAULT 0,
        respuestas_incorrectas INTEGER DEFAULT 0
    )
    """)

    # Tabla temas
    cur.execute("""
    CREATE TABLE IF NOT EXISTS temas (
        id SERIAL PRIMARY KEY,
        tema TEXT NOT NULL,
        tipo TEXT NOT NULL,   -- "info" o "pregunta"
        contenido TEXT NOT NULL,
        respuesta_correcta TEXT
    )
    """)

    # Limpiar e insertar temas (idempotente para este script: hacemos DELETE e INSERT)
    cur.execute("DELETE FROM temas")

    temas_y_preguntas = [
        ("riesgos", "info", "Los riesgos y peligros son todos auqellos elementos que pueden generar accidentes,incidentes o emergencias,para prevenisrlos recuerda: aplicar el análisis de trabajo seguro, usar adecuadamente los  EPP, realizar  ejercicios de estiramiento, reportr de actos y condiciones inseguras, y reportar tu estado  de salud"),
        ("riesgos", "pregunta", "1. ¿Qué debe hacer un trabajador para prevenir riesgos?\na) No reportar actos inseguros\nb) Hacer ejercicios de estiramiento y usar EPP\nc) Ignorar el estado de salud\nd) Ninguna de las anteriores", "b"),
        ("aspectos", "info", "Aspectos ambientales: componentes de un producto, actividad o servicio que pueden interactuar o causar un efecto en el medio ambiente, como consumo de agua, energía o generación de residuos."),
        ("aspectos", "pregunta", "1. ¿Cuál es un ejemplo de aspecto ambiental?\na) Consumo de agua\nb) Consumo de energía\nc) Generación de residuos\nd) Todas las anteriores", "d"),
        ("impacto", "info", "Impacto ambiental: efecto real que el aspecto ambiental tiene sobre el medio. Ejemplo: contaminación del agua, no segregación de residuos, alto consumo de energía."),
        ("impacto", "pregunta", "1. ¿Qué es un impacto ambiental?\na) Una acción preventiva\nb) Un efecto real sobre el ambiente\nc) Un tipo de EPP\nd) Un comité de seguridad", "b"),
        ("procedimientos", "info", "Dentro de las actividades se desarrollan algunas tareas de alto riesgo, recuerda que para realizarlas debes, contar con un permiso de trabajo en alturas, utilizar el arnés para el ascenso o descenso Alos vehículos , aislar el área de posibles fuentes de ignición, y aplicar el análisis de comportamientos críticos"),
        ("procedimientos", "pregunta", "1. ¿Qué se requiere para trabajos en alturas (>2m)?\na) Permiso y uso de arnés\nb) Nada especial\nc) Solo casco\nd) Ninguna de las anteriores", "a"),
        ("comites", "info", "Comités: Comité de Seguridad y Salud en el Trabajo y Comité de Convivencia Laboral."),
        ("comites", "pregunta", "1. Una función del Comité de Seguridad y Salud en el Trabajo es:\na) Capacitar en seguridad\nb) Vender EPP\nc) velar por el cumplimeinto d elos programas de seguridad\nd) Ninguna", "c"),
        ("emergencias", "info", "Una vez en el sitio recuerde establecer y conocer el plan de emergencia en caso de accidente o incidente, recuerde seguir la instrucciones del personal, dirigirse al área de atención de emergencia y punto de encuentro , conservar la calma y conocer el punto de atención mas cercano de la ARL"),
        ("emergencias", "pregunta", "1. En caso de evacuación debe:\na) Correr y gritar\nb) Conservar la calma y dirigirse al punto de encuentro\nc) Usar el celular\nd) Esconderse", "b"),
        ("responsabilidades", "info", "Por ultimo, recuerda cuales son tus funciones y responsabilidades durante la prestación del servicios:apoyar limpieza y contención, usar EPP, reportar actos inseguros, no operar maquinaria sin capacitación, realizar estiramientos, garantizar hidratación y descanso."),
        ("responsabilidades", "pregunta", "1. Función de los trabajadores:\na) Reportar actos inseguros y usar EPP\nb) Operar equipos sin capacitación\nc) Ignorar su salud\nd) No hidratarse", "a"),
    ]

    for item in temas_y_preguntas:
        if len(item) == 3:
            cur.execute(
                "INSERT INTO temas (tema, tipo, contenido) VALUES (%s, %s, %s)",
                (item[0], item[1], item[2])
            )
        else:
            cur.execute(
                "INSERT INTO temas (tema, tipo, contenido, respuesta_correcta) VALUES (%s, %s, %s, %s)",
                (item[0], item[1], item[2], item[3])
            )

    conn.commit()
    cur.close()
    conn.close()
    print("✅ DB creada / actualizada y temas insertados")

if __name__ == "__main__":
    run_setup()
