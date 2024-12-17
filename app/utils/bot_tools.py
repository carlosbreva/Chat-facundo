import json, os
from langchain.tools import tool
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from google.cloud import bigquery

# Manejo de credenciales para Replit
if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
    # Si estamos en Replit, usar el secreto
    credentials_json = json.loads(os.environ['GOOGLE_APPLICATION_CREDENTIALITS'])
    with open('key.json', 'w') as f:
        json.dump(credentials_json, f)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
else:
    # Local development
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./key.json"

load_dotenv()


client = bigquery.Client()


class UserLevelRequest(BaseModel):
    dni: str = Field(..., description="El DNI del usuario para buscar el nivel de competencia en la base de datos.")

@tool
def handle_user_level_request(dni: str) -> str:
    """
    Esta función busca el nivel de competencia de un usuario por su DNI en la base de datos.
    """
    try:
        query = """
        SELECT DNI, NOMBRE, MATERIA
        FROM `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.PROFESORES`
        """
        data = client.query(query).to_dataframe()
        dni_filtered = data.loc[data['DNI'] == dni]
        
        if not dni_filtered.empty:
            return json.loads(dni_filtered.to_json(orient='records'))
        return 'No encontramos un usuario registrado con tu DNI'
    except Exception as e:
        return f"Error al procesar la solicitud: {str(e)}"


class LessonContentRequest(BaseModel):
    tema: int = Field(..., description="El número del tema para buscar el contenido del PDF.")
    leccion: str = Field(..., description="El título de la lección para buscar el contenido del PDF.")

@tool(args_schema=LessonContentRequest)
def handle_lesson_content_request(tema: int, leccion: str) -> str:
    """
    Esta función busca el contenido del PDF en BigQuery basado en el tema y la lección especificados.
    Args:
        tema (int): El número del tema
        leccion (str): El título de la lección
    """
    try:
        query = f"""
        SELECT informacion
        FROM `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.pdf_data`
        WHERE tema = {tema} AND leccion = @leccion
        LIMIT 1
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("leccion", "STRING", leccion)
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = query_job.result()

        for row in results:
            return row.informacion

        return "No se encontró un contenido correspondiente al tema y lección especificados."
    except Exception as e:
        return f"Error al procesar la solicitud: {str(e)}"


def get_available_lessons(tema: int) -> list:
    """
    Obtiene las lecciones disponibles para un tema específico.
    """
    query = f"""
    SELECT DISTINCT leccion
    FROM `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.pdf_data`
    WHERE tema = {tema}
    ORDER BY leccion
    """
    
    data = client.query(query).to_dataframe()
    if not data.empty:
        return [(leccion, leccion) for leccion in data['leccion']]
    return []


tools = [handle_user_level_request, handle_lesson_content_request]