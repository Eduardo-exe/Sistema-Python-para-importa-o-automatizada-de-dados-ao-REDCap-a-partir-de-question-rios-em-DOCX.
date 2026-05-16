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
    
    # remove underscore after cortar para 25 chars (evita terminar com "_")
    return name[:25].rstrip('_')

def detect_field_type(line, options):
    """Detecta automaticamente o tipo de campo baseado no conteúdo"""
    line_lower = line.lower()
    
    # Se for um título (termina com ".."), retorna 'descriptive' imediatamente
    if '..' in line:
        return 'descriptive'
    
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
    
    # Para campos descriptive - texto descritivo puro
    if field_type == 'descriptive':
        config.update({'field_type': 'descriptive'})
    elif field_type == 'phone':
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
    child_low = child_label.lower().strip()
    
    # Para campos "Qual? Quanto tempo?" que são subperguntas de SIM/NÃO
    if parent_options:
        target_nums = []
        for num, desc in parent_options:
            desc_low = desc.lower()
            if any(k in desc_low for k in ['sim', 'positivo', 'pos', 'yes']):
                target_nums.append(num)
        
        if target_nums:
            return f"[{parent_field_name}] = '{target_nums[0]}'"
    
    # Se child_label inicia com "se sim" -> procura opção com "sim"
    if child_low.startswith('se sim') or child_low.startswith('se não') or child_low.startswith('se nao'):
        for num, desc in parent_options:
            if 'sim' in desc.lower():
                return f"[{parent_field_name}] = '{num}'"
    
    # Se parent_line já menciona 'sim' e child é 'qual', tenta mapear
    if any(k in parent_line.lower() for k in ['sim', 'não', 'nao', 'positivo']) and 'qual' in child_low:
        for num, desc in parent_options:
            if any(k in desc.lower() for k in ['sim', 'positivo']):
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

    # >>> CORREÇÃO: dividir parágrafos em linhas (splitlines) para não perder quebras internas
    paragraphs = []
    for p in doc.paragraphs:
        for line in p.text.splitlines():
            if line.strip():
                paragraphs.append(line.strip())

    # ADICIONA RECORD_ID COMO PRIMEIRO CAMPO
    record_id_field = {
        'variable_name': 'record_id',
        'form_name': 'lipodistrofia',
        'field_type': 'text',
        'field_label': 'Record ID',
        'choices': '',
        'text_validation': '',
        'validation_min': '',
        'validation_max': '',
        'detected_type': 'text',
        'branching_logic': '',
        'section_header': ''
    }
    fields.append(record_id_field)
    used_names.add('record_id')

    i = 0

    while i < len(paragraphs):
        current_line = paragraphs[i]

        # --- DETECTA TÍTULO (SECTION HEADER) ---
        if current_line.endswith(".."):
            title_text = current_line.rstrip(". ").strip()
            
            # Cria um nome de campo único para o título
            title_field_name = clean_field_name(title_text)
            original_name = title_field_name
            counter = 1
            while title_field_name in used_names:
                title_field_name = f"{original_name}_{counter}"[:25].rstrip('_')
                counter += 1
            used_names.add(title_field_name)
            
            # Cria campo descriptive para o título
            fields.append({
                'variable_name': title_field_name,
                'form_name': 'lipodistrofia',
                'field_type': 'descriptive',
                'field_label': title_text[:250],
                'choices': '',
                'text_validation': '',
                'validation_min': '',
                'validation_max': '',
                'detected_type': 'descriptive',
                'branching_logic': '',
                'section_header': ''
            })

            i += 1
            continue

        # Ignora linhas muito longas (prováveis instruções)
        if len(current_line) > 150:
            i += 1
            continue
        
        # Identifica perguntas principais: começam com número ou contêm ":" (mais permissivo)
        if re.match(r'^\d+\.', current_line) or ':' in current_line or re.match(r'^[A-Za-zÀ-ÿ].+\?$', current_line):
            # Extrai texto da pergunta (parte antes de ":" se houver)
            question_text = re.sub(r'^\d+\.\s*', '', current_line)
            if ':' in question_text:
                # Mantém antes de ":" como label principal
                question_label = question_text.split(':')[0].strip()
            else:
                question_label = question_text.strip()
            
            # CORREÇÃO: Verifica se há múltiplas perguntas na mesma linha (separadas por "?" ou ".")
            # Exemplo: "Doenças autoimunes. Qual? Quanto tempo?"
            questions_in_line = []
            
            # Se tiver múltiplas frases terminadas com "?" ou "."
            if '?' in question_text or '.' in question_text:
                # Divide por "?" primeiro
                parts_by_question = question_text.split('?')
                for part in parts_by_question:
                    part = part.strip()
                    if part:
                        # Se ainda tiver ponto, divide por ponto também
                        if '.' in part:
                            subparts = part.split('.')
                            for subpart in subparts:
                                subpart = subpart.strip()
                                if subpart:
                                    questions_in_line.append(subpart)
                        else:
                            questions_in_line.append(part)
            else:
                questions_in_line = [question_label]
            
            print(f"📝 Linha original: '{current_line[:50]}...'")
            print(f"   📋 Perguntas detectadas: {questions_in_line}")
            
            # Processa cada pergunta separadamente
            for q_idx, question_label in enumerate(questions_in_line):
                # Para subperguntas (não a primeira), verifica se é uma continuação
                is_subquestion = q_idx > 0
                
                # Coleta opções nas linhas seguintes (apenas para a PRIMEIRA pergunta)
                options = []
                if q_idx == 0:  # Apenas a primeira pergunta pode ter opções
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
                                options.append((num, desc, parts[1]))  
                            elif '->' in desc:
                                parts = [p.strip() for p in desc.split('->', 1)]
                                desc = parts[0]
                                options.append((num, desc, parts[1]))
                            else:
                                options.append((num, desc, None))
                        j += 1
                else:
                    j = i + 1  # Para subperguntas, não procura opções
                
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
                detected_type = detect_field_type(question_label, normalized_options if q_idx == 0 else [])
                field_config = get_redcap_field_config(detected_type, question_label, normalized_options if q_idx == 0 else [])
                
                # Formata choices para RedCap (apenas para a primeira pergunta)
                choices = ""
                if q_idx == 0 and normalized_options and field_config['field_type'] in ['radio', 'dropdown']:
                    choices = " | ".join([f"{num}, {desc}" for num, desc in normalized_options])
                
                # Se for subpergunta (não a primeira), adiciona branching logic
                branching_logic = ""
                if is_subquestion and q_idx == 1 and questions_in_line[0]:  # Segunda pergunta ligada à primeira
                    # Tenta detectar automaticamente a lógica de branching
                    parent_question = questions_in_line[0]
                    parent_field_name_clean = clean_field_name(parent_question)
                    
                    # Verifica se é uma pergunta SIM/NÃO
                    if any(word in parent_question.lower() for word in ['sim', 'não', 'nao']):
                        # Procura o campo pai correspondente
                        for field in fields[-5:]:  # Procura nos últimos campos
                            if parent_field_name_clean in field.get('variable_name', ''):
                                parent_field_name_actual = field.get('variable_name')
                                # Assumindo que a opção "SIM" é a primeira (1)
                                branching_logic = f"[{parent_field_name_actual}] = '1'"
                                break
                
                # Adiciona campo
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
                    'branching_logic': branching_logic,
                    'section_header': ''
                })
                
                # Processa inline children (subperguntas dentro de opções) - apenas para primeira pergunta
                if q_idx == 0:
                    for parent_num, child_text in inline_children:
                        child_label = child_text
                        child_field_name = clean_field_name(child_label)
                        orig_child = child_field_name
                        ccount = 1
                        while child_field_name in used_names:
                            child_field_name = f"{orig_child}_{ccount}"[:25].rstrip('_')
                            ccount += 1
                        used_names.add(child_field_name)
                        
                        child_type = detect_field_type(child_label, [])
                        child_config = get_redcap_field_config(child_type, child_label, [])
                        
                        branching = f"[{field_name}] = '{parent_num}'"
                        
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
                            'branching_logic': branching,
                            'section_header': ''
                        })
            
            # Depois de processar todas as perguntas da linha, avança para as linhas de opções (se houver)
            if options:  # Se havia opções
                j = i + 1
                while j < len(paragraphs) and re.match(r'^\(\d+\)', paragraphs[j].strip()):
                    j += 1
                i = j
            else:
                i += 1
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
                field.get('variable_name', ''),
                field.get('form_name', 'lipodistrofia'),
                field.get('section_header', ''),  # Section Header
                field.get('field_type', ''),
                field.get('field_label', ''),
                field.get('choices', ''),
                "",
                field.get('text_validation', ''),
                field.get('validation_min', ''),
                field.get('validation_max', ''),
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
    
    # Verifica se há campos
    if not fields:
        problems.append("Nenhum campo encontrado no documento")
        return problems
    
    # Verifica se o primeiro campo é 'text' (requisito do RedCap)
    first_field = fields[0]
    if first_field.get('field_type') != 'text':
        problems.append(f"O primeiro campo deve ser do tipo 'text', mas é '{first_field.get('field_type')}'")
    
    # Verifica se o primeiro campo é record_id
    if first_field.get('variable_name') != 'record_id':
        problems.append(f"O primeiro campo deve ser 'record_id', mas é '{first_field.get('variable_name')}'")
    
    for idx, field in enumerate(fields):
        name = field.get('variable_name', '')
        
        # Verifica se tem nome
        if not name:
            problems.append(f"Linha {idx+2}: Variable name faltando")
            continue
            
        # Verifica se tem field_type
        field_type = field.get('field_type', '')
        if not field_type:
            problems.append(f"Linha {idx+2} ({name}): Field type faltando")
            continue
            
        # Verifica se field_type é válido
        valid_types = ['text', 'notes', 'radio', 'dropdown', 'calc', 'file', 
                      'checkbox', 'yesno', 'truefalse', 'descriptive', 'slider']
        if field_type.lower() not in valid_types:
            problems.append(f"Linha {idx+2} ({name}): Field type inválido '{field_type}'")
            
        # Verifica duplicados
        if name in used_names:
            problems.append(f"Linha {idx+2}: Nome duplicado '{name}'")
        used_names.add(name)
        
        # Verifica formato do nome
        if name.endswith('_'):
            problems.append(f"Linha {idx+2}: Termina com underscore: {name}")
        if re.match(r'^\d', name):
            problems.append(f"Linha {idx+2}: Começa com número: {name}")
        if len(name) > 100:
            problems.append(f"Linha {idx+2}: Muito longo (>100): {name}")
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            problems.append(f"Linha {idx+2}: Formato inválido: {name}")
            
        # Verifica se tem field_label (opcional, mas recomendado)
        if not field.get('field_label', ''):
            problems.append(f"Linha {idx+2} ({name}): Field label faltando (recomendado)")
    
    return problems

# EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    input_file = "Dados de Identificação e Sociodemográficos.docx"           
    output_file = "redcap_final.csv"
    
    print("📖 Lendo documento Word...")
    fields = parse_document(input_file)
    
    print("✅ Validação dos campos...")
    problems = validate_fields(fields)
    if problems:
        print("❌ Problemas encontrados (lista):")
        for problem in problems[:20]:  # Mostra apenas os primeiros 20 problemas
            print(f"   - {problem}")
        if len(problems) > 20:
            print(f"   ... e mais {len(problems)-20} problemas")
        print("\n🔄 Nota: O parser tentou evitar duplicatas, verifique manualmente os nomes conflitantes.")
    else:
        print("✅ Todos os campos estão válidos!")
    
    print("\n💾 Gerando CSV RedCap...")
    create_redcap_csv(fields, output_file)
    
    print(f"\n🎉 CONCLUÍDO! Arquivo: {output_file}")
    print(f"📊 Total de campos: {len(fields)}")
    
    # Mostra informações sobre os primeiros campos
    print(f"\n🔍 Primeiros 15 campos gerados:")
    for i, field in enumerate(fields[:15]):
        var_name = field.get('variable_name', '')
        field_type = field.get('field_type', '')
        field_label = field.get('field_label', '')[:40]
        br = field.get('branching_logic', '')
        
        type_icon = "🏷️ " if field_type == 'descriptive' else "📝"
        br_text = f" | BRANCH: {br}" if br else ""
        
        print(f"   {i+1:2d}. {type_icon}{var_name:25} ({field_type:12}) → {field_label}...{br_text}")
    
    # Conta tipos de campos
    type_counts = {}
    for field in fields:
        field_type = field.get('field_type', 'unknown')
        type_counts[field_type] = type_counts.get(field_type, 0) + 1
    
    print(f"\n📈 Estatísticas dos tipos de campo:")
    for tipo, count in sorted(type_counts.items()):
        icon = "🏷️ " if tipo == 'descriptive' else "📝"
        print(f"   - {icon}{tipo:15}: {count:3} campos")