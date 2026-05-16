from docx import Document
import csv
import re
import unidecode

def clean_field_name(name):
    """Limpa nomes para padrão RedCap"""
    # Remove acentos e converte para ASCII
    name = unidecode.unidecode(name)
    
    # Remove números do início, pontuação, espaços
    name = re.sub(r'^\d+\.?\s*', '', name)  # Remove "1. ", "2. " etc
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)  # Remove pontuação
    name = re.sub(r'\s+', '_', name)  # Espaços para underscore
    
    # Remove underscores no final
    name = name.rstrip('_')
    
    # Abreviações comuns para nomes longos
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
    
    # Garante que não começa com número
    if re.match(r'^\d', name):
        name = 'q_' + name
    
    return name[:25]  # Limita a 25 caracteres

def detect_field_type(line, options):
    """Detecta automaticamente o tipo de campo baseado no conteúdo"""
    line_lower = line.lower()
    
    # Primeiro verifica se tem opções de múltipla escolha
    if options:
        if len(options) <= 5:
            return 'radio'
        else:
            return 'dropdown'
    
    # Detecção de campos especiais - SIMPLIFICADO E CORRIGIDO
    # TELEFONE - só detecta se for a palavra principal
    if any(word in line_lower for word in ['telefone', 'celular', 'cel', 'fone', 'whatsapp', 'contato']):
        return 'phone'
    
    # DATA - só detecta se for sobre datas específicas - CORRIGIDO E SIMPLIFICADO
    data_keywords = [
        'data de nascimento', 'data de diagnóstico', 'data diagnostico',
        'data de início', 'data de inicio', 'data de fim',
        'data de entrada', 'data de saída', 'data de saida',
        'data de cirurgia', 'data'
    ]
    if any(keyword in line_lower for keyword in data_keywords):
        return 'date'
    
    # EMAIL
    if any(word in line_lower for word in ['email', 'e-mail', 'correio eletrônico']):
        return 'email'
    
    # NÚMERO (incluindo idade, peso, altura, etc.)
    number_keywords = [
        'idade', 'peso', 'altura', 'kg', 'cm', 'metros', 'quilogramas',
        'pressão arterial', 'pressao arterial', 'temperatura', 'frequência', 'frequencia',
        'número', 'numero', 'quantidade', 'qtd', 'valor', 'percentual',
        'porcentagem', '%', 'ancestralidade'
    ]
    
    if any(keyword in line_lower for keyword in number_keywords):
        return 'number'
    
    # Pressão arterial - caso específico
    if 'pressão arterial' in line_lower or 'pressao arterial' in line_lower:
        if 'diastólica' in line_lower or 'diastolica' in line_lower:
            return 'number'
        elif 'sistólica' in line_lower or 'sistolica' in line_lower:
            return 'number'
        else:
            return 'text'
    
    # SIM/NÃO - só quando é claramente uma pergunta binária
    if (any(word in line_lower for word in ['sim', 'não', 'nao']) and 
        len(line_lower.split()) < 15 and
        not any(word in line_lower for word in ['descreva', 'explique', 'justifique'])):
        return 'yesno'
    
    # CEP
    if any(word in line_lower for word in ['cep', 'código postal', 'codigo postal']):
        return 'zipcode'
    
    # CPF
    if any(word in line_lower for word in ['cpf', 'cnpj', 'rg', 'identidade']):
        return 'cpf'
    
    # NOTAS/TEXTO LONGO
    notes_keywords = [
        'descreva', 'observação', 'observacao', 'comentário', 'comentario',
        'justifique', 'explique', 'detalhe', 'informe', 'relate', 'descrever'
    ]
    
    if any(keyword in line_lower for keyword in notes_keywords):
        return 'notes'
    
    # TEXTO CURTO (padrão)
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
        config.update({
            'field_type': 'text',
            'text_validation': 'phone',
            'min': '',
            'max': ''
        })
    elif field_type == 'date':
        config.update({
            'field_type': 'text',
            'text_validation': 'date_dmy',  # Formato dia/mês/ano
            'min': '',
            'max': ''
        })
    elif field_type == 'email':
        config.update({
            'field_type': 'text',
            'text_validation': 'email',
            'min': '',
            'max': ''
        })
    elif field_type == 'number':
        config.update({
            'field_type': 'text',
            'text_validation': 'number',
            'min': '0',
            'max': ''
        })
        # Configurações específicas para tipos numéricos
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
        config.update({
            'field_type': 'yesno',
            'text_validation': '',
            'min': '',
            'max': ''
        })
    elif field_type == 'zipcode':
        config.update({
            'field_type': 'text',
            'text_validation': 'zipcode',
            'min': '',
            'max': ''
        })
    elif field_type == 'cpf':
        config.update({
            'field_type': 'text',
            'text_validation': 'cpf',
            'min': '',
            'max': ''
        })
    elif field_type == 'notes':
        config.update({
            'field_type': 'notes',
            'text_validation': '',
            'min': '',
            'max': ''
        })
    elif field_type in ['radio', 'dropdown']:
        config.update({
            'field_type': field_type,
            'text_validation': '',
            'min': '',
            'max': ''
        })
    
    return config

def parse_document(doc_path):
    doc = Document(doc_path)
    fields = []
    used_names = set()
    
    i = 0
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    
    while i < len(paragraphs):
        current_line = paragraphs[i]
        
        # Pula cabeçalhos muito longos
        if len(current_line) > 150:
            i += 1
            continue
            
        # Detecta perguntas (começam com número ou têm :)
        if re.match(r'^\d+\.', current_line) or ':' in current_line:
            
            # Extrai pergunta principal
            question_text = re.sub(r'^\d+\.\s*', '', current_line)
            question_text = question_text.split(':')[0] if ':' in question_text else question_text
            
            # Coleta opções das linhas seguintes
            options = []
            j = i + 1
            while j < len(paragraphs) and re.match(r'^\(\d+\)', paragraphs[j]):
                option_match = re.match(r'\((\d+)\)\s*(.+)', paragraphs[j])
                if option_match:
                    options.append((option_match.group(1), option_match.group(2).strip()))
                j += 1
            
            # Cria nome do campo
            field_name = clean_field_name(question_text)
            
            # Garante nome único
            original_name = field_name
            counter = 1
            while field_name in used_names:
                field_name = f"{original_name}_{counter}"[:25].rstrip('_')
                counter += 1
            used_names.add(field_name)
            
            # Detecta tipo e configuração
            detected_type = detect_field_type(current_line, options)
            field_config = get_redcap_field_config(detected_type, current_line, options)
            
            # Formata opções para RedCap
            choices = ""
            if options and field_config['field_type'] in ['radio', 'dropdown']:
                choices = " | ".join([f"{num}, {desc}" for num, desc in options])
            
            fields.append({
                'variable_name': field_name,
                'form_name': 'lipodistrofia',
                'field_type': field_config['field_type'],
                'field_label': current_line[:80],  # Limita label
                'choices': choices,
                'text_validation': field_config['text_validation'],
                'validation_min': field_config['min'],
                'validation_max': field_config['max'],
                'detected_type': detected_type  # Para debug
            })
            
            i = j  # Pula as linhas processadas
        else:
            i += 1
    
    return fields

def create_redcap_csv(fields, output_path):
    """Cria CSV no formato exato do RedCap"""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        # Escreve cabeçalho completo do RedCap
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
        
        # Escreve cada campo
        for field in fields:
            writer.writerow([
                field['variable_name'],      # A - Variable / Field Name
                field['form_name'],          # B - Form Name  
                "",                         # C - Section Header
                field['field_type'],         # D - Field Type
                field['field_label'],        # E - Field Label
                field['choices'],           # F - Choices
                "",                         # G - Field Note
                field['text_validation'],   # H - Text Validation
                field['validation_min'],    # I - Text Validation Min
                field['validation_max'],    # J - Text Validation Max
                "",                         # K - Identifier?
                "",                         # L - Branching Logic
                "",                         # M - Required Field?
                "",                         # N - Custom Alignment
                "",                         # O - Question Number
                "",                         # P - Matrix Group Name
                "",                         # Q - Matrix Ranking?
                ""                          # R - Field Annotation
            ])

def validate_fields(fields):
    """Valida os campos antes de gerar CSV"""
    problems = []
    used_names = set()
    
    for field in fields:
        name = field['variable_name']
        
        # Verifica duplicatas
        if name in used_names:
            problems.append(f"Duplicado: {name}")
        used_names.add(name)
        
        # Verifica formato do nome
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
        print("❌ Problemas encontrados:")
        for problem in problems:
            print(f"   - {problem}")
        print("🔄 Corrigindo automaticamente...")
        # Re-processa para corrigir
        fields = parse_document(input_file)
    
    print("💾 Gerando CSV RedCap...")
    create_redcap_csv(fields, output_file)
    
    print(f"🎉 CONCLUÍDO! Arquivo: {output_file}")
    print(f"📊 Total de campos: {len(fields)}")
    
    # Mostra preview com tipos detectados
    print("\n🔍 Primeiros 15 campos (com tipos detectados):")
    for i, field in enumerate(fields[:15]):
        validation_info = f" | {field['text_validation']}" if field['text_validation'] else ""
        print(f"   {i+1:2d}. {field['variable_name']:20} ({field['field_type']:8}) → {field['detected_type']:10}{validation_info}")
    
    # Estatísticas dos tipos detectados
    type_counts = {}
    for field in fields:
        detected = field['detected_type']
        type_counts[detected] = type_counts.get(detected, 0) + 1
    
    print(f"\n📈 Estatísticas dos tipos detectados:")
    for tipo, count in sorted(type_counts.items()):
        print(f"   - {tipo:12}: {count:3} campos")