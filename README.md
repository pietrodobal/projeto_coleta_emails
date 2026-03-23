# 📧 Projeto Coleta e Organização de Emails

Script Python para **coletar**, **validar** e **organizar** endereços de email a partir de arquivos de texto, arquivos CSV e páginas web.

---

## 📋 Funcionalidades

- Extração de emails de arquivos **TXT** e **CSV**
- Extração de emails de **páginas web** via web scraping
- **Validação** de formato de email com expressão regular
- **Normalização** (conversão para minúsculas, remoção de espaços)
- **Remoção de duplicatas**
- **Ordenação** alfabética
- Exportação do resultado em **CSV**

---

## 🚀 Como usar

### 1. Clone o repositório

```bash
git clone https://github.com/pietrodobal/projeto_coleta_emails.git
cd projeto_coleta_emails
```

### 2. Instale as dependências

```bash
pip install -r requirements.txt
```

### 3. Execute o script

**A partir de um arquivo:**
```bash
python coleta_emails.py --arquivo entrada.txt --saida emails.csv
```

**A partir de uma URL:**
```bash
python coleta_emails.py --url https://exemplo.com --saida emails.csv
```

**Combinando arquivo e URL:**
```bash
python coleta_emails.py --arquivo entrada.txt --url https://exemplo.com --saida resultado.csv
```

O arquivo de saída será salvo na pasta `saida/`.

---

## 🗂️ Estrutura do projeto

```
projeto_coleta_emails/
├── coleta_emails.py         # Script principal
├── tests_coleta_emails.py   # Testes automatizados (pytest)
├── requirements.txt         # Dependências do projeto
├── .gitignore               # Arquivos ignorados pelo Git
└── README.md                # Este arquivo
```

---

## 🧪 Testes

Os testes cobrem extração, validação, normalização, organização e exportação de emails.

```bash
pip install pytest
python -m pytest tests_coleta_emails.py -v
```

---

## 📦 Dependências

| Pacote          | Uso                                      |
|-----------------|------------------------------------------|
| `requests`      | Requisições HTTP para coleta via URL     |
| `beautifulsoup4`| Parser HTML para extração de texto       |
| `lxml`          | Backend eficiente para o BeautifulSoup   |

> **Nota:** As dependências `requests`, `beautifulsoup4` e `lxml` são necessárias apenas para coleta via URL. A coleta a partir de arquivos locais não requer instalação adicional.

---

## 💡 Exemplo de saída

```
[INFO] 5 email(s) encontrado(s) em 'entrada.txt'

==================================================
  Total de emails únicos e válidos: 4
==================================================
  • admin@portal.org
  • marketing@empresa.com.br
  • suporte@empresa.com
  • vendas@empresa.com
==================================================

[INFO] 4 email(s) salvo(s) em 'saida/emails.csv'
```

---

## 🛠️ Tecnologias

- **Python 3.10+**
- `re` — expressões regulares (stdlib)
- `csv` — leitura e escrita de CSV (stdlib)
- `argparse` — interface de linha de comando (stdlib)
- `requests` + `BeautifulSoup4` — web scraping

---

## 👨‍💻 Autor

Desenvolvido por **Pietro Dobal** como projeto freelancer de coleta e organização de emails.
