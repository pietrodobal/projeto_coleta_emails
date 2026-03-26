#!/usr/bin/env python3
"""
Consolida dados da faculdade com dados da casa.
Mescla emails validados e rejeitados, remove duplicatas.
Usa apenas csv stdlib (sem pandas).
"""

import csv

# Diretórios
CASA = "saida"
FACULDADE = "saida_faculdade"

def ler_csv(arquivo):
    """Lê CSV e retorna (header, rows)."""
    with open(arquivo, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    return header, rows

def salvar_csv(arquivo, header, rows):
    """Salva CSV com header e rows."""
    with open(arquivo, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)

def consolidar_validados():
    """Consolida emails validados."""
    print("📧 Consolidando validados...")
    
    # Ler arquivos
    header, casa_rows = ler_csv(f"{CASA}/emails_validados.csv")
    print(f"   Casa: {len(casa_rows)} validados")
    
    _, recuperados_rows = ler_csv(f"{FACULDADE}/a_validar_recuperado_apenas_pendentes.csv")
    print(f"   Faculdade (recuperados): {len(recuperados_rows)} validados")
    
    # Mesclar
    consolidado = casa_rows + recuperados_rows
    
    # Remover duplicatas (manter primeira ocorrência)
    vistos = set()
    consolidado_limpo = []
    duplicatas = 0
    for row in consolidado:
        email = row.get('email_validado', '').strip()
        if email not in vistos:
            vistos.add(email)
            consolidado_limpo.append(row)
        else:
            duplicatas += 1
    
    print(f"   ✓ Total após consolidação: {len(consolidado_limpo)} validados")
    print(f"   ✓ Duplicatas removidas: {duplicatas}")
    
    # Salvar
    salvar_csv(f"{CASA}/emails_validados.csv", header, consolidado_limpo)
    print(f"   ✓ Salvo em {CASA}/emails_validados.csv\n")
    
    return len(consolidado_limpo)


def consolidar_rejeitados():
    """Consolida emails rejeitados."""
    print("❌ Consolidando rejeitados...")
    
    # Ler arquivos
    header, casa_rows = ler_csv(f"{CASA}/Rejeitados.csv")
    print(f"   Casa: {len(casa_rows)} rejeitados")
    
    _, faculdade_rows = ler_csv(f"{FACULDADE}/Rejeitados.csv")
    print(f"   Faculdade: {len(faculdade_rows)} rejeitados")
    
    # Mesclar
    consolidado = casa_rows + faculdade_rows
    
    # Remover duplicatas
    vistos = set()
    consolidado_limpo = []
    duplicatas = 0
    col_email = (header or ['email_validado'])[0]  # Primeira coluna é email (fallback)
    for row in consolidado:
        email = row.get(col_email, '').strip()
        if email not in vistos:
            vistos.add(email)
            consolidado_limpo.append(row)
        else:
            duplicatas += 1
    
    print(f"   ✓ Total após consolidação: {len(consolidado_limpo)} rejeitados")
    print(f"   ✓ Duplicatas removidas: {duplicatas}")
    
    # Salvar
    salvar_csv(f"{CASA}/Rejeitados.csv", header, consolidado_limpo)
    print(f"   ✓ Salvo em {CASA}/Rejeitados.csv\n")
    
    return len(consolidado_limpo)


if __name__ == "__main__":
    print("\n" + "="*60)
    print("CONSOLIDAÇÃO FACULDADE + CASA")
    print("="*60 + "\n")
    
    validados_total = consolidar_validados()
    rejeitados_total = consolidar_rejeitados()
    
    print("="*60)
    print(f"✅ CONSOLIDAÇÃO COMPLETA")
    print(f"   📊 Total validados: {validados_total}")
    print(f"   📊 Total rejeitados: {rejeitados_total}")
    print("="*60 + "\n")
