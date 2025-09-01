# Auto U - Assistente Inteligente de E-mails

Este projeto é uma aplicação web que utiliza inteligência artificial para analisar o conteúdo de e-mails, classificá-los como produtivos ou improdutivos e gerar respostas automáticas e contextuais.

## Funcionalidades

* **Classificação de E-mails:** Utiliza um modelo de Machine Learning (Hugging Face Transformers) para determinar se um e-mail é produtivo ou improdutivo.
* **Identificação de Intenção:** Para e-mails produtivos, um modelo de linguagem generativo (Google Gemini) identifica a intenção de negócio com base em uma lista pré-definida.
* **Geração de Respostas:** Cria respostas automáticas e coerentes com base na classificação e na intenção detectada.
* **Processamento de Arquivos:** Aceita e-mails em formato de texto puro (`.txt`), PDF (`.pdf`) ou texto direto via API.

## Como Executar Localmente

Siga os passos abaixo para configurar e executar a aplicação no seu ambiente de desenvolvimento.

### Pré-requisitos

Antes de começar, garanta que você tenha os seguintes softwares instalados:
* [Python 3.11+](https://www.python.org/downloads/)
* [pip](https://pip.pypa.io/en/stable/installation/) (geralmente instalado com o Python)
* [Git](https://git-scm.com/downloads/)

### 1. Clonar o Repositório

Primeiro, clone este repositório para a sua máquina local.
```bash
git clone [https://github.com/marcello-iorio/autoU.git](https://github.com/marcello-iorio/autoU.git)
cd autoU
```

### 2. Configurar o Ambiente Virtual

É uma boa prática usar um ambiente virtual para isolar as dependências do projeto.

```bash
# Criar o ambiente virtual
python -m venv venv

# Ativar o ambiente virtual
# No Windows:
venv\Scripts\activate
# No macOS/Linux:
source venv/bin/activate
```

### 3. Instalar as Dependências

Com o ambiente virtual ativo, instale todas as bibliotecas necessárias que estão listadas no arquivo `requirements.txt`.

```bash
pip install -r requirements.txt
```

### 4. Configurar a Chave de API

A aplicação precisa de uma chave de API para o Google Gemini. Você precisará criar um arquivo de ambiente para armazená-la de forma segura.

1.  Crie um arquivo chamado `.env` na raiz do projeto.
2.  Dentro deste arquivo, adicione a seguinte linha, substituindo `SUA_CHAVE_API_AQUI` pela sua chave real:
    ```
    GOOGLE_API_KEY=SUA_CHAVE_API_AQUI
    ```

### 5. Executar a Aplicação

Agora que tudo está configurado, inicie o servidor Flask:

```bash
python app.py
```

Se tudo correu bem, você verá uma mensagem indicando que o servidor está rodando, incluindo os logs de carregamento do modelo e das intenções. A aplicação estará acessível em `http://127.0.0.1:5000`.

## Como Usar a API

A aplicação expõe dois endpoints principais: `/analyze` e `/refine`.

### Endpoint `/analyze`

Este é o endpoint principal para analisar um e-mail.

#### **Enviando texto puro (JSON):**

```bash
curl -X POST -H "Content-Type: application/json" \
-d '{"text": "Prezados, gostaria de solicitar um orçamento para o projeto X. Seguem os detalhes em anexo."}' \
[http://127.0.0.1:5000/analyze](http://127.0.0.1:5000/analyze)
```

#### **Enviando um arquivo (.pdf ou .txt):**

```bash
curl -X POST -F "file=@/caminho/para/seu/arquivo.pdf" [http://127.0.0.1:5000/analyze](http://127.0.0.1:5000/analyze)
```

**Resposta de Exemplo:**
```json
{
  "category": "Produtivo",
  "original_email": "Prezados, gostaria de solicitar um orçamento para o projeto X. Seguem os detalhes em anexo.",
  "response": "Prezados, recebemos sua solicitação de orçamento para o projeto X e em breve nossa equipe entrará em contato com mais detalhes. Atenciosamente."
}
```