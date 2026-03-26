"""
Projeto Coleta e Organização de Emails (Com Validação IA)
"""
import argparse
import csv
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlsplit, urlunsplit
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
ARQUIVO_URLS_PROCESSADAS_SEM_IA = Path(PASTA_SAIDA) / "urls_processadas.txt"
ARQUIVO_URLS_PROCESSADAS_COM_IA = Path(PASTA_SAIDA) / "urls_processadas_ia.txt"
MAX_FALHAS_CONSECUTIVAS_IA = int(os.getenv("IA_MAX_FALHAS_CONSECUTIVAS", "5"))
MAX_EMAILS_POR_EXECUCAO = int(os.getenv("MAX_EMAILS_POR_EXECUCAO", "2500"))
COLETA_TIMEOUT_SECONDS = int(os.getenv("COLETA_TIMEOUT_SECONDS", "10"))
IA_HTTP_TIMEOUT_SECONDS = int(os.getenv("IA_HTTP_TIMEOUT_SECONDS", "12"))
IA_OLLAMA_TIMEOUT_SECONDS = int(os.getenv("IA_OLLAMA_TIMEOUT_SECONDS", str(IA_HTTP_TIMEOUT_SECONDS)))
IA_GEMINI_TIMEOUT_SECONDS = int(os.getenv("IA_GEMINI_TIMEOUT_SECONDS", str(IA_HTTP_TIMEOUT_SECONDS)))
IA_MIN_DECISOES_SIM = int(os.getenv("IA_MIN_DECISOES_SIM", "2"))


def obter_arquivo_urls_processadas(usar_ia: bool) -> Path:
    return ARQUIVO_URLS_PROCESSADAS_COM_IA if usar_ia else ARQUIVO_URLS_PROCESSADAS_SEM_IA


def normalizar_url_para_controle(url: str) -> str:
    try:
        partes = urlsplit(url.strip())
        caminho = partes.path.rstrip("/")
        return urlunsplit((partes.scheme.lower(), partes.netloc.lower(), caminho, partes.query, ""))
    except Exception:
        return url.strip().lower().rstrip("/")


def carregar_urls_processadas(arquivo_urls_processadas: Path) -> set[str]:
    if not arquivo_urls_processadas.exists():
        return set()

    with arquivo_urls_processadas.open("r", encoding="utf-8") as arquivo:
        return {
            normalizar_url_para_controle(linha)
            for linha in arquivo
            if linha.strip()
        }


def registrar_url_processada(url: str, arquivo_urls_processadas: Path) -> None:
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    url_normalizada = normalizar_url_para_controle(url)
    with arquivo_urls_processadas.open("a", encoding="utf-8") as arquivo:
        arquivo.write(url_normalizada + "\n")

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

def coletar_de_url(url: str) -> tuple[dict, bool]:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {}, False

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64)'}
        resposta = requests.get(url, headers=headers, timeout=COLETA_TIMEOUT_SECONDS)
        resposta.raise_for_status()
    except requests.RequestException:
        return {}, False

    soup = BeautifulSoup(resposta.text, "lxml")
    texto = soup.get_text(separator=" ")
    resultados = extrair_emails_com_contexto(texto)

    for link in soup.select("a[href^='mailto:']"):
        href_attr = link.get("href")
        if isinstance(href_attr, str):
            href = href_attr.strip()
        elif isinstance(href_attr, list):
            href = " ".join(str(item) for item in href_attr if item).strip()
        else:
            href = ""
        if not href:
            continue

        bruto = href[len("mailto:"):]
        if "?" in bruto:
            bruto = bruto.split("?", 1)[0]
        email = normalizar_email(unquote(bruto))
        if not email or not EMAIL_REGEX.fullmatch(email):
            continue
        if email not in resultados:
            resultados[email] = "extraído de link mailto"

    return resultados, True

def configurar_ia():
    ordem_padrao = ["groq", "gemini", "openrouter", "ollama"]
    ordem_env = os.getenv("IA_PROVIDER_ORDER", "").strip()
    ordem = [item.strip().lower() for item in ordem_env.split(",") if item.strip()] if ordem_env else ordem_padrao

    clientes = []

    for provedor in ordem:
        if provedor == "gemini":
            chave = os.getenv("GEMINI_API_KEY")
            if not chave:
                continue
            if not genai:
                print("[IA] Gemini ignorado: pacote google-generativeai ausente.", file=sys.stderr)
                continue
            configure_fn = getattr(genai, "configure", None)
            model_cls = getattr(genai, "GenerativeModel", None)
            if not callable(configure_fn) or model_cls is None:
                print("[IA] Gemini ignorado: versão incompatível do pacote.", file=sys.stderr)
                continue
            try:
                configure_fn(api_key=chave)
                clientes.append({
                    "nome": "gemini",
                    "tipo": "gemini",
                    "modelo": model_cls(os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
                    "falhas_consecutivas": 0,
                })
            except Exception as erro:
                print(f"[IA] Gemini indisponível: {erro}", file=sys.stderr)

        elif provedor == "groq":
            chave = os.getenv("GROQ_API_KEY") or os.getenv("GROQ_CLOUD_API_KEY")
            if not chave:
                continue
            clientes.append({
                "nome": "groq",
                "tipo": "http_chat",
                "url": "https://api.groq.com/openai/v1/chat/completions",
                "key": chave,
                "modelo": os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                "falhas_consecutivas": 0,
                "headers": {
                    "Authorization": f"Bearer {chave}",
                    "Content-Type": "application/json",
                },
            })

        elif provedor == "openrouter":
            chave = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPEN_ROUTER_API_KEY")
            if not chave:
                continue
            app_url = os.getenv("OPENROUTER_APP_URL", "http://localhost")
            app_nome = os.getenv("OPENROUTER_APP_NAME", "coleta-emails")
            clientes.append({
                "nome": "openrouter",
                "tipo": "http_chat",
                "url": "https://openrouter.ai/api/v1/chat/completions",
                "key": chave,
                "modelo": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.1-8b-instruct:free"),
                "falhas_consecutivas": 0,
                "headers": {
                    "Authorization": f"Bearer {chave}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": app_url,
                    "X-Title": app_nome,
                },
            })

        elif provedor == "ollama":
            clientes.append({
                "nome": "ollama",
                "tipo": "ollama",
                "url": os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate"),
                "modelo": os.getenv("OLLAMA_MODEL", "llama3.1:8b"),
                "falhas_consecutivas": 0,
            })

    if not clientes:
        print(
            "Nenhum provedor de IA configurado. Configure ao menos uma chave: GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY, ou Ollama local.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"[IA] Provedores ativos (ordem): {', '.join(c['nome'] for c in clientes)}", file=sys.stderr)
    return clientes


def _extrair_resposta_sim_nao(texto: str) -> bool | None:
    if not texto:
        return None
    resposta = texto.strip().upper()
    if resposta.startswith("S"):
        return True
    if resposta.startswith("N"):
        return False
    return None


def _erro_limite_ou_cota(mensagem: str) -> bool:
    msg = mensagem.lower()
    sinais = ["429", "rate", "quota", "limit", "resource_exhausted", "too many requests", "insufficient_quota"]
    return any(s in msg for s in sinais)


def _erro_permanente(mensagem: str) -> bool:
    msg = mensagem.lower()
    sinais = [
        "401",
        "403",
        "404",
        "unauthorized",
        "forbidden",
        "not found",
        "model not found",
        "invalid api key",
        "api key inválida",
        "insufficient_quota",
    ]
    return any(s in msg for s in sinais)


def _validar_com_cliente(cliente: dict, prompt: str) -> tuple[bool | None, str]:
    try:
        if cliente["tipo"] == "gemini":
            resposta = cliente["modelo"].generate_content(
                prompt,
                request_options={"timeout": IA_GEMINI_TIMEOUT_SECONDS},
            )
            time.sleep(1)
            texto = getattr(resposta, "text", "")
            decisao = _extrair_resposta_sim_nao(texto)
            return decisao, "nenhum"

        if cliente["tipo"] == "http_chat":
            import requests

            payload = {
                "model": cliente["modelo"],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "temperature": 0,
            }
            resp = requests.post(
                cliente["url"],
                headers=cliente["headers"],
                data=json.dumps(payload),
                timeout=IA_HTTP_TIMEOUT_SECONDS,
            )
            if resp.status_code in (401, 403):
                return None, "permanente"
            if resp.status_code == 404:
                return None, "permanente"
            if resp.status_code == 429:
                return None, "temporario"
            resp.raise_for_status()

            data = resp.json()
            texto = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            return _extrair_resposta_sim_nao(texto), "nenhum"

        if cliente["tipo"] == "ollama":
            import requests

            payload = {
                "model": cliente["modelo"],
                "prompt": prompt,
                "stream": False,
            }
            resp = requests.post(cliente["url"], json=payload, timeout=IA_OLLAMA_TIMEOUT_SECONDS)
            if resp.status_code == 404:
                return None, "permanente"
            if resp.status_code >= 500:
                return None, "temporario"
            resp.raise_for_status()
            data = resp.json()
            texto = data.get("response", "")
            return _extrair_resposta_sim_nao(texto), "nenhum"

        return None, "temporario"
    except Exception as erro:
        mensagem = str(erro)
        if _erro_permanente(mensagem):
            return None, "permanente"
        if _erro_limite_ou_cota(mensagem):
            return None, "temporario"
        return None, "temporario"


def validar_com_ia(clientes_ia: list[dict], email: str, contexto: str) -> tuple[bool, str]:
    prompt = f"""
    Objetivo da campanha: contatos acadêmicos institucionais de alta relevância para Artes, Cinema, Letras,
    Sociologia, Filosofia e Humanidades em universidades/faculdades.

    Email: {email}
    Contexto extraído da página: {contexto}

    Critérios para responder S (SIM):
    - Contato institucional útil para relacionamento acadêmico (secretaria, coordenação, pós-graduação, departamento,
      núcleo acadêmico, escolar, extensão acadêmica ou equivalente).
    - Forte relação com as áreas-alvo no contexto.

    Critérios para responder N (NÃO):
    - Email pessoal de docente/aluno/colaborador sem função institucional clara de contato.
    - Caixa genérica sem vínculo acadêmico estratégico ao objetivo da campanha.
    - Contexto fraco, ambíguo ou fora das áreas-alvo.
    - Em caso de dúvida, risco estratégico ou baixa confiança, responda N.

    Responda APENAS com S ou N.
    """

    indice = 0
    decisoes_sim = 0
    decisoes_nao = 0
    sim_por_ollama = False

    while indice < len(clientes_ia):
        cliente = clientes_ia[indice]
        decisao, tipo_erro = _validar_com_cliente(cliente, prompt)

        if decisao is True:
            cliente["falhas_consecutivas"] = 0
            decisoes_sim += 1
            if cliente.get("nome") == "ollama":
                sim_por_ollama = True
            indice += 1
            continue

        if decisao is False:
            cliente["falhas_consecutivas"] = 0
            decisoes_nao += 1
            indice += 1
            continue

        if tipo_erro == "permanente":
            print(f"[IA] Provedor '{cliente['nome']}' com erro permanente. Removendo desta execução.", file=sys.stderr)
            clientes_ia.pop(indice)
            continue

        cliente["falhas_consecutivas"] = cliente.get("falhas_consecutivas", 0) + 1
        if cliente["falhas_consecutivas"] >= MAX_FALHAS_CONSECUTIVAS_IA:
            print(
                f"[IA] Provedor '{cliente['nome']}' indisponível por {cliente['falhas_consecutivas']} falhas seguidas. Removendo desta execução.",
                file=sys.stderr,
            )
            clientes_ia.pop(indice)
            continue

        indice += 1

    if decisoes_sim >= IA_MIN_DECISOES_SIM:
        if sim_por_ollama:
            return True, "aprovado_com_ollama"
        return True, "aprovado_em_cascata"
    if decisoes_nao > 0:
        return False, "reprovado_em_cascata"
    return False, "sem_decisao_ia"


def carregar_emails_csv(caminho_saida: str) -> list[str]:
    caminho_completo = os.path.join(PASTA_SAIDA, caminho_saida)
    if not os.path.exists(caminho_completo):
        return []

    with open(caminho_completo, "r", newline="", encoding="utf-8") as arquivo_csv:
        leitor = csv.DictReader(arquivo_csv)
        if not leitor.fieldnames:
            return []
        coluna = "email_validado" if "email_validado" in leitor.fieldnames else leitor.fieldnames[0]
        return [
            (linha.get(coluna) or "").strip()
            for linha in leitor
            if (linha.get(coluna) or "").strip()
        ]


def salvar_csv_unico_acumulado(emails_novos: list[str], caminho_saida: str) -> None:
    existentes = carregar_emails_csv(caminho_saida)
    vistos = set()
    combinados = []

    for email in existentes + emails_novos:
        chave = email.strip().lower()
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        combinados.append(email.strip())

    salvar_csv(combinados, caminho_saida)

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
    parser.add_argument(
        "--ignorar-processadas",
        action="store_true",
        help="Revisita URLs mesmo que já estejam marcadas como processadas.",
    )
    parser.add_argument(
        "--max-urls",
        type=int,
        default=0,
        help="Limita o número de URLs desta execução (0 = sem limite).",
    )
    parser.add_argument(
        "--saida-rejeitados",
        default="Rejeitados.csv",
        help="Arquivo de rejeitados da etapa IA (acumulado sem duplicatas).",
    )
    parser.add_argument(
        "--saida-dupla-verificacao",
        default="dupla_verificacao.csv",
        help="Arquivo para revisão manual de aprovações envolvendo Ollama.",
    )
    args = parser.parse_args()

    urls_alvo = []
    if args.url:
        urls_alvo.append(args.url)
    elif args.lote:
        urls_alvo.extend(urls_importadas)
    else:
        parser.error("Informe --url ou --lote")

    arquivo_urls_processadas = obter_arquivo_urls_processadas(args.ia)
    urls_processadas = carregar_urls_processadas(arquivo_urls_processadas)

    if args.lote and not args.ignorar_processadas:
        urls_alvo = [
            url for url in urls_alvo
            if normalizar_url_para_controle(url) not in urls_processadas
        ]

    if args.max_urls > 0:
        urls_alvo = urls_alvo[: args.max_urls]

    emails_aprovados = []
    emails_rejeitados_ia = []
    emails_dupla_verificacao = []
    clientes_ia = configurar_ia() if args.ia else []

    if args.ia and not clientes_ia:
        print("[IA] Sem provedores ativos. Encerrando etapa IA e mantendo brutos para revisão manual.", file=sys.stderr)
        return 0

    ia_indisponivel = False

    for url in urls_alvo:
        emails_brutos, sucesso_coleta = coletar_de_url(url)

        if sucesso_coleta and not args.ignorar_processadas:
            url_normalizada = normalizar_url_para_controle(url)
            if url_normalizada not in urls_processadas:
                registrar_url_processada(url, arquivo_urls_processadas)
                urls_processadas.add(url_normalizada)

        if not emails_brutos:
            continue
        
        if args.ia:
            for email, contexto in emails_brutos.items():
                if not clientes_ia:
                    ia_indisponivel = True
                    break
                if email in emails_aprovados:
                    continue
                aprovado, motivo = validar_com_ia(clientes_ia, email, contexto)
                if aprovado:
                    if motivo == "aprovado_com_ollama":
                        if email not in emails_dupla_verificacao:
                            emails_dupla_verificacao.append(email)
                    else:
                        emails_aprovados.append(email)
                else:
                    if motivo != "sem_decisao_ia" and email not in emails_rejeitados_ia:
                        emails_rejeitados_ia.append(email)

            if ia_indisponivel:
                print("[IA] Provedores indisponíveis durante a execução. Encerrando etapa IA e mantendo brutos para revisão manual.", file=sys.stderr)
                break
        else:
            for email in emails_brutos.keys():
                if email not in emails_aprovados:
                    emails_aprovados.append(email)

        if len(emails_aprovados) >= MAX_EMAILS_POR_EXECUCAO:
            break

    emails_aprovados.sort()
    if emails_aprovados:
        salvar_csv(emails_aprovados, args.saida)

    if args.ia and emails_rejeitados_ia:
        emails_rejeitados_ia.sort()
        salvar_csv_unico_acumulado(emails_rejeitados_ia, args.saida_rejeitados)

    if args.ia and emails_dupla_verificacao:
        emails_dupla_verificacao.sort()
        salvar_csv_unico_acumulado(emails_dupla_verificacao, args.saida_dupla_verificacao)

    return 0

if __name__ == "__main__":
    sys.exit(main())