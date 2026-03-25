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

**Execução paralela em 2+ computadores (sharding):**
Quando duas máquinas rodam em paralelo, use shards para evitar que ambas processem as mesmas URLs da `lista_urls.py`.

```bash
# Máquina A (shard 0 de 2)
python coleta_emails.py --lote --ia --shard-count 2 --shard-index 0 --saida emails_validados_a.csv --saida-rejeitados rejeitados_ia_a.csv

# Máquina B (shard 1 de 2)
python coleta_emails.py --lote --ia --shard-count 2 --shard-index 1 --saida emails_validados_b.csv --saida-rejeitados rejeitados_ia_b.csv
```

Se quiser isolar completamente as saídas por máquina, defina `SAIDA_DIR` (ex.: `saida_faculdade`):

```bash
SAIDA_DIR=saida_faculdade python coleta_emails.py --lote --ia --shard-count 2 --shard-index 1
```

Depois, unifique os CSVs em uma máquina de consolidação (ou mantenha o fluxo de consolidação já existente no projeto).

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
cd "/workspaces/projeto_coleta_emails"

# iniciar monitoramento (reinicia ciclo_horario.sh se cair)
bash supervisor_noturno.sh start

# ver status do supervisor + ciclo
bash supervisor_noturno.sh status

# reiniciar supervisor
bash supervisor_noturno.sh restart

# parar supervisor
bash supervisor_noturno.sh stop
```

Opcional: ajustar frequência de checagem (padrão 30s):

```bash
CHECK_INTERVAL_SECONDS=30 bash supervisor_noturno.sh start
```

Opcional: executar em paralelo em 2 máquinas no fluxo noturno (sharding):

```bash
# Máquina A
SHARD_COUNT=2 SHARD_INDEX=0 bash supervisor_noturno.sh start

# Máquina B
SHARD_COUNT=2 SHARD_INDEX=1 bash supervisor_noturno.sh start
```

Com pasta separada para esta máquina:

```bash
SAIDA_DIR=saida_faculdade SHARD_COUNT=2 SHARD_INDEX=1 bash supervisor_noturno.sh start
```

Para rodar sem IA e manter um arquivo único com todos os e-mails encontrados:

```bash
SAIDA_DIR=saida_faculdade USAR_IA=0 SHARD_COUNT=2 SHARD_INDEX=1 bash supervisor_noturno.sh start
```

Padrão remoto recomendado (fora do computador de casa):

```bash
# iniciar com defaults remotos (sem IA, saida_faculdade, arquivo total)
bash supervisor_remoto.sh start

# status
bash supervisor_remoto.sh status

# parar
bash supervisor_remoto.sh stop
```

Defaults do modo remoto (`supervisor_remoto.sh` / `ciclo_remoto.sh`):

- `SAIDA_DIR=saida_faculdade`
- `USAR_IA=0`
- `LISTA_URLS_REL=saida_faculdade/lista_urls_faculdade.py`
- `EMAILS_TOTAL_REL=a_validar_faculdade.csv`
- `SHARD_COUNT=1` e `SHARD_INDEX=0` (pode sobrescrever)

Arquivo consolidado gerado automaticamente por ciclo:

- `saida_faculdade/a_validar_faculdade.csv` (somente emails ainda não validados)
- `saida_faculdade/ja_filtrados_faculdade.csv` (sincronizado a partir de `validados_faculdade.csv`)

Nesse modo, a pasta `saida_faculdade` passa a concentrar os resultados desta máquina, incluindo:

- `saida_faculdade/lista_urls_faculdade.py` (URLs encontradas da etapa de busca)
- `saida_faculdade/emails_validados.csv` e `saida_faculdade/Rejeitados.csv`
- `saida_faculdade/ciclos/*.csv` (arquivos por ciclo)

Para parar automaticamente em um horário e fazer commit/push em branch separada (sem usar `main`):

```bash
# agenda parada às 11:10 e publica resultados em branch própria
SAIDA_DIR=saida_faculdade bash agendar_parada_commit_branch.sh 11:10 results/saida_faculdade_hoje
```

Para respeitar horário local (ex.: Brasil), informe o fuso:

```bash
TARGET_TZ=America/Sao_Paulo SAIDA_DIR=saida_faculdade bash agendar_parada_commit_branch.sh 11:10 results/saida_faculdade_hoje
```

O script para o supervisor/ciclo local, gera `RELATORIO_MADRUGADA.md` com `--saida-dir`, comita apenas `SAIDA_DIR` + relatório e faz push para a branch informada.

Checagem rápida após merge (conflitos + comparação de resultados):

```bash
bash check_merge_rapido.sh
```

Logs do supervisor ficam em: `supervisor_noturno.log`.

### Scripts ativos do fluxo noturno

- `supervisor_noturno.sh`: monitora e reinicia automaticamente o ciclo.
- `ciclo_horario.sh`: orquestra coleta sem IA, coleta com IA, consolidação e busca de novas URLs.
- `auto_pos_coleta.sh`: consolida validados/rejeitados e mantém os arquivos de ciclo.

Para maximizar volume durante a madrugada, o ciclo usa busca de URLs ampliada e maior teto de e-mails por execução.

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