"""
Projeto Coleta e Organização de Emails (Com Validação IA)
"""
import argparse
import csv
import importlib.util
import os
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

ARQUIVO_CREDENCIAIS_OCULTO = Path(__file__).with_name(".credenciais")
ARQUIVO_CREDENCIAIS_LEGADO = Path(__file__).with_name("credenciais")
if ARQUIVO_CREDENCIAIS_OCULTO.exists():
    load_dotenv(dotenv_path=ARQUIVO_CREDENCIAIS_OCULTO)
else:
    load_dotenv(dotenv_path=ARQUIVO_CREDENCIAIS_LEGADO)

try:
    import google.generativeai as genai
except ImportError:
    genai = None

def carregar_urls_importadas() -> list[str]:
    caminho_lista = Path(__file__).with_name("lista_urls.py")
    if not caminho_lista.exists():
        return []

    spec = importlib.util.spec_from_file_location("lista_urls", caminho_lista)
    if not spec or not spec.loader:
        return []

    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    urls = getattr(modulo, "urls", [])
    return urls if isinstance(urls, list) else []

urls_importadas = carregar_urls_importadas()

EMAIL_REGEX = re.compile(
    r"([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
    re.IGNORECASE,
)
PASTA_SAIDA = "saida"

def normalizar_email(email: str) -> str:
    return email.strip().lower()

def extrair_emails_com_contexto(texto: str) -> dict:
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
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {}

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64)'}
        resposta = requests.get(url, headers=headers, timeout=15)
        resposta.raise_for_status()
    except requests.RequestException:
        return {}

    soup = BeautifulSoup(resposta.text, "lxml")
    texto = soup.get_text(separator=" ")
    return extrair_emails_com_contexto(texto)

def configurar_ia():
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        print("GEMINI_API_KEY ausente no arquivo .credenciais/credenciais.", file=sys.stderr)
        sys.exit(1)

    if not genai:
        print("Pacote google-generativeai não instalado no ambiente atual.", file=sys.stderr)
        sys.exit(1)

    configure_fn = getattr(genai, "configure", None)
    model_cls = getattr(genai, "GenerativeModel", None)
    if not callable(configure_fn) or model_cls is None:
        print("Versão incompatível de google-generativeai no ambiente atual.", file=sys.stderr)
        sys.exit(1)

    configure_fn(api_key=chave)
    return model_cls('gemini-2.5-flash')

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
        time.sleep(1)
        return 'S' in resposta.text.upper()
    except Exception:
        return False

def salvar_csv(emails: list[str], caminho_saida: str) -> None:
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_completo = os.path.join(PASTA_SAIDA, caminho_saida)
    with open(caminho_completo, "w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.writer(arquivo_csv)
        escritor.writerow(["email_validado"])
        for email in emails:
            escritor.writerow([email])

def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta e valida emails com IA.")
    parser.add_argument("--url", "-u", help="URL específica para extração.")
    parser.add_argument("--lote", action="store_true", help="Usa a lista gerada em lista_urls.py")
    parser.add_argument("--saida", "-s", default="emails_validados.csv", help="Arquivo CSV de saída.")
    parser.add_argument("--ia", action="store_true", help="Ativa o filtro de IA.")
    args = parser.parse_args()

    urls_alvo = []
    if args.url:
        urls_alvo.append(args.url)
    elif args.lote:
        urls_alvo.extend(urls_importadas)
    else:
        parser.error("Informe --url ou --lote")

    emails_aprovados = []
    modelo_ia = configurar_ia() if args.ia else None

    for url in urls_alvo:
        emails_brutos = coletar_de_url(url)
        if not emails_brutos:
            continue
        
        if args.ia:
            for email, contexto in emails_brutos.items():
                if email not in emails_aprovados and validar_com_ia(modelo_ia, email, contexto):
                    emails_aprovados.append(email)
        else:
            for email in emails_brutos.keys():
                if email not in emails_aprovados:
                    emails_aprovados.append(email)

        if len(emails_aprovados) >= 400:
            break

    emails_aprovados.sort()
    if emails_aprovados:
        salvar_csv(emails_aprovados, args.saida)

    return 0

if __name__ == "__main__":
    sys.exit(main())