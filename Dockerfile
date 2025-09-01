# Etapa 1: Imagem Base
# Usamos uma imagem oficial do Python, versão "slim" para ser mais leve.
FROM python:3.10-slim

# Etapa 2: Diretório de Trabalho
# Define o diretório padrão dentro do contêiner para onde os comandos serão executados.
WORKDIR /app

# Etapa 3: Dependências do Sistema
# Instala bibliotecas do sistema operacional que o PyMuPDF (para ler PDFs) pode precisar.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Etapa 4: Dependências do Python
# Copia o requirements.txt primeiro para aproveitar o cache do Docker.
# Se este arquivo não mudar, o Docker não reinstalará tudo a cada build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Etapa 5: Copiar Arquivos da Aplicação
# Copia todos os componentes necessários do seu projeto para dentro do contêiner.
COPY app ./app
COPY meu_classificador_de_emails ./meu_classificador_de_emails
COPY dataset_emails_produtivo_improdutivo_15k.csv .

# Copia os arquivos de frontend que estão na raiz do projeto.
# Adicione ou remova linhas aqui conforme os arquivos que você tiver.
COPY index.html .
COPY src ./src
# COPY style.css .
# COPY script.js .

# Etapa 6: Expor a Porta
# Informa ao Docker que o contêiner escutará na porta 8080, padrão do Google Cloud Run.
EXPOSE 8080

# Etapa 7: Comando de Execução
# Inicia o servidor web Gunicorn para rodar a aplicação Flask em um ambiente de produção.
# --bind: Onde o servidor vai escutar (todas as interfaces, porta 8080).
# --workers/--threads: Configuração básica de performance.
# --timeout 0: Impede que o servidor desista em predições de modelo que possam ser demoradas.
# app.app:app: Sintaxe para encontrar o objeto Flask -> {pasta}.{arquivo}:{variável_app}
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app.app:app"]