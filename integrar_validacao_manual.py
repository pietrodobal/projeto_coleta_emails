#!/usr/bin/env python3
"""
Integra resultado da validação manual.
- Adiciona válidos ao emails_validados.csv
- Adiciona rejeitados ao Rejeitados.csv
"""

import csv

# Emails validados manualmente
VALIDADOS = {
    "comunicados.facartes@ucuenca.edu.ec",
    "diploma.discapacidad@cienciassociales.edu.uy",
    "diplomaestudiosurbanos@cienciassociales.edu.uy",
    "diplomaps@cienciassociales.edu.uy",
    "direccion-pl34@cobach34alansacjun.edu.mx",
    "info.artesyhumanidades@cu.ucsg.edu.ec",
    "maestria.cpolit@cienciassociales.edu.uy",
    "maestria.dts@cienciassociales.edu.uy",
    "marlene.gomez@cienciassociales.edu.uy",
    "posgradofaces@uas.edu.mx",
    "secaoalunosfilosofia@usp.br",
    "solicitudesposgrados@cienciassociales.edu.uy",
}

def integrar():
    print("\n" + "="*60)
    print("INTEGRANDO VALIDAÇÃO MANUAL")
    print("="*60 + "\n")
    
    # Ler arquivos atuais
    with open("saida/emails_validados.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        validados_atuais = list(reader)
    
    with open("saida/Rejeitados.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        header_rej = reader.fieldnames
        rejeitados_atuais = list(reader)
    
    # Ler arquivo de validação manual
    with open("saida/VALIDACAO_MANUAL_254_EMAILS.csv", 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        todos_manuais = list(reader)
    
    print(f"📊 Estado antes:")
    print(f"   Validados: {len(validados_atuais)}")
    print(f"   Rejeitados: {len(rejeitados_atuais)}")
    print(f"   Manuais analisados: {len(todos_manuais)}")
    print()
    
    # Separar válidos e rejeitados do arquivo manual
    novos_validados = []
    novos_rejeitados = []
    
    for row in todos_manuais:
        email = row.get('email_validado', '').strip()
        if not email:
            continue
        
        if email in VALIDADOS:
            novos_validados.append({'email_validado': email})
        else:
            novos_rejeitados.append({'email_validado': email})
    
    print(f"📋 Resultado da análise:")
    print(f"   Válidos encontrados: {len(novos_validados)}")
    print(f"   Rejeitados encontrados: {len(novos_rejeitados)}")
    print()
    
    # Mesclar e dedupllicar validados
    todos_validados = validados_atuais + novos_validados
    conjunto_valido = {}
    for row in todos_validados:
        email = row.get('email_validado', '').strip()
        if email and email not in conjunto_valido:
            conjunto_valido[email] = row
    
    # Mesclar e deduplicar rejeitados
    todos_rejeitados = rejeitados_atuais + novos_rejeitados
    conjunto_rejeitado = {}
    for row in todos_rejeitados:
        email = row.get('email_validado', '').strip()
        if email and email not in conjunto_rejeitado:
            conjunto_rejeitado[email] = row
    
    # Salvar
    fieldnames_valido = header or ['email_validado']
    with open("saida/emails_validados.csv", 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_valido)
        writer.writeheader()
        writer.writerows(list(conjunto_valido.values()))
    
    fieldnames_rejeitado = header_rej or ['email_validado']
    with open("saida/Rejeitados.csv", 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames_rejeitado)
        writer.writeheader()
        writer.writerows(list(conjunto_rejeitado.values()))
    
    print(f"✅ Estado depois:")
    print(f"   Validados: {len(conjunto_valido)}")
    print(f"   Rejeitados: {len(conjunto_rejeitado)}")
    print()
    print(f"📈 Resumo:")
    print(f"   ✓ +{len(novos_validados)} validados")
    print(f"   ✓ +{len(novos_rejeitados)} rejeitados")
    print("="*60 + "\n")

if __name__ == "__main__":
    integrar()
