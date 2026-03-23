import argparse
import ast
import os
import random
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests
from dotenv import load_dotenv

ARQUIVO_CREDENCIAIS_OCULTO = Path(__file__).with_name(".credenciais")
ARQUIVO_CREDENCIAIS_LEGADO = Path(__file__).with_name("credenciais")
if ARQUIVO_CREDENCIAIS_OCULTO.exists():
    load_dotenv(dotenv_path=ARQUIVO_CREDENCIAIS_OCULTO)
else:
    load_dotenv(dotenv_path=ARQUIVO_CREDENCIAIS_LEGADO)

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

try:
    from googlesearch import search
except ImportError:
    search = None

dorks = [
    'site:edu.br intitle:"corpo docente" "cinema" OR "artes"',
    'site:edu.ar inurl:contacto "letras" OR "artes"',
    'site:edu.mx inurl:directorio "humanidades"',
    'site:edu.co inurl:posgrado "ciencias humanas" OR "artes"',
    'site:edu.br "secretaria de pós-graduação" "sociologia" OR "filosofia"',
    'site:edu.ar inurl:autoridades "ciencias sociales"',
    'site:edu.mx "personal académico" "artes visuales"',
    'site:edu.br inurl:departamento "humanidades"',
    'site:edu.br inurl:docentes "artes"',
    'site:edu.br inurl:coordenacao "letras"',
    'site:edu.ar inurl:departamento "filosofia"',
    'site:edu.ar inurl:docentes "sociologia"',
    'site:edu.mx inurl:facultad "humanidades"',
    'site:edu.mx inurl:docentes "letras"',
    'site:edu.co inurl:facultad "artes"',
    'site:edu.co inurl:docentes "humanidades"',
    'site:edu.pe inurl:escuela "humanidades"',
    'site:edu.pe inurl:docentes "artes"',
    'site:edu.cl inurl:facultad "humanidades"',
    'site:edu.cl inurl:academicos "artes"',
    'site:edu.uy inurl:departamento "ciencias sociales"',
    'site:edu.ec inurl:facultad "artes"',
    'site:edu.py inurl:carrera "humanidades"',
    'site:edu.bo inurl:docentes "filosofia"',
    'site:edu.br "diretoria" "faculdade de artes"',
    'site:edu.ar "secretaría académica" "humanidades"',
    'site:edu.mx "coordinación" "ciencias sociales"',
    'site:edu.co "directorio" "facultad de humanidades"',
    'site:edu.br inurl:contato "departamento de filosofia"',
    'site:edu.ar inurl:contacto "departamento de letras"',
    'site:edu.mx inurl:contacto "facultad de artes"',
    'site:edu.co inurl:contacto "ciencias humanas"'
]

PARAMETROS_RASTREAMENTO = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
}


def normalizar_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return ""

    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    query_filtrada = [
        (chave, valor)
        for chave, valor in parse_qsl(parsed.query, keep_blank_values=False)
        if chave.lower() not in PARAMETROS_RASTREAMENTO
    ]
    query_ordenada = urlencode(sorted(query_filtrada))

    caminho = parsed.path.rstrip("/")
    caminho = caminho if caminho else "/"

    return urlunparse((parsed.scheme.lower(), netloc, caminho, "", query_ordenada, ""))


def extrair_site(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def carregar_urls_existentes(caminho_saida: str) -> list[str]:
    try:
        with open(caminho_saida, "r", encoding="utf-8") as arquivo:
            texto = arquivo.read()
    except FileNotFoundError:
        return []

    try:
        node = ast.parse(texto)
    except SyntaxError:
        return []

    for item in node.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == "urls":
                    valor = ast.literal_eval(item.value)
                    return valor if isinstance(valor, list) else []
    return []


def buscar_no_duckduckgo(dork: str, num_resultados: int) -> list[str]:
    if DDGS is None:
        raise RuntimeError("duckduckgo_search não está instalado.")
    with DDGS() as ddgs:
        resultados = ddgs.text(dork, max_results=num_resultados, region="wt-wt", safesearch="off")
        return [item.get("href", "") for item in resultados if item.get("href")]


def buscar_no_google(dork: str, num_resultados: int) -> list[str]:
    if search is None:
        raise RuntimeError("googlesearch-python não está instalado.")
    resultados_brutos = search(dork, num_results=num_resultados, lang="es")
    resultados = []
    for item in resultados_brutos:
        url = item if isinstance(item, str) else getattr(item, "url", "")
        if url:
            resultados.append(url)
    return resultados


def buscar_no_cse(dork: str, num_resultados: int) -> list[str]:
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cse_cx = os.getenv("GOOGLE_CSE_CX")
    if not api_key or not cse_cx:
        raise RuntimeError("GOOGLE_CSE_API_KEY/GOOGLE_CSE_CX ausentes no arquivo de credenciais.")

    coletadas: list[str] = []
    inicio = 1
    restantes = max(1, num_resultados)

    while restantes > 0 and inicio <= 91:
        por_pagina = min(10, restantes)
        resposta = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": api_key,
                "cx": cse_cx,
                "q": dork,
                "num": por_pagina,
                "start": inicio,
            },
            timeout=20,
        )
        resposta.raise_for_status()
        dados = resposta.json()

        itens = dados.get("items", [])
        if not itens:
            break

        for item in itens:
            link = item.get("link", "")
            if link:
                coletadas.append(link)

        restantes -= len(itens)
        inicio += len(itens)

    return coletadas


def eh_erro_limite(mensagem_erro: str) -> bool:
    mensagem = mensagem_erro.lower()
    gatilhos = ["429", "too many requests", "ratelimit", "sorry/index"]
    return any(gatilho in mensagem for gatilho in gatilhos)


def buscar_com_retry(dork: str, engine: str, num_resultados: int, max_tentativas: int, backoff_base: float) -> list[str]:
    provedores = [engine] if engine != "auto" else ["cse", "duckduckgo", "google"]

    for provedor in provedores:
        for tentativa in range(1, max_tentativas + 1):
            try:
                if provedor == "duckduckgo":
                    resultados = buscar_no_duckduckgo(dork, num_resultados)
                elif provedor == "google":
                    resultados = buscar_no_google(dork, num_resultados)
                else:
                    resultados = buscar_no_cse(dork, num_resultados)

                if resultados:
                    return resultados

                print(f"[{provedor}] Sem resultados para este dork.")
                break
            except Exception as e:
                if eh_erro_limite(str(e)) and tentativa < max_tentativas:
                    espera = (backoff_base * (2 ** (tentativa - 1))) + random.uniform(0.5, 2.0)
                    print(
                        f"[{provedor}] Limite detectado. Aguardando {espera:.1f}s antes da tentativa {tentativa + 1}..."
                    )
                    time.sleep(espera)
                    continue

                if tentativa == max_tentativas:
                    print(f"[{provedor}] Falha após {max_tentativas} tentativas: {e}")
                else:
                    print(f"[{provedor}] Erro: {e}")

        if engine == "auto":
            print(f"Mudando para provedor alternativo após falhas no {provedor}.")

    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca URLs acadêmicas com menos bloqueio por rate-limit.")
    parser.add_argument("--engine", choices=["auto", "cse", "duckduckgo", "google"], default="auto")
    parser.add_argument("--num-resultados", type=int, default=8)
    parser.add_argument("--max-tentativas", type=int, default=3)
    parser.add_argument("--backoff-base", type=float, default=8.0)
    parser.add_argument("--pausa-min", type=float, default=2.0)
    parser.add_argument("--pausa-max", type=float, default=5.0)
    parser.add_argument("--limite-total", type=int, default=200)
    parser.add_argument("--max-urls-por-site", type=int, default=1)
    parser.add_argument("--rodadas", type=int, default=1)
    parser.add_argument("--acumular", action="store_true")
    parser.add_argument("--saida", default="lista_urls.py")
    args = parser.parse_args()

    urls_unicas = set()
    contagem_por_site = {}

    if args.acumular:
        for url_existente in carregar_urls_existentes(args.saida):
            url_normalizada = normalizar_url(url_existente)
            if not url_normalizada:
                continue
            site = extrair_site(url_normalizada)
            urls_unicas.add(url_normalizada)
            if site:
                contagem_por_site[site] = contagem_por_site.get(site, 0) + 1

    for rodada in range(1, args.rodadas + 1):
        if len(urls_unicas) >= args.limite_total:
            break

        print(f"=== Rodada {rodada}/{args.rodadas} ===")
        for indice, dork in enumerate(dorks, start=1):
            print(f"[{indice}/{len(dorks)}] Buscando: {dork}")
            resultados = buscar_com_retry(
                dork=dork,
                engine=args.engine,
                num_resultados=args.num_resultados,
                max_tentativas=args.max_tentativas,
                backoff_base=args.backoff_base,
            )

            for url in resultados:
                url_normalizada = normalizar_url(url)
                if not url_normalizada:
                    continue

                if url_normalizada in urls_unicas:
                    continue

                site = extrair_site(url_normalizada)
                quantidade_no_site = contagem_por_site.get(site, 0)
                if site and quantidade_no_site >= args.max_urls_por_site:
                    continue

                urls_unicas.add(url_normalizada)
                if site:
                    contagem_por_site[site] = quantidade_no_site + 1

            pausa = random.uniform(args.pausa_min, args.pausa_max)
            time.sleep(pausa)

            if len(urls_unicas) >= args.limite_total:
                break

    urls_limitadas = list(urls_unicas)[: args.limite_total]

    with open(args.saida, "w", encoding="utf-8") as f:
        f.write("urls = [\n")
        for url in urls_limitadas:
            f.write(f'    "{url}",\n')
        f.write("]\n")

    print(f"Processo finalizado. {len(urls_limitadas)} URLs validadas e salvas em '{args.saida}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())