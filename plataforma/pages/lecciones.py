import streamlit as st
import os
from google.cloud import bigquery
from PyPDF2 import PdfReader

# Set up Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./key.json"

# Initialize the BigQuery client
client = bigquery.Client()

# Function to extract text from a PDF file
def extract_text_from_pdf(file):
    reader = PdfReader(file)
    content = ""
    for page in reader.pages:
        content += page.extract_text()
    return content

# Function to insert file information into BigQuery
def insert_file_info(tema, leccion, file_content):
    query = """
    INSERT INTO `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.pdf_data` (tema, leccion, informacion)
    VALUES (@tema, @leccion, @informacion)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("tema", "INT64", tema),
            bigquery.ScalarQueryParameter("leccion", "INT64", leccion),
            bigquery.ScalarQueryParameter("informacion", "STRING", file_content)
        ]
    )
    client.query(query, job_config=job_config)
    st.success("La información del documento se ha agregado a BigQuery exitosamente.")

# Streamlit UI
st.title("Subir Lecciones")

# Input fields for tema and leccion
tema = st.text_input("Número de Tema", value="", help="Ingresa el número de tema (debe ser un número entero)")
leccion = st.text_input("Número de Lección", value="", help="Ingresa el número de lección (debe ser un número entero)")

# File uploader
file = st.file_uploader("Subir Archivo PDF", type=["pdf"])

# Process the file if uploaded
if file is not None:
    file_content = extract_text_from_pdf(file)  # Extract text from the PDF
    st.write("Contenido del archivo cargado:", file_content[:500])  # Display a preview of the file content

    # Button to insert the file content into BigQuery
    if st.button("Agregar a BigQuery"):
        if tema.isdigit() and leccion.isdigit():
            insert_file_info(int(tema), int(leccion), file_content)
        else:
            st.error("Por favor, ingresa números válidos para tema y lección.")
