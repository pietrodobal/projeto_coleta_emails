import csv
import os
import pytest
from unittest.mock import patch, MagicMock

# Importa as funções atualizadas do script principal
from coleta_emails import (
    normalizar_email,
    extrair_emails_com_contexto,
    validar_com_ia,
    salvar_csv,
    PASTA_SAIDA
)

# ---------------------------------------------------------------------------
# Testes de Normalização e Extração
# ---------------------------------------------------------------------------

def test_normalizar_email():
    assert normalizar_email("  DOCENTE@UBA.AR  ") == "docente@uba.ar"
    assert normalizar_email("contato@uff.br") == "contato@uff.br"

def test_extrair_emails_com_contexto():
    texto_html = """
    Bem-vindo ao departamento. Fale com a coordenação em coord@letras.uba.ar para 
    matrículas. O suporte de TI é ti@uba.ar e atende das 9h às 18h.
    """
    resultado = extrair_emails_com_contexto(texto_html)
    
    # Verifica se extraiu os e-mails corretamente sem duplicatas
    assert "coord@letras.uba.ar" in resultado
    assert "ti@uba.ar" in resultado
    
    # Verifica se capturou o contexto (palavras ao redor)
    assert "coordenação em coord@letras.uba.ar para" in resultado["coord@letras.uba.ar"]

# ---------------------------------------------------------------------------
# Testes com Mock da IA (Custo Zero)
# ---------------------------------------------------------------------------

@patch('coleta_emails.time.sleep') # Impede o sleep de atrasar o teste
def test_validar_com_ia_aprovado(mock_sleep):
    # Simula o modelo LLM
    mock_modelo = MagicMock()
    mock_resposta = MagicMock()
    mock_resposta.text = "S" # IA responde SIM
    mock_modelo.generate_content.return_value = mock_resposta
    
    resultado = validar_com_ia(mock_modelo, "docente@artes.edu", "Professor titular de cinema")
    
    assert resultado is True
    mock_modelo.generate_content.assert_called_once()
    mock_sleep.assert_called_once_with(1)

@patch('coleta_emails.time.sleep')
def test_validar_com_ia_reprovado(mock_sleep):
    # Simula o modelo LLM
    mock_modelo = MagicMock()
    mock_resposta = MagicMock()
    mock_resposta.text = "N" # IA responde NÃO
    mock_modelo.generate_content.return_value = mock_resposta
    
    resultado = validar_com_ia(mock_modelo, "ti@universidade.edu", "Suporte técnico de computadores")
    
    assert resultado is False
    mock_modelo.generate_content.assert_called_once()

# ---------------------------------------------------------------------------
# Testes de Exportação
# ---------------------------------------------------------------------------

def test_salvar_csv(tmp_path, monkeypatch):
    # Redireciona o diretório de trabalho para uma pasta temporária do pytest
    monkeypatch.chdir(tmp_path)
    emails_validados = ["prof1@uba.ar", "secretaria@ufj.br"]
    
    salvar_csv(emails_validados, "teste_saida.csv")
    caminho_arquivo = tmp_path / PASTA_SAIDA / "teste_saida.csv"
    
    assert caminho_arquivo.exists()
    
    with open(caminho_arquivo, newline="", encoding="utf-8") as f:
        linhas = list(csv.reader(f))
        
    assert linhas[0] == ["email_validado"]
    assert ["prof1@uba.ar"] in linhas
    assert ["secretaria@ufj.br"] in linhas