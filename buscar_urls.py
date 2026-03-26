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
    # Brasil
    'site:edu.br intitle:"corpo docente" "cinema" OR "artes"',
    'site:edu.br "secretaria de pós-graduação" "sociologia" OR "filosofia"',
    'site:edu.br inurl:departamento "humanidades"',
    'site:edu.br inurl:docentes "artes"',
    'site:edu.br inurl:coordenacao "letras"',
    'site:edu.br "diretoria" "faculdade de artes"',
    'site:edu.br inurl:contato "departamento de filosofia"',
    'site:edu.br inurl:docentes "historia"',
    'site:edu.br "corpo docente" "antropologia"',
    'site:edu.br inurl:ppg "sociologia" OR "antropologia"',
    'site:edu.br inurl:departamento "letras"',
    'site:edu.br inurl:professores "filosofia"',
    'site:edu.br "quadro docente" "história"',
    'site:edu.br "coordenação" "ciencias humanas"',
    'site:edu.br inurl:contato "instituto de artes"',
    'site:edu.br inurl:programa "pós-graduação" "humanidades"',
    'site:edu.br inurl:curso "corpo docente" "letras"',
    'site:edu.br inurl:anais "congresso" "humanidades"',
    'site:edu.br inurl:anais "simpósio" "artes"',
    'site:edu.br "anais" "ciências sociais" "universidade"',

    # Argentina
    'site:edu.ar inurl:contacto "letras" OR "artes"',
    'site:edu.ar inurl:autoridades "ciencias sociales"',
    'site:edu.ar inurl:departamento "filosofia"',
    'site:edu.ar inurl:docentes "sociologia"',
    'site:edu.ar "secretaría académica" "humanidades"',
    'site:edu.ar inurl:contacto "departamento de letras"',
    'site:edu.ar inurl:cuerpo-docente "artes" OR "cine"',
    'site:edu.ar inurl:posgrado "historia"',
    'site:edu.ar inurl:profesores "humanidades"',
    'site:edu.ar inurl:catedra "filosofia" OR "letras"',
    'site:edu.ar inurl:anales "congreso" "humanidades"',

    # México
    'site:edu.mx inurl:directorio "humanidades"',
    'site:edu.mx "personal académico" "artes visuales"',
    'site:edu.mx inurl:facultad "humanidades"',
    'site:edu.mx inurl:docentes "letras"',
    'site:edu.mx "coordinación" "ciencias sociales"',
    'site:edu.mx inurl:contacto "facultad de artes"',
    'site:edu.mx inurl:directorio "filosofia" OR "letras"',
    'site:edu.mx inurl:plantilla-docente "sociologia"',
    'site:edu.mx inurl:academico "ciencias sociales"',
    'site:edu.mx inurl:profesores "humanidades"',
    'site:edu.mx inurl:memorias "congreso" "ciencias sociales"',

    # Colômbia
    'site:edu.co inurl:posgrado "ciencias humanas" OR "artes"',
    'site:edu.co inurl:facultad "artes"',
    'site:edu.co inurl:docentes "humanidades"',
    'site:edu.co "directorio" "facultad de humanidades"',
    'site:edu.co inurl:contacto "ciencias humanas"',
    'site:edu.co inurl:profesores "filosofia"',
    'site:edu.co inurl:departamento "filosofia"',
    'site:edu.co inurl:docentes "ciencias sociales"',
    'site:edu.co inurl:anales "congreso" "humanidades"',

    # Outros LATAM
    'site:edu.pe inurl:escuela "humanidades"',
    'site:edu.pe inurl:docentes "artes"',
    'site:edu.pe inurl:coordinacion "humanidades"',
    'site:edu.cl inurl:facultad "humanidades"',
    'site:edu.cl inurl:academicos "artes"',
    'site:edu.cl inurl:docentes "filosofia"',
    'site:edu.uy inurl:departamento "ciencias sociales"',
    'site:edu.uy inurl:docentes "artes"',
    'site:edu.ec inurl:facultad "artes"',
    'site:edu.ec inurl:docentes "humanidades"',
    'site:edu.py inurl:carrera "humanidades"',
    'site:edu.bo inurl:docentes "filosofia"',
    'site:edu.pe inurl:anales "congreso" "humanidades"',
    'site:edu.cl inurl:actas "congreso" "humanidades"',
    'site:edu.uy inurl:anais OR inurl:anales "ciencias sociales"',

    # Acadêmico amplo (sem filtro estrito por país)
    'site:.edu inurl:faculty "humanities" "email"',
    'site:.edu "department of philosophy" "faculty"',
    'site:.edu inurl:people "arts" "professor"',
    'site:.edu "social sciences" "contact"',

    # Portais acadêmicos e pesquisa
    'site:scholar.google.com "humanities" "university"',
    'site:researchgate.net "department" "humanities" "email"',
    'site:researchgate.net "social sciences" "university" "contact"',
    'site:scielo.org "universidade" "contato"',
    'site:scielo.org "ciencias sociales" "universidad"',
    'site:repositorio "edu.br" "humanidades" "contato"',
    'site:repositorio "edu.ar" "ciencias sociales" "contacto"',
    'site:dialnet.unirioja.es "universidad" "humanidades"',
    'site:eric.ed.gov "social sciences" "university"',
    'site:orcid.org "university" "humanities"',
    'site:academia.edu "department of" "humanities"',
    '"fórum universitário" "departamento" "contato"',
    '"foro universitario" "facultad" "contacto"',
    '"jornada acadêmica" "contato" "humanidades"',
    '"congreso" "ciencias sociales" "universidad" "contacto"',

    # Fóruns, jornais e portais institucionais (agressivo)
    '"jornal universitário" "expediente" "email"',
    '"jornal da universidade" "contato" "redação"',
    '"portal universitário" "quem somos" "contato"',
    '"portal acadêmico" "contato" "humanidades"',
    '"forum universitario" "docentes" "contacto"',
    '"foro academico" "ciencias sociales" "contacto"',
    'site:.br "portal" "universidade" "contato" "humanidades"',
    'site:.br "jornal" "universidade" "expediente" "email"',
    'site:.ar "portal" "universidad" "contacto" "humanidades"',
    'site:.mx "portal" "universidad" "contacto" "ciencias sociales"',
    'site:.co "portal" "universidad" "contacto" "humanidades"',
    'site:.cl "portal" "universidad" "contacto" "humanidades"',
    'site:.pe "portal" "universidad" "contacto" "humanidades"',
    'site:gov.br "universidade" "departamento" "contato"',
    'site:edu.br inurl:forum "universidade" "humanidades"',
    'site:edu.ar inurl:foro "universidad" "ciencias sociales"',
    'site:edu.mx inurl:foro "universidad" "humanidades"',
    'site:edu.co inurl:foro "universidad" "humanidades"',
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

DOMINIOS_BLOQUEADOS = {
    "google.com",
    "bing.com",
    "zhihu.com",
    "yahoo.com",
    "msn.com",
    "apple.com",
    "americanexpress.com",
    "fedex.com",
    "bunnings.com.au",
    "tripadvisor.com",
    "autotrader.com",
    "cars.com",
    "carmax.com",
    "cargurus.com",
    "edmunds.com",
    "truecar.com",
    "chemicalguys.com",
    "twitch.tv",
    "youtube.com",
    "emojipedia.org",
    "emojicopy.com",
    "emojiverse.ai",
    "emojis.wiki",
    "googleapis.com",
    "doubleclick.net",
    "googleadservices.com",
    "adobe.com",
}

DOMINIOS_EXCECAO_ACADEMICOS = {
    "scholar.google.com",
    "researchgate.net",
    "scielo.org",
    "academia.edu",
    "orcid.org",
    "dialnet.unirioja.es",
    "eric.ed.gov",
}

SUFIXOS_LATAM = {
    ".br",
    ".ar",
    ".mx",
    ".co",
    ".cl",
    ".pe",
    ".uy",
    ".ec",
    ".py",
    ".bo",
    ".ve",
    ".cr",
    ".pa",
    ".do",
    ".gt",
    ".hn",
    ".ni",
    ".sv",
    ".cu",
}

EDU_LATAM = {
    ".edu.br",
    ".edu.ar",
    ".edu.mx",
    ".edu.co",
    ".edu.cl",
    ".edu.pe",
    ".edu.uy",
    ".edu.ec",
    ".edu.py",
    ".edu.bo",
    ".edu.ve",
    ".edu.cr",
    ".edu.pa",
    ".edu.do",
    ".edu.gt",
    ".edu.hn",
    ".edu.ni",
    ".edu.sv",
    ".edu.cu",
}

PROVEDOR_COOLDOWN_ATE: dict[str, float] = {}


def provedor_em_cooldown(provedor: str) -> bool:
    ate = PROVEDOR_COOLDOWN_ATE.get(provedor, 0.0)
    restante = ate - time.time()
    if restante > 0:
        print(f"[{provedor}] Em cooldown por limite/rate-limit. Restam {restante:.0f}s.")
        return True
    return False


def ativar_cooldown_provedor(provedor: str) -> None:
    cooldown_segundos = float(os.getenv("BUSCA_COOLDOWN_LIMITE_SECONDS", "2400"))
    PROVEDOR_COOLDOWN_ATE[provedor] = time.time() + cooldown_segundos
    print(f"[{provedor}] Cooldown ativado por {int(cooldown_segundos)}s após detecção de limite.")


def eh_url_pertinente(url: str) -> bool:
    site = extrair_site(url)
    if not site:
        return False

    caminho = (urlparse(url).path or "").lower()

    if site in DOMINIOS_EXCECAO_ACADEMICOS:
        return True

    if any(site == bloqueado or site.endswith(f".{bloqueado}") for bloqueado in DOMINIOS_BLOQUEADOS):
        return False

    # Prioriza domínios acadêmicos e governamentais educacionais
    if ".edu." in site or site.endswith(".edu"):
        return True

    # Mantém alguns domínios institucionais relevantes não-.edu
    indicadores_institucionais = (
        "univers",
        "faculdade",
        "facultad",
        "instituto",
        "campus",
        "if",
        "uf",
        "usp",
        "unam",
        "udelar",
        "uach",
        "unr",
    )
    if any(indicador in site for indicador in indicadores_institucionais):
        return True

    # Agressivo: aceita portais/fóruns/jornais quando o contexto sugere relevância acadêmica
    indicadores_fontes = (
        "forum",
        "foro",
        "portal",
        "jornal",
        "noticia",
        "noticias",
        "news",
        "revista",
        "blog",
        "anais",
        "congresso",
        "congreso",
        "simposio",
        "simpósio",
        "expediente",
    )

    if any(ind in site for ind in indicadores_fontes) or any(ind in caminho for ind in indicadores_fontes):
        return True

    return False


def cse_configurado() -> bool:
    return bool(os.getenv("GOOGLE_CSE_API_KEY") and os.getenv("GOOGLE_CSE_CX"))


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


def eh_url_brasil(url: str) -> bool:
    site = extrair_site(url)
    return site.endswith(".br") if site else False


def eh_url_latam(url: str) -> bool:
    site = extrair_site(url)
    if not site:
        return False

    if any(site.endswith(sufixo) for sufixo in SUFIXOS_LATAM):
        return True

    return any(site.endswith(sufixo_edu) for sufixo_edu in EDU_LATAM)


def selecionar_dorks(apenas_br: bool) -> list[str]:
    if not apenas_br:
        return dorks
    return [dork for dork in dorks if "site:edu.br" in dork]


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


def buscar_no_bing(dork: str, num_resultados: int) -> list[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 não está instalado.") from exc

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }

    coletadas: list[str] = []
    inicio = 1

    while len(coletadas) < num_resultados and inicio <= 101:
        por_pagina = min(50, num_resultados - len(coletadas))
        resposta = requests.get(
            "https://www.bing.com/search",
            params={"q": dork, "count": por_pagina, "first": inicio},
            headers=headers,
            timeout=20,
        )
        resposta.raise_for_status()

        soup = BeautifulSoup(resposta.text, "lxml")
        links = soup.select("li.b_algo h2 a[href]")
        if not links:
            break

        adicionados = 0
        for link in links:
            href_attr = link.get("href")
            if isinstance(href_attr, str):
                href = href_attr.strip()
            elif isinstance(href_attr, list):
                href = " ".join(str(item) for item in href_attr if item).strip()
            else:
                href = ""
            if href.startswith("http"):
                coletadas.append(href)
                adicionados += 1
                if len(coletadas) >= num_resultados:
                    break

        if adicionados == 0:
            break

        inicio += adicionados
        time.sleep(random.uniform(0.8, 1.8))

    return coletadas[:num_resultados]


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
        try:
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
        except requests.exceptions.HTTPError as http_err:
            # Detecta erro de quota excedida (código 429 ou mensagem de quota)
            status_code = None
            text = ""
            if hasattr(http_err, 'response') and http_err.response is not None:
                status_code = http_err.response.status_code
                text = http_err.response.text or ""
            if status_code == 429 or ("quota" in text.lower() or "exceeded" in text.lower()):
                print("[cse] Limite de quota atingido. Ativando cooldown do provedor CSE.")
                ativar_cooldown_provedor("cse")
                break
            raise
        except Exception as e:
            # Falha genérica
            print(f"[cse] Erro inesperado: {e}")
            break

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


def buscar_no_yandex(dork: str, num_resultados: int) -> list[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 não está instalado.") from exc

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }

    resposta = requests.get(
        "https://yandex.com/search/",
        params={"text": dork},
        headers=headers,
        timeout=20,
    )
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "lxml")
    coletadas: list[str] = []

    for link in soup.select("a[href]"):
        href_attr = link.get("href")
        if isinstance(href_attr, str):
            href = href_attr.strip()
        elif isinstance(href_attr, list):
            href = " ".join(str(item) for item in href_attr if item).strip()
        else:
            href = ""

        if not href.startswith("http"):
            continue

        site = extrair_site(href)
        if site.endswith("yandex.com") or site.endswith("yandex.ru"):
            continue

        coletadas.append(href)
        if len(coletadas) >= num_resultados:
            break

    return coletadas


def buscar_no_brave(dork: str, num_resultados: int) -> list[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 não está instalado.") from exc

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }

    resposta = requests.get(
        "https://search.brave.com/search",
        params={"q": dork, "source": "web"},
        headers=headers,
        timeout=20,
    )
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "lxml")
    coletadas: list[str] = []

    for link in soup.select("a[href]"):
        href_attr = link.get("href")
        if isinstance(href_attr, str):
            href = href_attr.strip()
        elif isinstance(href_attr, list):
            href = " ".join(str(item) for item in href_attr if item).strip()
        else:
            href = ""

        if not href.startswith("http"):
            continue

        site = extrair_site(href)
        if "brave.com" in site:
            continue

        coletadas.append(href)
        if len(coletadas) >= num_resultados:
            break

    return coletadas


def buscar_no_qwant(dork: str, num_resultados: int) -> list[str]:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise RuntimeError("beautifulsoup4 não está instalado.") from exc

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    }

    resposta = requests.get(
        "https://www.qwant.com/",
        params={"q": dork, "t": "web"},
        headers=headers,
        timeout=20,
    )
    resposta.raise_for_status()

    soup = BeautifulSoup(resposta.text, "lxml")
    coletadas: list[str] = []

    for link in soup.select("a[href]"):
        href_attr = link.get("href")
        if isinstance(href_attr, str):
            href = href_attr.strip()
        elif isinstance(href_attr, list):
            href = " ".join(str(item) for item in href_attr if item).strip()
        else:
            href = ""

        if not href.startswith("http"):
            continue

        site = extrair_site(href)
        if "qwant.com" in site:
            continue

        coletadas.append(href)
        if len(coletadas) >= num_resultados:
            break

    return coletadas


def eh_erro_limite(mensagem_erro: str) -> bool:
    mensagem = mensagem_erro.lower()
    gatilhos = ["429", "too many requests", "ratelimit", "sorry/index"]
    return any(gatilho in mensagem for gatilho in gatilhos)


def salvar_urls_em_arquivo(caminho_saida: str, urls_unicas: set[str], limite_total: int) -> int:
    urls_limitadas = sorted(urls_unicas)[:limite_total]
    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.write("urls = [\n")
        for url in urls_limitadas:
            f.write(f'    "{url}",\n')
        f.write("]\n")
    return len(urls_limitadas)


def buscar_com_retry(dork: str, engine: str, num_resultados: int, max_tentativas: int, backoff_base: float) -> list[str]:
    if engine == "auto":
        provedores_env = os.getenv("BUSCA_AUTO_PROVEDORES", "yandex,bing,qwant,duckduckgo,brave,google,cse")
        provedores = [p.strip().lower() for p in provedores_env.split(",") if p.strip()]
        permitidos = {"cse", "duckduckgo", "bing", "google", "yandex", "brave", "qwant"}
        provedores = [p for p in provedores if p in permitidos]

        if not provedores:
            provedores = ["yandex", "bing", "qwant", "duckduckgo", "brave", "google"]

        if "cse" in provedores and not cse_configurado():
            print("[cse] Não configurado. Pulando CSE (adicione GOOGLE_CSE_API_KEY e GOOGLE_CSE_CX para ativar).")
            provedores = [p for p in provedores if p != "cse"]
    else:
        provedores = [engine]

    for provedor in provedores:
        if provedor_em_cooldown(provedor):
            if engine == "auto":
                print(f"Mudando para provedor alternativo após cooldown no {provedor}.")
            continue

        for tentativa in range(1, max_tentativas + 1):
            try:
                if provedor == "duckduckgo":
                    resultados = buscar_no_duckduckgo(dork, num_resultados)
                elif provedor == "bing":
                    resultados = buscar_no_bing(dork, num_resultados)
                elif provedor == "google":
                    resultados = buscar_no_google(dork, num_resultados)
                elif provedor == "yandex":
                    resultados = buscar_no_yandex(dork, num_resultados)
                elif provedor == "brave":
                    resultados = buscar_no_brave(dork, num_resultados)
                elif provedor == "qwant":
                    resultados = buscar_no_qwant(dork, num_resultados)
                else:
                    resultados = buscar_no_cse(dork, num_resultados)

                if resultados:
                    return resultados

                print(f"[{provedor}] Sem resultados para este dork.")
                break
            except Exception as e:
                erro_str = str(e)
                if tentativa == max_tentativas:
                    print(f"[{provedor}] Falha definitiva após {max_tentativas} tentativas: {erro_str}")
                    if eh_erro_limite(erro_str):
                        ativar_cooldown_provedor(provedor)
                    break

                if eh_erro_limite(erro_str):
                    # Recuo exponencial com jitter
                    tempo_espera = backoff_base * (2 ** (tentativa - 1)) + random.uniform(0.5, 2.5)
                    print(f"[{provedor}] Rate limit (429) detectado. Recuo exponencial: aguardando {tempo_espera:.1f}s (Tentativa {tentativa}/{max_tentativas}).")
                    time.sleep(tempo_espera)
                else:
                    print(f"[{provedor}] Erro comum: {erro_str}. Retentando em breve...")
                    time.sleep(2)

        if engine == "auto":
            print(f"Mudando para provedor alternativo após falhas no {provedor}.")

    return []


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca URLs acadêmicas com menos bloqueio por rate-limit.")
    parser.add_argument(
        "--engine",
        choices=["auto", "cse", "duckduckgo", "bing", "google", "yandex", "brave", "qwant"],
        default="auto",
    )
    parser.add_argument("--num-resultados", type=int, default=35)
    parser.add_argument("--max-tentativas", type=int, default=3)
    parser.add_argument("--backoff-base", type=float, default=8.0)
    parser.add_argument("--pausa-min", type=float, default=2.0)
    parser.add_argument("--pausa-max", type=float, default=5.0)
    parser.add_argument("--limite-total", type=int, default=1000)
    parser.add_argument("--max-urls-por-site", type=int, default=8)
    parser.add_argument("--rodadas", type=int, default=2)
    parser.add_argument("--acumular", action="store_true")
    parser.add_argument("--apenas-br", action="store_true")
    parser.add_argument("--apenas-latam", action="store_true")
    parser.add_argument("--saida", default="lista_urls.py")
    args = parser.parse_args()

    dorks_ativas = selecionar_dorks(args.apenas_br)
    if not dorks_ativas:
        print("Nenhuma dork disponível para o filtro selecionado.")
        return 1

    urls_unicas = set()
    contagem_por_site = {}

    if args.acumular:
        for url_existente in carregar_urls_existentes(args.saida):
            url_normalizada = normalizar_url(url_existente)
            if not url_normalizada:
                continue
            # NÃO filtrar URLs já existentes - preservar lista completa
            # O filtro só se aplica a URLs NOVAS descobertas
            site = extrair_site(url_normalizada)
            urls_unicas.add(url_normalizada)
            if site:
                contagem_por_site[site] = contagem_por_site.get(site, 0) + 1

    try:
        for rodada in range(1, args.rodadas + 1):
            if len(urls_unicas) >= args.limite_total:
                break

            print(f"=== Rodada {rodada}/{args.rodadas} ===")
            for indice, dork in enumerate(dorks_ativas, start=1):
                print(f"[{indice}/{len(dorks_ativas)}] Buscando: {dork}")
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

                    if not eh_url_pertinente(url_normalizada):
                        continue

                    if args.apenas_br and not eh_url_brasil(url_normalizada):
                        continue

                    if args.apenas_latam and not eh_url_latam(url_normalizada):
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

                total_atual = salvar_urls_em_arquivo(args.saida, urls_unicas, args.limite_total)
                print(f"Progresso salvo: {total_atual} URLs em '{args.saida}'.")

                pausa = random.uniform(args.pausa_min, args.pausa_max)
                time.sleep(pausa)

                if len(urls_unicas) >= args.limite_total:
                    break
    except KeyboardInterrupt:
        total_atual = salvar_urls_em_arquivo(args.saida, urls_unicas, args.limite_total)
        print(f"\nInterrompido pelo usuário. Progresso salvo com {total_atual} URLs em '{args.saida}'.")
        return 130

    total_final = salvar_urls_em_arquivo(args.saida, urls_unicas, args.limite_total)
    print(f"Processo finalizado. {total_final} URLs validadas e salvas em '{args.saida}'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())