"""
Testes para o módulo coleta_emails.
"""

import csv
import os

import pytest

from coleta_emails import (
    extrair_emails_de_texto,
    normalizar_email,
    organizar_emails,
    salvar_csv,
    validar_email,
    PASTA_SAIDA,
)


# ---------------------------------------------------------------------------
# Extração
# ---------------------------------------------------------------------------

class TestExtrairEmailsDeTexto:
    def test_extrai_email_simples(self):
        assert extrair_emails_de_texto("contato@empresa.com") == ["contato@empresa.com"]

    def test_extrai_multiplos_emails(self):
        texto = "Fale com joao@teste.com ou maria@exemplo.com.br para mais informações."
        resultado = extrair_emails_de_texto(texto)
        assert "joao@teste.com" in resultado
        assert "maria@exemplo.com.br" in resultado

    def test_texto_sem_email(self):
        assert extrair_emails_de_texto("Nenhum email aqui.") == []

    def test_extrai_email_em_meio_a_html(self):
        html = '<a href="mailto:dev@projeto.io">dev@projeto.io</a>'
        resultado = extrair_emails_de_texto(html)
        assert "dev@projeto.io" in resultado


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------

class TestValidarEmail:
    def test_email_valido(self):
        assert validar_email("usuario@dominio.com") is True

    def test_email_com_subdominio(self):
        assert validar_email("user@mail.empresa.com.br") is True

    def test_email_sem_arroba(self):
        assert validar_email("usuariodominio.com") is False

    def test_email_sem_dominio(self):
        assert validar_email("usuario@") is False

    def test_email_vazio(self):
        assert validar_email("") is False

    def test_email_com_espacos(self):
        assert validar_email("  usuario@dominio.com  ") is True  # normaliza antes


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

class TestNormalizarEmail:
    def test_converte_para_minusculas(self):
        assert normalizar_email("USUARIO@DOMINIO.COM") == "usuario@dominio.com"

    def test_remove_espacos(self):
        assert normalizar_email("  email@teste.com  ") == "email@teste.com"


# ---------------------------------------------------------------------------
# Organização
# ---------------------------------------------------------------------------

class TestOrganizarEmails:
    def test_remove_duplicatas(self):
        emails = ["a@b.com", "a@b.com", "c@d.com"]
        assert organizar_emails(emails) == ["a@b.com", "c@d.com"]

    def test_normaliza_e_deduplica(self):
        emails = ["A@B.COM", "a@b.com"]
        assert organizar_emails(emails) == ["a@b.com"]

    def test_ordena_alfabeticamente(self):
        emails = ["z@z.com", "a@a.com", "m@m.com"]
        assert organizar_emails(emails) == ["a@a.com", "m@m.com", "z@z.com"]

    def test_filtra_invalidos(self):
        emails = ["valido@ok.com", "invalido", "@semlocal.com"]
        assert organizar_emails(emails) == ["valido@ok.com"]

    def test_lista_vazia(self):
        assert organizar_emails([]) == []


# ---------------------------------------------------------------------------
# Exportação CSV
# ---------------------------------------------------------------------------

class TestSalvarCsv:
    def test_cria_arquivo_csv(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        emails = ["a@a.com", "b@b.com"]
        salvar_csv(emails, "teste.csv")

        caminho = tmp_path / PASTA_SAIDA / "teste.csv"
        assert caminho.exists()

        with open(caminho, newline="", encoding="utf-8") as f:
            linhas = list(csv.reader(f))

        assert linhas[0] == ["email"]
        assert ["a@a.com"] in linhas
        assert ["b@b.com"] in linhas

    def test_csv_vazio_apenas_cabecalho(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        salvar_csv([], "vazio.csv")

        caminho = tmp_path / PASTA_SAIDA / "vazio.csv"
        with open(caminho, newline="", encoding="utf-8") as f:
            linhas = list(csv.reader(f))

        assert linhas == [["email"]]
