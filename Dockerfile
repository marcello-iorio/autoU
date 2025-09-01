# Usa a imagem base do Python 3.11, que é compatível com suas bibliotecas
FROM python:3.11-slim

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala dependências do sistema (para o PyMuPDF)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todos os arquivos da sua aplicação
COPY app.py .
COPY meu_classificador_de_emails ./meu_classificador_de_emails
COPY dataset_emails_produtivo_improdutivo_15k.csv .
COPY index.html .
COPY src ./src

# Exponha a porta que o Cloud Run usa
EXPOSE 8080

# Comando final para iniciar o servidor Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]