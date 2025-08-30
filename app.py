# --- SEÇÃO DE IMPORTAÇÕES ---
import os
import pandas as pd  # Importamos pandas para ler nosso arquivo CSV
from dotenv import load_dotenv
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import pipeline

# --- 1. CONFIGURAÇÃO INICIAL E CHAVE DE API ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("ERRO CRÍTICO: Variável de ambiente GOOGLE_API_KEY não encontrada.")
else:
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
    except Exception as e:
        print(f"ERRO CRÍTICO: Chave de API do Gemini inválida. Erro: {e}")

app = Flask(__name__)
CORS(app)

MODEL_PATH = "./meu_classificador_de_emails"

# --- 2. PREPARAÇÃO DA LISTA DE INTENÇÕES (A GRANDE MUDANÇA!) ---

def load_known_intents():
    """
    Esta função carrega o CSV, filtra os e-mails produtivos
    e cria uma lista de 'assuntos' (subjects) únicos que o Gemini usará como referência.
    """
    try:
        df = pd.read_csv('dataset_emails_produtivo_improdutivo_15k.csv')
        # Filtramos apenas os e-mails que são 'Produtivo'
        df_produtivo = df[df['label'] == 'Produtivo']
        # Pegamos a coluna 'subject' e criamos uma lista com os valores únicos.
        intents = df_produtivo['subject'].unique().tolist()
        print(f">>> Lista de {len(intents)} intenções conhecidas carregada com sucesso!")
        return intents
    except FileNotFoundError:
        print("ERRO: O arquivo 'dataset_emails_produtivo_improdutivo_15k.csv' não foi encontrado.")
        return []

# Carregamos a lista de intenções uma vez quando o servidor inicia.
known_intents = load_known_intents()

# --- 3. CARREGAMENTO DOS MODELOS DE IA ---
def load_classifier_model():
    """Carrega nosso modelo BERT treinado."""
    print("Carregando modelo classificador (BERT)...")
    if not os.path.exists(MODEL_PATH):
        print(f"ERRO: A pasta do modelo '{MODEL_PATH}' não foi encontrada.")
        return None
    try:
        classifier_pipeline = pipeline("text-classification", model=MODEL_PATH, device=-1)
        print(">>> Modelo classificador carregado com sucesso!")
        return classifier_pipeline
    except Exception as e:
        print(f"Ocorreu um erro ao carregar o modelo classificador: {e}")
        return None

def load_generative_model():
    """Configura o acesso ao Gemini."""
    print("Configurando modelo generativo (Gemini)...")
    if not GOOGLE_API_KEY: return None
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        print(">>> Modelo generativo pronto!")
        return model
    except Exception as e:
        print(f"Erro ao configurar o modelo generativo: {e}")
        return None

classifier = load_classifier_model()
generative_model = load_generative_model()

# --- 4. ENDPOINT DE ANÁLISE COM LÓGICA HÍBRIDA ---
@app.route('/analyze', methods=['POST'])
def analyze_email():
    if not all([classifier, generative_model, known_intents]):
        return jsonify({"error": "Um ou mais componentes de IA não estão carregados."}), 500

    data = request.json
    email_text = data.get('text')
    if not email_text:
        return jsonify({"error": "Nenhum texto de e-mail fornecido."}), 400

    try:
        # --- ETAPA 1: O PORTEIRO (BERT) FAZ A CLASSIFICAÇÃO INICIAL ---
        classification_result = classifier(email_text)[0]
        label_id = classification_result['label']
        category = "Produtivo" if label_id == 'LABEL_1' else "Improdutivo"
        print(f"BERT classificou como: '{category}'")

        # --- LÓGICA CONDICIONAL ---
        if category == "Improdutivo":
            # Se for improdutivo, a lógica é simples.
            print("Intenção: Improdutivo. Gerando resposta simples.")
            prompt = f"O e-mail a seguir foi classificado como improdutivo (um elogio, convite, etc.):\n\n---\n{email_text}\n---\n\nGere uma resposta curta e cordial de agradecimento em português do Brasil."
        
        else: # Se a categoria for "Produtivo"...
            # --- ETAPA 2: O DETETIVE (GEMINI) IDENTIFICA A INTENÇÃO ESPECÍFICA ---
            print("Intenção: Produtivo. Pedindo ao Gemini para identificar a sub-categoria...")
            
            # Criamos um prompt para que o Gemini faça uma segunda classificação.
            intent_prompt = f"""
            Analise o e-mail abaixo e diga a qual das seguintes intenções de negócio ele corresponde melhor:
            Lista de Intenções: {', '.join(known_intents)}

            --- E-MAIL ---
            {email_text}
            --- FIM DO E-MAIL ---

            Responda APENAS com o nome da intenção da lista. Se não corresponder a nenhuma, responda APENAS com a palavra "Outro".
            """
            intent_response = generative_model.generate_content(intent_prompt)
            detected_intent = intent_response.text.strip()
            print(f"Gemini detectou a intenção como: '{detected_intent}'")

            # --- ETAPA 3: O REDATOR (GEMINI) GERA A RESPOSTA CONTEXTUAL ---
            if detected_intent != "Outro" and detected_intent in known_intents:
                # Se encontramos uma intenção conhecida, o prompt é super específico.
                prompt = f"""
                Um e-mail foi recebido e classificado com a intenção específica de: **{detected_intent}**.
                O conteúdo do e-mail é:\n\n---\n{email_text}\n---\n\nEscreva uma resposta profissional e direta em português do Brasil que confirme o recebimento desta solicitação específica.
                """
            else:
                # Se a intenção é nova ou desconhecida ("Outro"), usamos o fallback que você queria.
                prompt = f"""
                Um e-mail foi classificado como 'Produtivo', mas não se encaixa em nenhuma categoria de solicitação conhecida. O conteúdo é:\n\n---\n{email_text}\n---\n\nUse sua inteligência geral para escrever uma resposta profissional em português do Brasil, confirmando o recebimento e informando que o assunto será verificado pela equipe responsável.
                """

        # Finalmente, geramos a resposta final com o prompt que foi escolhido.
        final_response = generative_model.generate_content(prompt)
        response_text = final_response.text

        print(">>> Resposta final gerada com sucesso!")
        return jsonify({
            "category": category, # A categoria principal do BERT
            "response": response_text.strip()
        })

    except Exception as e:
        print(f"Ocorreu um erro durante a análise: {e}")
        return jsonify({"error": f"Ocorreu um erro interno: {str(e)}"}), 500


# O endpoint /refine continua o mesmo...
@app.route('/refine', methods=['POST'])
def refine_response():
    # ... (código do refine) ...
    pass


# --- 5. EXECUÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)