import os, warnings, param
from google.cloud import bigquery
from langchain.chat_models import ChatOpenAI
from langchain.tools.render import format_tool_to_openai_function
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor
from dotenv import load_dotenv
from app.services.firestore_service import FirestoreChatMessageHistory
from app.services.langchain_memory import ConversationBufferMemory
from app.utils.bot_tools import tools


load_dotenv()


os.getenv('OPENAI_API_KEY')
warnings.filterwarnings('ignore')

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./key.json"
client = bigquery.Client()

openai_llm_model = os.getenv('OPENAI_LLM_MODEL')

class cbfs(param.Parameterized):
    def __init__(self, tools, **params):
        super(cbfs, self).__init__(**params)
        self.functions = [format_tool_to_openai_function(f) for f in tools]
        self.model = ChatOpenAI(temperature=0, model=os.getenv('OPENAI_LLM_MODEL')).bind(functions=self.functions)
        self.collection_name = os.getenv('FIRESTORE_COLLECTION_NAME')
        self.session_id = None
        self.user_id = None
        self.prompt = self.read_prompt_from_file()
        
        # Inicializar memoria con valores por defecto
        chat_history_obj = FirestoreChatMessageHistory(
            collection_name=self.collection_name,
            user_id='default',
            session_id='default'
        )
        self.memory = ConversationBufferMemory(
            return_messages=True, 
            memory_key="chat_history", 
            chat_memory=chat_history_obj
        )
        self.update_chain()

    def read_prompt_from_file(self) -> str:
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
    
    def update_phone_number(self, phone_number):
        """Actualiza el número de teléfono actual."""
        self.phone_number = phone_number

    def update_chain(self):
        self.chain = RunnablePassthrough.assign(
            agent_scratchpad=lambda x: format_to_openai_functions(x["intermediate_steps"])
        ) | ChatPromptTemplate.from_messages([
            ("system", self.prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ]) | self.model | OpenAIFunctionsAgentOutputParser()
        self.qa = AgentExecutor(agent=self.chain, tools=tools, verbose=False, memory=self.memory)
    
    def get_response(self, input, session_id=None, user_id=None):
        # Actualizar session_id y user_id si se proporcionan
        if session_id is not None and user_id is not None:
            self.update_session_and_user(session_id, user_id)
        
        # Leer y actualizar el prompt desde el archivo
        self.prompt = self.read_prompt_from_file()
        
        # Agregar el contenido de la lección al prompt si está disponible
        if hasattr(st.session_state, 'lesson_content'):
            self.prompt = self.prompt + f"\n\nContenido de la lección actual:\n{st.session_state.lesson_content}"
        
        self.update_chain()
        
        return self.qa.invoke({"input": input})['output']

    def update_session_and_user(self, new_session_id, new_user_id):
        # Actualiza siempre la sesión y el usuario
        self.session_id = new_session_id
        self.user_id = new_user_id

        # Crear nuevo objeto de historial de chat
        chat_history_obj = FirestoreChatMessageHistory(
            collection_name=self.collection_name,
            user_id=self.user_id,
            session_id=self.session_id,
            firestore_client=self.memory.chat_memory.firestore_client
        )
        
        # Crear nueva memoria con el nuevo historial
        self.memory = ConversationBufferMemory(
            return_messages=True, 
            memory_key="chat_history", 
            chat_memory=chat_history_obj
        )
        
        # Actualizar la cadena con la nueva memoria
        self.update_chain()

    def clr_history(self, count=0):
        self.chat_history = []
        return

def create_chat_agent():
    return cbfs(tools)