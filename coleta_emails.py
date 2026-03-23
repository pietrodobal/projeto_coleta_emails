"""
Projeto Coleta e Organização de Emails (Com Validação IA)
=========================================================
Script para coletar, validar com IA e organizar endereços de email.
Uso no Ubuntu:
    export GEMINI_API_KEY="sua_chave_aqui"
    python coleta_emails.py --url https://exemplo.com --ia
"""

import argparse
import csv
import os
import re
import sys
import time
from pathlib import Path

try:
    import google.generativeai as genai
except ImportError:
    genai = None

# ---------------------------------------------------------------------------
# Constantes e Configurações
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)
PASTA_SAIDA = "saida"

# ---------------------------------------------------------------------------
# Funções de Coleta e Contexto
# ---------------------------------------------------------------------------

def normalizar_email(email: str) -> str:
    return email.strip().lower()

def extrair_emails_com_contexto(texto: str) -> dict:
    """Extrai emails únicos e captura 80 caracteres ao redor para contexto da IA."""
    resultados = {}
    for match in EMAIL_REGEX.finditer(texto):
        email = normalizar_email(match.group(1))
        if email not in resultados:
            inicio = max(0, match.start() - 80)
            fim = min(len(texto), match.end() + 80)
            contexto = texto[inicio:fim].replace("\n", " ").strip()
            resultados[email] = contexto
    return resultados

def coletar_de_url(url: str) -> dict:
    """Faz o download da página e retorna um dicionário {email: contexto}."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("[ERRO] Instale as dependências: pip install -r requirements.txt", file=sys.stderr)
        return {}

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64)'}
        resposta = requests.get(url, headers=headers, timeout=15)
        resposta.raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERRO] Falha ao acessar '{url}': {exc}", file=sys.stderr)
        return {}

    soup = BeautifulSoup(resposta.text, "lxml")
    texto = soup.get_text(separator=" ")
    emails_com_contexto = extrair_emails_com_contexto(texto)
    
    print(f"[INFO] {len(emails_com_contexto)} email(s) bruto(s) encontrado(s) em '{url}'")
    return emails_com_contexto

# ---------------------------------------------------------------------------
# Validação com IA (Custo Zero)
# ---------------------------------------------------------------------------

def configurar_ia():
    chave = os.getenv("GEMINI_API_KEY")
    if not chave or not genai:
        print("[ERRO] Variável GEMINI_API_KEY não encontrada ou biblioteca ausente.", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=chave)
    # Modelo 2.5 Flash é ideal e gratuito no Google AI Studio
    return genai.GenerativeModel('gemini-2.5-flash')

def validar_com_ia(modelo, email: str, contexto: str) -> bool:
    prompt = f"""
    Analise o e-mail: {email}
    Contexto da página: {contexto}
    Este e-mail pertence a uma secretaria, departamento, diretoria ou docente das áreas de 
    Artes, Cinema, Letras, Sociologia, Filosofia ou Humanidades?
    Responda APENAS 'S' ou 'N'.
    """
    try:
        resposta = modelo.generate_content(prompt)
        time.sleep(1) # Pausa para respeitar o limite de requisições do plano gratuito
        return 'S' in resposta.text.upper()
    except Exception as e:
        print(f"[AVISO] Falha na IA para {email}: {e}", file=sys.stderr)
        return False

# ---------------------------------------------------------------------------
# Organização e Exportação
# ---------------------------------------------------------------------------

def salvar_csv(emails: list[str], caminho_saida: str) -> None:
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_completo = os.path.join(PASTA_SAIDA, caminho_saida)

    with open(caminho_completo, "w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.writer(arquivo_csv)
        escritor.writerow(["email_validado"])
        for email in emails:
            escritor.writerow([email])

    print(f"[INFO] {len(emails)} email(s) salvo(s) em '{caminho_completo}'")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Coleta e valida emails com IA.")
    parser.add_argument("--url", "-u", help="URL de uma página web para extrair emails.")
    parser.add_argument("--saida", "-s", default="emails_validados.csv", help="Arquivo CSV de saída.")
    parser.add_argument("--ia", action="store_true", help="Ativa o filtro de inteligência artificial.")
    return parser

def main() -> int:
    parser = construir_parser()
    args = parser.parse_args()

    if not args.url:
        parser.error("Informe uma URL com --url")

    emails_brutos = coletar_de_url(args.url)
    emails_aprovados = []

    if args.ia and emails_brutos:
        print("[INFO] Iniciando validação rigorosa com IA...")
        modelo_ia = configurar_ia()
        
        for email, contexto in emails_brutos.items():
            if validar_com_ia(modelo_ia, email, contexto):
                print(f"  [APROVADO] {email}")
                emails_aprovados.append(email)
            else:
                print(f"  [DESCARTADO] {email}")
    else:
        emails_aprovados = list(emails_brutos.keys())

    emails_aprovados.sort()
    
    print(f"\n{'='*50}\n  Total Aprovado: {len(emails_aprovados)}\n{'='*50}")
    if emails_aprovados:
        salvar_csv(emails_aprovados, args.saida)

    return 0

if __name__ == "__main__":
    sys.exit(main())
