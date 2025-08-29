# db_setup.py
import psycopg2
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_wdLcRaVTk68A@ep-jolly-heart-adfm5yui-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
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
        ("riesgos", "info", "Riesgos y peligros: análisis de trabajo seguro, uso adecuados de EPP, ejercicios de estiramiento, reporte de actos y condiciones inseguras, y reportes de estado de salud."),
        ("riesgos", "pregunta", "1. ¿Qué debe hacer un trabajador para prevenir riesgos?\na) No reportar actos inseguros\nb) Hacer ejercicios de estiramiento y usar EPP\nc) Ignorar el estado de salud\nd) Ninguna de las anteriores", "b"),
        ("riesgos", "pregunta", "2. ¿Qué acción corresponde a un análisis de trabajo seguro?\na) Operar maquinaria sin capacitación\nb) Identificar peligros y aplicar controles\nc) No usar arnés en alturas\nd) No hidratarse", "b"),
        ("aspectos", "info", "Aspectos ambientales: componentes de un producto, actividad o servicio que pueden interactuar o causar un efecto en el medio ambiente, como consumo de agua, energía o generación de residuos."),
        ("aspectos", "pregunta", "1. ¿Cuál es un ejemplo de aspecto ambiental?\na) Consumo de agua\nb) Consumo de energía\nc) Generación de residuos\nd) Todas las anteriores", "d"),
        ("aspectos", "pregunta", "2. ¿Un aspecto ambiental siempre es?\na) Algo que modifica directamente el ambiente\nb) Un componente de una actividad con posible interacción ambiental\nc) Un residuo específico\nd) Ninguna de las anteriores", "b"),
        ("impacto", "info", "Impacto ambiental: efecto real que el aspecto ambiental tiene sobre el medio. Ejemplo: contaminación del agua, no segregación de residuos, alto consumo de energía."),
        ("impacto", "pregunta", "1. ¿Qué es un impacto ambiental?\na) Una acción preventiva\nb) Un efecto real sobre el ambiente\nc) Un tipo de EPP\nd) Un comité de seguridad", "b"),
        ("impacto", "pregunta", "2. Un ejemplo de impacto ambiental es:\na) Uso de arnés\nb) No separar residuos\nc) Realizar pausas activas\nd) Hidratarse", "b"),
        ("procedimientos", "info", "Procedimientos seguros: trabajo seguro en alturas, permiso de trabajo y arnés para ascenso, atención de derrames, uso adecuado de EPP, aislamiento del área, análisis de compartimientos críticos."),
        ("procedimientos", "pregunta", "1. ¿Qué se requiere para trabajos en alturas (>2m)?\na) Permiso y uso de arnés\nb) Nada especial\nc) Solo casco\nd) Ninguna de las anteriores", "a"),
        ("procedimientos", "pregunta", "2. ¿Cuál es un procedimiento seguro en emergencias químicas?\na) Ignorar la fuga\nb) Usar EPP y aislar el área\nc) No reportar\nd) Correr sin control", "b"),
        ("comites", "info", "Comités: Comité de Seguridad y Salud en el Trabajo y Comité de Convivencia Laboral."),
        ("comites", "pregunta", "1. Una función del Comité de Seguridad y Salud en el Trabajo es:\na) Capacitar en seguridad\nb) Vender EPP\nc) Controlar inventarios\nd) Ninguna", "a"),
        ("comites", "pregunta", "2. Una función del Comité de Convivencia Laboral es:\na) Resolver conflictos laborales\nb) Controlar energía eléctrica\nc) Vigilar residuos químicos\nd) Comprar equipos", "a"),
        ("emergencias", "info", "Plan de emergencias: siga instrucciones del personal, diríjase al punto de encuentro, conserve la calma, evite celulares, porte documentos, apoye evacuaciones."),
        ("emergencias", "pregunta", "1. En caso de evacuación debe:\na) Correr y gritar\nb) Conservar la calma y dirigirse al punto de encuentro\nc) Usar el celular\nd) Esconderse", "b"),
        ("emergencias", "pregunta", "2. Función del personal en control vial:\na) Desordenar al personal\nb) Coordinar evacuación y verificar listado\nc) No hacer nada\nd) Usar celular", "b"),
        ("responsabilidades", "info", "Funciones y responsabilidades: apoyar limpieza y contención, usar EPP, reportar actos inseguros, no operar maquinaria sin capacitación, realizar estiramientos, garantizar hidratación y descanso."),
        ("responsabilidades", "pregunta", "1. Función de los trabajadores:\na) Reportar actos inseguros y usar EPP\nb) Operar equipos sin capacitación\nc) Ignorar su salud\nd) No hidratarse", "a"),
        ("responsabilidades", "pregunta", "2. Buena práctica de autocuidado:\na) Realizar estiramientos y descansar\nb) Evadir responsabilidades\nc) No usar EPP\nd) No reportar incidentes", "a"),
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
