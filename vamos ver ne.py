# -*- coding: utf-8 -*-
"""
Parser DOCX -> RedCap CSV
Inclui detecção automática de ramificação (branching logic) para subperguntas tipo "Qual?"
e opções inline do tipo "Positivo → Qual?".
Referência de arquivo enviado (imagem): /mnt/data/50fb836a-7b76-4946-905f-e46c25421085.png
"""

from docx import Document
import csv
import re
import unidecode

def clean_field_name(name):
    """Limpa nomes para padrão RedCap"""
    name = unidecode.unidecode(name)
    name = re.sub(r'^\d+\.?\s*', '', name)  # Remove "1. ", "2. " etc
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)  # Remove pontuação
    name = re.sub(r'\s+', '_', name)  # Espaços para underscore
    name = name.rstrip('_')
    
    abbrevs = {
        'quanto_tempo': 'tempo',
        'medicacao': 'med',
        'medicamento': 'med',
        'doencas_autoimunes': 'autoimune',
        'doenca_cardiovascular': 'dcv',
        'circunferencia': 'circ',
        'pressao_arterial': 'pa',
        'ultrassonografia': 'us',
        'ancestralidade': 'anc',
        'retinopatia': 'retina',
        'diastolica': 'dias',
        'sistolica': 'sist'
    }
    for long, short in abbrevs.items():
        name = name.replace(long, short)
    
    if re.match(r'^\d', name):
        name = 'q_' + name
    
    return name[:25]

def detect_field_type(line, options):
    """Detecta automaticamente o tipo de campo baseado no conteúdo"""
    line_lower = line.lower()
    
    if options:
        if len(options) <= 5:
            return 'radio'
        else:
            return 'dropdown'
    
    if any(word in line_lower for word in ['telefone', 'celular', 'cel', 'fone', 'whatsapp', 'contato']):
        return 'phone'
    
    data_keywords = [
        'data de nascimento', 'data de diagnóstico', 'data diagnostico',
        'data de início', 'data de inicio', 'data de fim',
        'data de entrada', 'data de saída', 'data de saida',
        'data de cirurgia', 'data'
    ]
    if any(keyword in line_lower for keyword in data_keywords):
        return 'date'
    
    if any(word in line_lower for word in ['email', 'e-mail', 'correio eletrônico']):
        return 'email'
    
    number_keywords = [
        'idade', 'peso', 'altura', 'kg', 'cm', 'metros', 'quilogramas',
        'pressão arterial', 'pressao arterial', 'temperatura', 'frequência', 'frequencia',
        'número', 'numero', 'quantidade', 'qtd', 'valor', 'percentual',
        'porcentagem', '%', 'ancestralidade'
    ]
    if any(keyword in line_lower for keyword in number_keywords):
        return 'number'
    
    if 'pressão arterial' in line_lower or 'pressao arterial' in line_lower:
        if 'diastólica' in line_lower or 'diastolica' in line_lower:
            return 'number'
        elif 'sistólica' in line_lower or 'sistolica' in line_lower:
            return 'number'
        else:
            return 'text'
    
    if (any(word in line_lower for word in ['sim', 'não', 'nao']) and 
        len(line_lower.split()) < 15 and
        not any(word in line_lower for word in ['descreva', 'explique', 'justifique'])):
        return 'yesno'
    
    if any(word in line_lower for word in ['cep', 'código postal', 'codigo postal']):
        return 'zipcode'
    
    if any(word in line_lower for word in ['cpf', 'cnpj', 'rg', 'identidade']):
        return 'cpf'
    
    notes_keywords = [
        'descreva', 'observação', 'observacao', 'comentário', 'comentario',
        'justifique', 'explique', 'detalhe', 'informe', 'relate', 'descrever'
    ]
    if any(keyword in line_lower for keyword in notes_keywords):
        return 'notes'
    
    return 'text'

def get_redcap_field_config(field_type, line, options):
    """Retorna configuração completa do campo para RedCap"""
    line_lower = line.lower()
    config = {
        'field_type': 'text',
        'text_validation': '',
        'min': '',
        'max': ''
    }
    if field_type == 'phone':
        config.update({'field_type': 'text','text_validation': 'phone'})
    elif field_type == 'date':
        config.update({'field_type': 'text','text_validation': 'date_dmy'})
    elif field_type == 'email':
        config.update({'field_type': 'text','text_validation': 'email'})
    elif field_type == 'number':
        config.update({'field_type': 'text','text_validation': 'number','min': '0','max': ''})
        if 'idade' in line_lower:
            config.update({'min': '0', 'max': '120'})
        elif 'peso' in line_lower:
            config.update({'min': '0', 'max': '300'})
        elif 'altura' in line_lower:
            config.update({'min': '0', 'max': '250'})
        elif 'pressão arterial' in line_lower or 'pressao arterial' in line_lower:
            if 'diastólica' in line_lower or 'diastolica' in line_lower:
                config.update({'min': '0', 'max': '200'})
            elif 'sistólica' in line_lower or 'sistolica' in line_lower:
                config.update({'min': '0', 'max': '300'})
        elif 'ancestralidade' in line_lower or 'percentual' in line_lower or '%' in line_lower:
            config.update({'min': '0', 'max': '100'})
    elif field_type == 'yesno':
        config.update({'field_type': 'yesno'})
    elif field_type == 'zipcode':
        config.update({'field_type': 'text','text_validation': 'zipcode'})
    elif field_type == 'cpf':
        config.update({'field_type': 'text','text_validation': 'cpf'})
    elif field_type == 'notes':
        config.update({'field_type': 'notes'})
    elif field_type in ['radio', 'dropdown']:
        config.update({'field_type': field_type})
    return config

def detect_branching_logic(parent_field_name, parent_options, child_label, parent_line):
    """
    Decide a lógica de ramificação baseada no rótulo do filho ou no contexto.
    Retorna string no formato: "[parent_field] = 'n'" ou "" se não detectar.
    """
    # Normaliza
    child_low = child_label.lower().strip()
    # Caso clássico: "qual" ou "qual?" aparece -> assume que está atrelado a opção "positivo" ou "sim"
    # Procura em parent_options por palavras-chave
    target_nums = []
    for num, desc in parent_options:
        desc_low = desc.lower()
        if any(k in desc_low for k in ['positivo', 'pos', 'sim', 'yes']):
            target_nums.append(num)
    # Se encontrou numeros alvo, retorna primeira correspondência
    if target_nums:
        return f"[{parent_field_name}] = '{target_nums[0]}'"
    
    # Se child_label inicia com "se sim" -> procura opção com "sim"
    if child_low.startswith('se sim') or child_low.startswith('se não') or child_low.startswith('se nao'):
        for num, desc in parent_options:
            if 'sim' in desc.lower():
                return f"[{parent_field_name}] = '{num}'"
    
    # Se parent_line já menciona 'positivo' e child é 'qual', tenta mapear
    if 'positivo' in parent_line.lower() and 'qual' in child_low:
        for num, desc in parent_options:
            if 'positivo' in desc.lower():
                return f"[{parent_field_name}] = '{num}'"
    
    # fallback: se existir apenas 2 opções e uma contém 'sim' ou 'positivo', usa essa
    if len(parent_options) == 2:
        for num, desc in parent_options:
            if any(k in desc.lower() for k in ['sim', 'positivo', 'pos']):
                return f"[{parent_field_name}] = '{num}'"
    
    return ""

def parse_document(doc_path):
    doc = Document(doc_path)
    fields = []
    used_names = set()
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    i = 0

    while i < len(paragraphs):
        current_line = paragraphs[i]
        
        # Ignora linhas muito longas (prováveis instruções)
        if len(current_line) > 150:
            i += 1
            continue
        
        # Identifica perguntas principais: começam com número ou contém ":" (mais permissivo)
        if re.match(r'^\d+\.', current_line) or ':' in current_line or re.match(r'^[A-Za-zÀ-ÿ].+\?$', current_line):
            # Extrai texto da pergunta (parte antes de ":" se houver)
            question_text = re.sub(r'^\d+\.\s*', '', current_line)
            if ':' in question_text:
                # Mantém antes de ":" como label principal
                question_label = question_text.split(':')[0].strip()
            else:
                question_label = question_text.strip()
            
            # Coleta opções nas linhas seguintes no formato "(1) Texto"
            options = []
            j = i + 1
            while j < len(paragraphs) and re.match(r'^\(\d+\)', paragraphs[j].strip()):
                option_match = re.match(r'^\((\d+)\)\s*(.+)', paragraphs[j].strip())
                if option_match:
                    num = option_match.group(1)
                    desc = option_match.group(2).strip()
                    # Detecta se opção contém "→" ou "->" indicando subpergunta inline
                    if '→' in desc:
                        parts = [p.strip() for p in desc.split('→', 1)]
                        desc = parts[0]
                        # Anota o texto do filho inline na própria lista (guardamos após processamento)
                        
                        options.append((num, desc, parts[1]))  
                    elif '->' in desc:
                        parts = [p.strip() for p in desc.split('->', 1)]
                        desc = parts[0]
                        options.append((num, desc, parts[1]))
                    else:
                        options.append((num, desc, None))
                j += 1
            
            # Normaliza estrutura de options para (num, desc) e keep inline map
            normalized_options = []
            inline_children = []  
            for entry in options:
                if len(entry) == 3:
                    num, desc, inline = entry
                    normalized_options.append((num, desc))
                    if inline:
                        inline_children.append((num, inline))
                else:
                    normalized_options.append(entry)
            
            # Gera nome do campo principal
            field_name = clean_field_name(question_label)
            original_name = field_name
            counter = 1
            while field_name in used_names:
                field_name = f"{original_name}_{counter}"[:25].rstrip('_')
                counter += 1
            used_names.add(field_name)
            
            # Detecta tipo e configuração
            detected_type = detect_field_type(current_line, normalized_options)
            field_config = get_redcap_field_config(detected_type, current_line, normalized_options)
            # Formata choices para RedCap
            choices = ""
            if normalized_options and field_config['field_type'] in ['radio', 'dropdown']:
                choices = " | ".join([f"{num}, {desc}" for num, desc in normalized_options])
            
            # Inicialmente sem lógica de ramificação para o campo pai
            fields.append({
                'variable_name': field_name,
                'form_name': 'lipodistrofia',
                'field_type': field_config['field_type'],
                'field_label': question_label[:250],
                'choices': choices,
                'text_validation': field_config['text_validation'],
                'validation_min': field_config['min'],
                'validation_max': field_config['max'],
                'detected_type': detected_type,
                'branching_logic': ''
            })
            
            # Agora, verifica se logo após (j) há uma subpergunta do tipo "Qual?"
            # ou se existiram inline children que já indicam subpergunta
            # Primeiro trata inline children
            # Primeiro trata inline children (AGORA CORRIGIDO)
            for parent_num, child_text in inline_children:

                # divide por interrogações
                sub_questions = [q.strip() for q in child_text.split('?') if q.strip()]

                for sq in sub_questions:
                    label = sq + "?"  # restaura o ?
                    field_base = clean_field_name(sq)

                    if not field_base:
                        continue

                    child_field_name = field_base
                    orig = child_field_name
                    count = 1

                    # evita campos duplicados
                    while child_field_name in used_names:
                        child_field_name = f"{orig}_{count}"[:25].rstrip('_')
                        count += 1
                    used_names.add(child_field_name)

                    child_type = detect_field_type(label, [])
                    child_config = get_redcap_field_config(child_type, label, [])

                    branching = f"[{field_name}] = '{parent_num}'"

                    fields.append({
                        'variable_name': child_field_name,
                        'form_name': 'lipodistrofia',
                        'field_type': child_config['field_type'],
                        'field_label': label[:250],
                        'choices': '',
                        'text_validation': child_config['text_validation'],
                        'validation_min': child_config['min'],
                        'validation_max': child_config['max'],
                        'detected_type': child_type,
                        'branching_logic': branching
                    })

            
            # Depois trata subpergunta em linha abaixo (ex.: "Qual?" sozinho)
            if j < len(paragraphs):
                below = paragraphs[j].strip()
                # condição para considerar como subpergunta: curto e contém 'qual' ou começa com 'se '
                if (re.match(r'^[Qq]ual\??$', below) or re.match(r'^[Ss]e\s+', below) 
                    or (below.endswith('?') and len(below.split()) <= 4 and normalized_options)):
                    # Decide a lógica de branching automaticamente
                    branching_logic = detect_branching_logic(field_name, normalized_options, below, current_line)
                    if branching_logic:
                        # Cria campo filho
                        child_label = below
                        child_field_name = clean_field_name(child_label)
                        orig_child = child_field_name
                        ccount = 1
                        while child_field_name in used_names:
                            child_field_name = f"{orig_child}_{ccount}"[:25].rstrip('_')
                            ccount += 1
                        used_names.add(child_field_name)
                        
                        child_type = detect_field_type(child_label, [])
                        child_config = get_redcap_field_config(child_type, child_label, [])
                        
                        fields.append({
                            'variable_name': child_field_name,
                            'form_name': 'lipodistrofia',
                            'field_type': child_config['field_type'],
                            'field_label': child_label[:250],
                            'choices': '',
                            'text_validation': child_config['text_validation'],
                            'validation_min': child_config['min'],
                            'validation_max': child_config['max'],
                            'detected_type': child_type,
                            'branching_logic': branching_logic
                        })
                        # Pula a linha do filho já processada
                        j += 1
            
            # Avança i para pular as linhas de opções e possivelmente o filho
            i = j
        else:
            i += 1
    
    return fields

def create_redcap_csv(fields, output_path):
    """Cria CSV no formato exato do RedCap, incluindo Branching Logic"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Variable / Field Name", "Form Name", "Section Header", 
            "Field Type", "Field Label", 
            "Choices, Calculations, OR Slider Labels",
            "Field Note", "Text Validation Type OR Show Slider Number",
            "Text Validation Min", "Text Validation Max", "Identifier?",
            "Branching Logic (Show field only if...)", "Required Field?",
            "Custom Alignment", "Question Number (surveys only)",
            "Matrix Group Name", "Matrix Ranking?", "Field Annotation"
        ])
        for field in fields:
            writer.writerow([
                field['variable_name'],      
                field['form_name'],          
                "",                          
                field['field_type'],         
                field['field_label'],        
                field['choices'],            
                "",                          
                field['text_validation'],  
                field['validation_min'],     
                field['validation_max'],     
                "",                          
                field.get('branching_logic', ''),  
                "",                          
                "",                         
                "",                          
                "",                          
                "",                          
                ""                           
            ])

def validate_fields(fields):
    """Valida os campos antes de gerar CSV"""
    problems = []
    used_names = set()
    for field in fields:
        name = field['variable_name']
        if name in used_names:
            problems.append(f"Duplicado: {name}")
        used_names.add(name)
        if name.endswith('_'):
            problems.append(f"Termina com underscore: {name}")
        if re.match(r'^\d', name):
            problems.append(f"Começa com número: {name}")
        if len(name) > 100:
            problems.append(f"Muito longo (>100): {name}")
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            problems.append(f"Formato inválido: {name}")
    return problems

# EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    input_file = "1.docx"           
    output_file = "redcap_final.csv"
    
    print("📖 Lendo documento Word...")
    fields = parse_document(input_file)
    
    print("✅ Validação dos campos...")
    problems = validate_fields(fields)
    if problems:
        print("❌ Problemas encontrados (lista):")
        for problem in problems:
            print(f"   - {problem}")
        print("🔄 Nota: O parser tentou evitar duplicatas, verifique manualmente os nomes conflitantes.")
    
    print("💾 Gerando CSV RedCap...")
    create_redcap_csv(fields, output_file)
    
    print(f"🎉 CONCLUÍDO! Arquivo: {output_file}")
    print(f"📊 Total de campos: {len(fields)}")
    
    print("\n🔍 Primeiros 30 campos (com tipos detectados e branching):")
    for i, field in enumerate(fields[:30]):
        br = f" | BRANCH: {field.get('branching_logic')}" if field.get('branching_logic') else ""
        val = f" | {field['text_validation']}" if field['text_validation'] else ""
        print(f"   {i+1:2d}. {field['variable_name']:25} ({field['field_type']:8}) → {field['detected_type']:10}{val}{br}")
    
    # Estatísticas dos tipos detectados
    type_counts = {}
    for field in fields:
        detected = field['detected_type']
        type_counts[detected] = type_counts.get(detected, 0) + 1
    print(f"\n📈 Estatísticas dos tipos detectados:")
    for tipo, count in sorted(type_counts.items()):
        print(f"   - {tipo:12}: {count:3} campos")
