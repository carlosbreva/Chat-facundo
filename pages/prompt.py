import streamlit as st
import os
from google.cloud import bigquery

# Set up Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./key.json"

# Initialize the BigQuery client
client = bigquery.Client()

# Function to read the prompt from BigQuery
def read_prompt_from_bigquery():
    query = """
    SELECT prompt
    FROM `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.prompts`
    LIMIT 1
    """
    query_job = client.query(query)
    results = query_job.result()
    for row in results:
        return row.prompt
    return "No se encontró ningún prompt en la tabla."

# Function to delete the existing prompt in BigQuery
def delete_existing_prompt():
    query = """
    DELETE FROM `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.prompts`
    WHERE TRUE
    """
    client.query(query)  # Execute the delete query

# Function to insert the new prompt in BigQuery
def insert_new_prompt(new_prompt):
    query = """
    INSERT INTO `celtic-music-441416-i1.AGENTE_IA_CONTENIDOS.prompts` (prompt)
    VALUES (@new_prompt)
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("new_prompt", "STRING", new_prompt)
        ]
    )
    client.query(query, job_config=job_config)  # Execute the insert query

# Streamlit UI
st.title("Gestión del Prompt Agente IA contenidos")

# Read and display the current prompt
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = read_prompt_from_bigquery()

new_prompt = st.text_area("Edita el Prompt", value=st.session_state.current_prompt, height=400)

# Update button
if st.button("Actualizar Prompt"):
    delete_existing_prompt()  # Delete the existing prompt
    insert_new_prompt(new_prompt)  # Insert the new prompt
    st.session_state.current_prompt = new_prompt  # Update the session state
    st.success("El prompt se ha actualizado exitosamente en BigQuery.")
