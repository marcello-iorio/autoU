import os
import pandas as pd
from dotenv import load_dotenv
from google import genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from google.api_core.exceptions import ResourceExhausted
from transformers import pipeline
import fitz

# --- 1. CONFIGURAÇÃO INICIAL E CHAVE DE API ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    print("ERRO CRÍTICO: Variável de ambiente GOOGLE_API_KEY não encontrada.")
else:
    try:
        genarativeModel = genai.Client()
    except Exception as e:
        print(f"ERRO CRÍTICO: Chave de API do Gemini inválida. Erro: {e}")

app = Flask(__name__)
CORS(app)

MODEL_PATH = "./meu_classificador_de_emails"

# Lista de modelos para fallback
MODEL_FALLBACKS = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.5-pro"]

# --- 2. PREPARAÇÃO DA LISTA DE INTENÇÕES ---
def load_known_intents():
    try:
        df = pd.read_csv('dataset_emails_produtivo_improdutivo_15k.csv')
        df_produtivo = df[df['label'] == 'Produtivo']
        intents = df_produtivo['subject'].unique().tolist()
        print(f">>> Lista de {len(intents)} intenções conhecidas carregada com sucesso!")
        return intents
    except FileNotFoundError:
        print("ERRO: O arquivo 'dataset_emails_produtivo_improdutivo_15k.csv' não foi encontrado.")
        return []

known_intents = load_known_intents()

# --- 3. CARREGAMENTO DOS MODELOS DE IA ---
def load_classifier_model():
    try:
        classifier_pipeline = pipeline("text-classification", model=MODEL_PATH, device=-1)
        print(">>> Modelo classificador carregado com sucesso!")
        return classifier_pipeline
    except Exception as e:
        print(f"Ocorreu um erro ao carregar o modelo classificador: {e}")
        return None

classifier = load_classifier_model()
generative_model = genarativeModel

# --- Função auxiliar com fallback ---
def generate_with_fallback(prompt, model_list=MODEL_FALLBACKS):
    """
    Tenta gerar texto com uma lista de modelos em cascata.
    Se um der ResourceExhausted (código 429), tenta o próximo.
    """
    last_error = None
    for model in model_list:
        try:
            response = genarativeModel.models.generate_content(
                model=model,
                contents=prompt
            )
            return response.text.strip()
        except ResourceExhausted as e:
            print(f"[AVISO] Modelo {model} estourou a cota (429). Tentando próximo...")
            last_error = e
        except Exception as e:
            print(f"[ERRO] Modelo {model} falhou: {e}")
            last_error = e
    raise last_error

# --- 4. ENDPOINT DE ANÁLISE ---
@app.route('/analyze', methods=['POST'])
def analyze_email():
    if not all([classifier, genarativeModel, known_intents]):
        return jsonify({"error": "Um ou mais componentes de IA não estão carregados."}), 500

    email_text = ""

    if 'file' in request.files:
        file = request.files['file']
        if file.filename != '':
            filename = file.filename.lower()
            
            if filename.endswith('.pdf'):
                try:
                    with fitz.open(stream=file.read(), filetype="pdf") as pdf_document:
                        for page in pdf_document:
                            email_text += page.get_text()
                except Exception as e:
                    return jsonify({"error": f"Não foi possível ler o arquivo PDF. Pode estar corrompido. Erro: {str(e)}"}), 400

            elif filename.endswith('.txt'):
                try:
                    email_text = file.read().decode('utf-8')
                except Exception as e:
                    return jsonify({"error": f"Não foi possível ler o arquivo de texto. Erro: {str(e)}"}), 400
            else:
                return jsonify({"error": "Formato de arquivo não suportado. Por favor, envie .txt ou .pdf."}), 400
    
    elif request.is_json and 'text' in request.json:
        email_text = request.json.get('text')
    
    if not email_text.strip():
        return jsonify({"error": "O documento parece estar vazio ou não contém texto extraível."}), 400
    
    try:
        classification_result = classifier(email_text)[0]
        label_id = classification_result['label']
        category = "Produtivo" if label_id == 'LABEL_1' else "Improdutivo"

        if category == "Improdutivo":
            prompt = f"O e-mail a seguir foi classificado como improdutivo:\n\n---\n{email_text}\n---\n\nGere uma resposta curta e cordial de agradecimento em português do Brasil,com introdução,mas sem comentários."
        else:
            intent_prompt = f"""
            Analise o e-mail abaixo e diga a qual das seguintes intenções de negócio ele corresponde melhor:
            Lista de Intenções: {', '.join(known_intents)}
            --- E-MAIL ---
            {email_text}
            --- FIM DO E-MAIL ---
            Responda APENAS com o nome da intenção da lista. Se não corresponder a nenhuma, responda APENAS com a palavra "Outro".
            """
            detected_intent = generate_with_fallback(intent_prompt)

            if detected_intent != "Outro" and detected_intent in known_intents:
                prompt = f"""
                O e-mail recebido foi: --- {email_text} ---. A intenção foi classificada como '{detected_intent}'. Escreva uma resposta profissional e direta em português do Brasil que confirme o recebimento desta solicitação específica.
                Responda APENAS com o texto da resposta, com introdução, mas sem comentários.
                """
            else:
                prompt = f"""
                O e-mail recebido foi: --- {email_text} ---. A intenção foi classificada como 'Produtivo', mas não se encaixa em uma categoria conhecida. Escreva uma resposta profissional em português do Brasil, confirmando o recebimento e informando que o assunto será verificado pela equipe responsável.
                Responda APENAS com o texto da resposta, com introdução, mas sem comentários.
                """

        response_text = generate_with_fallback(prompt)
        
        return jsonify({
            "category": category,
            "response": response_text,
            "original_email": email_text
        })
    except Exception as e:
        return jsonify({"error": f"Ocorreu um erro interno: {str(e)}"}), 500

# --- ENDPOINT DE REFINAMENTO ---
@app.route('/refine', methods=['POST'])
def refine_response():
    data = request.json
    if not data or not all(k in data for k in ['original_email', 'draft_response']):
        return jsonify({"error": "Dados insuficientes para refinar a resposta."}), 400

    original_email = data['original_email']
    draft_response = data['draft_response']

    prompt = f"""
    Você é um assistente de comunicação profissional. Sua tarefa é gerar uma versão alternativa para uma resposta de e-mail.

    CONTEXTO:
    1.  **E-mail Original Recebido:**
        ---
        {original_email}
        ---

    2.  **Primeira Versão da Resposta (Rascunho):**
        ---
        {draft_response}
        ---

    TAREFA:
    Reescreva a "Primeira Versão da Resposta" de uma maneira diferente. Você pode, por exemplo, alterar o tom (deixar mais formal ou mais casual), mudar a estrutura da frase, ou usar palavras diferentes, mas mantendo o mesmo significado e objetivo.
    Responda APENAS com o texto da nova versão da resposta, com introdução, mas sem comentários como "aqui está uma alternativa".
    """
    try:
        refined_text = generate_with_fallback(prompt)
        print(">>> Resposta alternativa gerada com sucesso!")
        return jsonify({"refined_response": refined_text})
    except Exception as e:
        print(f"Ocorreu um erro durante o refinamento: {e}")
        return jsonify({"error": f"Ocorreu um erro interno ao refinar: {str(e)}"}), 500

# --- 5. EXECUÇÃO DO SERVIDOR ---
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
