import streamlit as st
from urllib.parse import parse_qs

st.set_page_config(layout='wide')

# Obtener parámetros de la URL usando st.query_params
tema_param = st.query_params.get('tema', None)

import os
from app.utils.bot import create_chat_agent
from google.cloud import bigquery
from app.utils.bot_tools import handle_user_level_request, get_available_lessons, handle_lesson_content_request, LessonContentRequest

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./key.json"

client = bigquery.Client()

# Función para leer el prompt desde el archivo
def read_prompt_from_file() -> str:
        """
        Esta función lee el prompt desde la tabla de BigQuery.
        """
        client = bigquery.Client()

        # Query para obtener el prompt
        query = """
        SELECT prompt
        FROM `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.prompts`
        LIMIT 1
        """

        query_job = client.query(query)  # Ejecuta la consulta
        results = query_job.result()     # Obtiene los resultados

        # Extrae el prompt si existe
        for row in results:
            return row.prompt

        return "No se encontró ningún prompt en la tabla."

# Inicializar todos los estados necesarios
if "is_authenticated" not in st.session_state:
    st.session_state.is_authenticated = False
    st.session_state.welcomed = False
    st.session_state.user_dni = None
    st.session_state.user_info = None
    st.session_state.messages = []

# Inicializar el agente solo si no existe y el usuario está autenticado
if "agent" not in st.session_state and st.session_state.is_authenticated:
    agent = create_chat_agent()
    if st.session_state.user_dni:  # Asegurarse de que tenemos el DNI
        agent.update_session_and_user(st.session_state.user_dni, st.session_state.user_dni)
    st.session_state.agent = agent

if not st.session_state.is_authenticated:
    st.title("Verificación de DNI")
    dni = st.text_input("Por favor, ingrese su DNI para continuar:")
    
    if st.button("Verificar"):
        result = handle_user_level_request(dni)
        if isinstance(result, str) and result == 'No encontramos un usuario registrado con tu DNI':
            st.error("DNI no autorizado. Por favor, verifique su DNI.")
        else:
            st.session_state.is_authenticated = True
            st.session_state.user_dni = dni
            st.session_state.user_info = result[0]
            st.rerun()
else:
    # Agregar selección de tema y lección antes de iniciar el chat
    if "lesson_selected" not in st.session_state:
        st.title("Selección de Tema y Lección")
        
        # Mostrar información del usuario
        if "user_info" in st.session_state:
            user_info = st.session_state.user_info
            st.markdown(f"**Profesor:** {user_info.get('NOMBRE', 'No disponible')}")
            st.markdown(f"**Materia:** {user_info.get('MATERIA', 'No disponible')}")
        
        # Selector de tema - usar el parámetro de la URL si existe
        if tema_param in ['1', '2']:
            tema = tema_param
            st.markdown(f"**Tema seleccionado:** {tema}")
        else:
            tema = st.selectbox("Seleccione el tema:", ["1", "2"])
        
        if tema:
            lecciones = get_available_lessons(int(tema))
            if lecciones:
                # Mostrar los títulos de las lecciones en el selectbox
                leccion_selected = st.selectbox("Seleccione la lección:", [titulo for _, titulo in lecciones])
                
                if st.button("Comenzar Chat"):
                    try:
                        # Guardar la información de tema y lección sin cargar el contenido aún
                        st.session_state.lesson_selected = True
                        st.session_state.tema_selected = tema
                        st.session_state.leccion_selected = leccion_selected
                        
                        # Crear e inicializar el agente
                        if "agent" not in st.session_state:
                            agent = create_chat_agent()
                            agent.update_session_and_user(st.session_state.user_dni, st.session_state.user_dni)
                            st.session_state.agent = agent
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al inicializar el chat: {str(e)}")
            else:
                st.warning(f"No hay lecciones disponibles para el tema {tema}")
    else:
        # Mostrar la interfaz del chat solo si hay una lección seleccionada
        if "lesson_selected" in st.session_state and st.session_state.lesson_selected:
            # Título de la aplicación Streamlit
            st.title("Agente IA")
            
            # Mostrar información del usuario y mensaje de bienvenida
            if "user_info" in st.session_state:
                user_info = st.session_state.user_info
                st.sidebar.markdown("### Información del Profesor")
                st.sidebar.markdown(f"**Nombre:** {user_info.get('NOMBRE', 'No disponible')}")
                st.sidebar.markdown(f"**Materia:** {user_info.get('MATERIA', 'No disponible')}")
                st.sidebar.markdown(f"**Tema:** {st.session_state.tema_selected}")
                st.sidebar.markdown(f"**Lección:** {st.session_state.leccion_selected}")
                
                # Mostrar mensaje de bienvenida con la lección seleccionada
                if not st.session_state.welcomed:
                    welcome_message = {
                        "role": "assistant",
                        "content": (
                            f"¡Bienvenido/a Profesor/a {user_info.get('NOMBRE', '')}! "
                            f"Estamos revisando el Tema {st.session_state.tema_selected}, "
                            f"Lección {st.session_state.leccion_selected}. "
                            "¿En qué puedo ayudarte?"
                        )
                    }
                    st.session_state.messages = [welcome_message]
                    st.session_state.welcomed = True
                    st.rerun()

            # Mostrar botón de cerrar sesión
            if st.sidebar.button("Cerrar Sesión"):
                # Limpiar estados
                for key in ['is_authenticated', 'messages', 'welcomed', 'user_info', 'agent', 'user_dni', 'lesson_selected', 'lesson_content']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
            
            session_id = st.session_state.user_dni
            user_id = st.session_state.user_dni

            # Initialize chat history
            if "messages" not in st.session_state:
                st.session_state.messages = []

            # Display chat messages from history on app rerun
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            # React to user input
            if user_input := st.chat_input("A preguntar"):
                try:
                    # Cargar el contenido de la lección si aún no está cargado
                    if "lesson_content" not in st.session_state:
                        tema = int(st.session_state.tema_selected)
                        leccion = st.session_state.leccion_selected
                        st.session_state.lesson_content = handle_lesson_content_request(
                            tema=tema,
                            leccion=leccion
                        )
                        
                        # Actualizar el prompt del agente con el nuevo contenido
                        if st.session_state.lesson_content:
                            st.session_state.agent.prompt = (
                                st.session_state.agent.prompt + 
                                f"\n\nContenido de la lección actual:\n{st.session_state.lesson_content}"
                            )
                            st.session_state.agent.update_chain()

                    # Display user message in chat message container
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    
                    # Add user message to chat history
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                    response = st.session_state.agent.get_response(user_input, session_id, user_id)
                    with st.chat_message("assistant"):
                        st.write(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    st.error(f"Error al procesar la respuesta: {str(e)}")
                    st.session_state.agent = None
                    st.rerun()
        else:
            st.warning("Por favor, selecciona una lección antes de comenzar el chat.")
            st.title("Selección de Tema y Lección")
            # ... resto del código de selección de tema y lección ...
