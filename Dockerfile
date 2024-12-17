# Usa una imagen base de Python
FROM python:3.11

# Copia todo el contenido del directorio actual al directorio de trabajo
COPY . .

# Instala las dependencias
RUN pip install --no-cache-dir -r requirements.txt


ENV TZ=America/Argentina/Buenos_Aires
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


CMD streamlit run inicio.py