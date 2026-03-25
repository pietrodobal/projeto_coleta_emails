# 📧 Extrator e Curador de E-mails com Validação de IA (Gemini API)

Script Python avançado para **coleta**, **filtragem semântica** e **organização** de endereços de e-mail a partir de páginas web. 

Estruturado para mineração de contatos altamente qualificados (como prospecção em diretórios acadêmicos da América Latina), o projeto utiliza expressões regulares (Regex) aliadas à Inteligência Artificial para eliminar "ruído" (e-mails genéricos, suporte, alunos) e reter apenas perfis decisores com base no contexto em que o e-mail aparece na página.

---

## 📋 Funcionalidades

- **Web Scraping de Precisão:** Extração de e-mails e captura automática do contexto adjacente no DOM (80 caracteres) para análise.
- **Validação Semântica via LLM:** Integração com a API do Google Gemini (2.5 Flash) para classificar e aprovar contatos com base no texto ao redor do e-mail.
- **Controle de Custos e API Limits:** Função de deduplicação na memória antes da chamada da API e delay estrutural (`time.sleep`) para viabilizar a execução integral no plano gratuito (Free Tier).
- **Modo Dry-run:** Capacidade de rodar a extração bruta para auditar as expressões regulares sem acionar a IA, poupando tokens.
- **Exportação Limpa:** Geração de arquivo CSV padronizado e livre de duplicatas.

---

## 🚀 Como usar no ambiente Linux (Ubuntu)

### 1. Preparação do Ambiente

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/projeto_coleta_emails.git
cd projeto_coleta_emails

# Crie e ative um ambiente virtual isolado
python3 -m venv venv
source venv/bin/activate

# Instale as dependências
pip install -r requirements.txt
```

### 2. Configuração da API (Gratuita)

Para utilizar o filtro inteligente, obtenha uma chave no [Google AI Studio](https://aistudio.google.com/) e exporte-a como variável de ambiente no seu terminal. Isso evita expor credenciais no código-fonte.

```bash
export GEMINI_API_KEY="sua_chave_aqui"
```

### 3. Execução

**Extração com Validação de IA (Recomendado):**
O script fará o scraping, extrairá o contexto de cada e-mail e fará a requisição para o LLM classificar a validade do contato.
```bash
python coleta_emails.py --url "https://www.exemplo.edu.br/diretorio" --ia
```

**Extração Bruta (Modo de Teste):**
Extrai e consolida todos os e-mails e contextos encontrados na página e exibe no terminal, sem realizar requisições externas para o Gemini.
```bash
python coleta_emails.py --url "https://www.exemplo.edu.br/diretorio"
```

Os contatos validados serão gerados no diretório de saída: `saida/emails_validados.csv`.

---

## 🌙 Execução contínua durante a noite (autorestart)

Para manter o pipeline rodando enquanto você dorme, use o supervisor:

```bash
cd "/home/pietro/projetos pessoais/coleta_e_organizacao_de_emails/projeto_coleta_emails"

# iniciar monitoramento (reinicia ciclo_horario.sh se cair)
bash supervisor_noturno.sh start

# ver status do supervisor + ciclo
bash supervisor_noturno.sh status

# reiniciar supervisor
bash supervisor_noturno.sh restart

# parar supervisor
bash supervisor_noturno.sh stop
```

Opcional: ajustar frequência de checagem (padrão 60s):

```bash
CHECK_INTERVAL_SECONDS=30 bash supervisor_noturno.sh start
```

Logs do supervisor ficam em: `supervisor_noturno.log`.

---

## 🗂️ Estrutura do Projeto

```text
projeto_coleta_emails/
├── coleta_emails.py         # Script de scraping e integração com Gemini
├── tests_coleta_emails.py   # Suíte de testes com simulação (Mocks) de IA
├── requirements.txt         # Dependências (requests, bs4, google-generativeai)
├── .gitignore               # Oculta venv, chaves exportadas e artefatos de saída
└── README.md                # Documentação
```

---

## 🛠️ Tecnologias e Bibliotecas

- **Python 3.10+**
- `google-generativeai` — Integração com LLM para Processamento de Linguagem Natural e classificação binária.
- `BeautifulSoup4` & `requests` — Extração de DOM HTML e requisições HTTP seguras.
- `re` & `csv` — Expressões regulares nativas e manipulação de planilhas.
- `pytest` & `unittest.mock` — Cobertura de testes unitários isolados, sem consumo de rede ou cota de API.

---

## 👨‍💻 Autor

Desenvolvido por **Pietro Baldo** — Estudante de Engenharia de Computação e QA.
Construído com foco em eficiência, testes de qualidade e integração de IA a custo zero para automação de processos de Data Mining.