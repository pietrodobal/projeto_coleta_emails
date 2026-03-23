"""
Projeto Coleta e Organização de Emails
========================================
Script para coletar, validar e organizar endereços de email
a partir de diversas fontes: arquivos de texto, CSV e páginas web.

Uso:
    python coleta_emails.py --arquivo entrada.txt --saida emails.csv
    python coleta_emails.py --url https://exemplo.com --saida emails.csv
    python coleta_emails.py --arquivo entrada.txt --url https://exemplo.com --saida resultado.csv
"""

import argparse
import csv
import os
import re
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    re.IGNORECASE,
)

PASTA_SAIDA = "saida"


# ---------------------------------------------------------------------------
# Funções auxiliares
# ---------------------------------------------------------------------------

def extrair_emails_de_texto(texto: str) -> list[str]:
    """Extrai todos os endereços de email encontrados em uma string de texto."""
    return EMAIL_REGEX.findall(texto)


def validar_email(email: str) -> bool:
    """Retorna True se o endereço de email for válido."""
    return bool(EMAIL_REGEX.fullmatch(email.strip()))


def normalizar_email(email: str) -> str:
    """Converte o email para minúsculas e remove espaços nas bordas."""
    return email.strip().lower()


# ---------------------------------------------------------------------------
# Fontes de coleta
# ---------------------------------------------------------------------------

def coletar_de_arquivo(caminho: str) -> list[str]:
    """Lê um arquivo (TXT ou CSV) e extrai todos os emails encontrados."""
    path = Path(caminho)
    if not path.exists():
        print(f"[ERRO] Arquivo não encontrado: {caminho}", file=sys.stderr)
        return []

    try:
        conteudo = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        print(f"[ERRO] Não foi possível ler o arquivo: {exc}", file=sys.stderr)
        return []

    emails = extrair_emails_de_texto(conteudo)
    print(f"[INFO] {len(emails)} email(s) encontrado(s) em '{caminho}'")
    return emails


def coletar_de_url(url: str) -> list[str]:
    """Faz o download de uma página web e extrai todos os emails encontrados."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print(
            "[ERRO] Dependências 'requests' e 'beautifulsoup4' são necessárias para "
            "coleta via URL. Execute: pip install -r requirements.txt",
            file=sys.stderr,
        )
        return []

    try:
        resposta = requests.get(url, timeout=15)
        resposta.raise_for_status()
    except requests.RequestException as exc:
        print(f"[ERRO] Falha ao acessar a URL '{url}': {exc}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resposta.text, "lxml")
    texto = soup.get_text(separator=" ")
    emails = extrair_emails_de_texto(texto)
    print(f"[INFO] {len(emails)} email(s) encontrado(s) em '{url}'")
    return emails


# ---------------------------------------------------------------------------
# Organização e exportação
# ---------------------------------------------------------------------------

def organizar_emails(emails_brutos: list[str]) -> list[str]:
    """
    Normaliza, valida e remove duplicatas da lista de emails.
    Retorna a lista ordenada alfabeticamente.
    """
    vistos: set[str] = set()
    resultado: list[str] = []

    for email in emails_brutos:
        email_normalizado = normalizar_email(email)
        if validar_email(email_normalizado) and email_normalizado not in vistos:
            vistos.add(email_normalizado)
            resultado.append(email_normalizado)

    resultado.sort()
    return resultado


def salvar_csv(emails: list[str], caminho_saida: str) -> None:
    """Salva a lista de emails em um arquivo CSV com cabeçalho."""
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    caminho_completo = os.path.join(PASTA_SAIDA, caminho_saida)

    with open(caminho_completo, "w", newline="", encoding="utf-8") as arquivo_csv:
        escritor = csv.writer(arquivo_csv)
        escritor.writerow(["email"])
        for email in emails:
            escritor.writerow([email])

    print(f"[INFO] {len(emails)} email(s) salvo(s) em '{caminho_completo}'")


def exibir_resumo(emails: list[str]) -> None:
    """Exibe um resumo dos emails coletados no terminal."""
    if not emails:
        print("\n[AVISO] Nenhum email válido foi encontrado.")
        return

    print(f"\n{'='*50}")
    print(f"  Total de emails únicos e válidos: {len(emails)}")
    print(f"{'='*50}")
    for email in emails:
        print(f"  • {email}")
    print(f"{'='*50}\n")


# ---------------------------------------------------------------------------
# Interface de linha de comando
# ---------------------------------------------------------------------------

def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Coleta e organiza endereços de email a partir de arquivos e URLs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--arquivo", "-a",
        metavar="CAMINHO",
        help="Caminho para um arquivo TXT ou CSV contendo emails.",
    )
    parser.add_argument(
        "--url", "-u",
        metavar="URL",
        help="URL de uma página web para extrair emails.",
    )
    parser.add_argument(
        "--saida", "-s",
        metavar="ARQUIVO",
        default="emails_coletados.csv",
        help="Nome do arquivo CSV de saída (padrão: emails_coletados.csv).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = construir_parser()
    args = parser.parse_args(argv)

    if not args.arquivo and not args.url:
        parser.error("Informe ao menos uma fonte: --arquivo ou --url")

    emails_brutos: list[str] = []

    if args.arquivo:
        emails_brutos.extend(coletar_de_arquivo(args.arquivo))

    if args.url:
        emails_brutos.extend(coletar_de_url(args.url))

    emails_organizados = organizar_emails(emails_brutos)
    exibir_resumo(emails_organizados)
    salvar_csv(emails_organizados, args.saida)

    return 0


if __name__ == "__main__":
    sys.exit(main())
