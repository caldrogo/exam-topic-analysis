# Use a lightweight base Python image
FROM python:3.14-slim

# Set working directory inside the container
WORKDIR /app

# Prevent Python from writing bytecode and buffer logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy dependencies first to leverage Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy everything needed into the container
COPY app.py /app/
COPY data/dataset_full.csv /app/data/
COPY data/dataset_sample.csv /app/data/
COPY data/prompts.json /app/data/

COPY src/config.py /app/src/
COPY src/calculate_kappa.py /app/src/

# Expose Streamlit's default port
EXPOSE 8501

# Configure Streamlit to run headlessly
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Launch the Streamlit application
CMD ["streamlit", "run", "app.py"]