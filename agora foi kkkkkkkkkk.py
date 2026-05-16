# -*- coding: utf-8 -*-
"""
Parser DOCX -> RedCap CSV - VERSÃO CORRIGIDA
Correção: Branching logic deve vir DEPOIS do campo principal relacionado
"""
from docx import Document
import csv
import re
import unidecode

def clean_field_name(name):
    """Limpa nomes para padrão RedCap"""
    name = unidecode.unidecode(name)
    name = re.sub(r'^\d+\.?\s*', '', name)  
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)  
    name = re.sub(r'\s+', '_', name)  
    name = name.rstrip('_')
    
    # Abreviações específicas
    if name.startswith('quanto_tempo'):
        name = 'tempo_' + name[13:] if len(name) > 13 else 'tempo'
    if name.startswith('medicacao'):
        name = 'med_' + name[10:] if len(name) > 10 else 'med'
    
    abbrevs = {
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
    
    return name[:25].rstrip('_')

def extract_multiple_questions_from_option(option_text):
    """Extrai múltiplas perguntas de uma opção como '(1) Sim → Quanto tempo? Medicação? Dose?'"""
    # Padrões: "(1) Sim → Quanto tempo? Medicação? Dose?" ou "(1) Sim → Qual? Quanto tempo? (anos)"
    match = re.match(r'^\((\d+)\)\s*(.+?)\s*→\s*(.+)', option_text)
    if match:
        option_num = match.group(1)
        option_label = match.group(2)
        questions_text = match.group(3)
        
        print(f"    DEBUG: Extraindo de: '{questions_text}'")
        
        # Transforma "(anos)" em uma pergunta completa
        questions_text = re.sub(r'(\?)\s*\((anos|meses|dias|horas)\)', r'\1 Em quantos \2?', questions_text)
        
        # Agora separa as perguntas
        questions = []
        current = ""
        inside_parens = 0
        
        for i, char in enumerate(questions_text):
            current += char
            
            # Conta parênteses
            if char == '(':
                inside_parens += 1
            elif char == ')':
                inside_parens -= 1
            
            # Só separa por ? se não estiver dentro de parênteses
            if (char == '?' and inside_parens == 0 and 
                (i == len(questions_text) - 1 or questions_text[i+1] != '(')):
                questions.append(current.strip())
                current = ""
        
        if current.strip():
            questions.append(current.strip())
        
        print(f"    DEBUG: Separou em: {questions}")
        return option_num, option_label, questions
    
    return None, None, []

def detect_field_type(question_text, options_count=0):
    """Detecta automaticamente o tipo de campo"""
    question_lower = question_text.lower()
    
    # Campos descritivos (títulos)
    if '..' in question_text:
        return 'descriptive'
    
    # Campos com opções
    if options_count > 0:
        if options_count <= 5:
            return 'radio'
        else:
            return 'dropdown'
    
    # Campos de texto longo (notes)
    long_text_keywords = ['descreva', 'observação', 'observacao', 'comentário', 
                         'comentario', 'justifique', 'explique', 'locais']
    if any(keyword in question_lower for keyword in long_text_keywords):
        return 'notes'
    
    # Default é sempre 'text' para poder ter validação
    return 'text'

def get_field_validation(field_type, question_text):
    """Retorna validação apropriada para o tipo de campo - APENAS PARA 'text'"""
    question_lower = question_text.lower()
    
    if field_type != 'text':
        return {'text_validation': '', 'min': '', 'max': ''}
    
    # Campos de data
    if any(word in question_lower for word in ['data', 'nascimento', 'entrevista']):
        return {'text_validation': 'date_dmy', 'min': '', 'max': ''}
    
    # Campos de telefone
    if any(word in question_lower for word in ['telefone', 'celular', 'fone']):
        return {'text_validation': 'phone', 'min': '', 'max': ''}
    
    # Campos numéricos
    num_keywords = ['idade', 'peso', 'altura', 'anos', 'tempo', 'pressão', 'pressao', 
                   'circunferência', 'circunferencia', 'imc', 'frequência', 'frequencia',
                   'kg', 'cm', 'mmhg', 'bpm', 'em quantos anos', 'em quantos meses']
    if any(keyword in question_lower for keyword in num_keywords):
        validation = {'text_validation': 'number', 'min': '0', 'max': '999'}
        
        if 'idade' in question_lower:
            validation['max'] = '120'
        elif 'peso' in question_lower or 'peso' in question_text:
            validation['max'] = '300'
        elif 'altura' in question_lower:
            validation['max'] = '250'
        elif 'pressão' in question_lower or 'pressao' in question_lower:
            if 'sistólica' in question_lower or 'sistolica' in question_lower:
                validation['max'] = '300'
            elif 'diastólica' in question_lower or 'diastolica' in question_lower:
                validation['max'] = '200'
        elif 'circunferência' in question_lower or 'circunferencia' in question_lower:
            validation['max'] = '200'
        elif 'imc' in question_lower:
            validation['max'] = '100'
        elif 'frequência' in question_lower or 'frequencia' in question_lower:
            validation['max'] = '250'
        elif 'tempo' in question_lower or 'anos' in question_lower or 'em quantos anos' in question_lower:
            validation['max'] = '100'
        
        return validation
    
    # Campos de email
    if 'email' in question_lower or 'e-mail' in question_lower:
        return {'text_validation': 'email', 'min': '', 'max': ''}
    
    # Campos de CPF
    if 'cpf' in question_lower:
        return {'text_validation': 'cpf', 'min': '', 'max': ''}
    
    # Campos de CEP
    if 'cep' in question_lower:
        return {'text_validation': 'zipcode', 'min': '', 'max': ''}
    
    # Campos percentuais
    if '%' in question_text or 'percentual' in question_lower or 'porcentagem' in question_lower:
        return {'text_validation': 'number', 'min': '0', 'max': '100'}
    
    return {'text_validation': '', 'min': '', 'max': ''}

def create_subquestion_field(parent_field_name, option_num, question, used_names):
    """Cria um campo de subpergunta com branching logic"""
    
    print(f"    DEBUG: Criando subpergunta: '{question}'")
    
    # Cria nome do campo
    field_name = clean_field_name(question)
    
    # Remove ? do final para o nome
    if field_name.endswith('_'):
        field_name = field_name[:-1]
    
    # Se o nome ficou muito curto ou vazio, usa um nome baseado no parent
    if len(field_name) < 3 or field_name in ['em', 'quantos', 'anos', 'meses', 'dias']:
        words = re.findall(r'\b\w+\b', question.lower())
        main_word = next((w for w in words if w not in ['em', 'quantos', 'qual', 'que']), 'tempo')
        field_name = f"{parent_field_name}_{main_word}"
    
    # Garante nome único
    original_name = field_name
    counter = 1
    while field_name in used_names:
        field_name = f"{original_name}_{counter}"[:25].rstrip('_')
        counter += 1
    used_names.add(field_name)
    
    # Branching logic
    branching = f"[{parent_field_name}] = '{option_num}'"
    
    # Determina tipo de campo
    field_type = 'text'  # Subperguntas sempre serão 'text'
    validation = get_field_validation(field_type, question)
    
    # Ajusta a label se necessário
    field_label = question
    
    # Se a label não termina com ?, adiciona
    if not field_label.endswith('?') and not field_label.endswith(':'):
        field_label = field_label + '?'
    
    # Cria o dicionário do campo
    field_data = {
        'variable_name': field_name,
        'form_name': 'lipodistrofia',
        'field_type': field_type,
        'field_label': field_label[:250],
        'choices': '',
        'text_validation': validation['text_validation'],
        'validation_min': validation['min'],
        'validation_max': validation['max'],
        'detected_type': field_type,
        'branching_logic': branching,
        'section_header': ''
    }
    
    print(f"   ✅ Subpergunta criada: {field_name}")
    print(f"      ↳ Label: '{field_label[:40]}...'")
    if validation['text_validation']:
        print(f"      ↳ Validação: {validation['text_validation']} (min: {validation['min']}, max: {validation['max']})")
    print(f"      ↳ Branching: {branching}")
    
    return field_data, field_name

def parse_document(doc_path):
    doc = Document(doc_path)
    fields = []
    used_names = set()
    
    print("📖 Lendo documento Word...")
    print("🔍 ATENÇÃO: Branching logic será colocada DEPOIS do campo principal")
    
    # Lê todas as linhas
    paragraphs = []
    for p in doc.paragraphs:
        for line in p.text.splitlines():
            if line.strip():
                paragraphs.append(line.strip())
    
    # Adiciona record_id (sempre o primeiro campo)
    fields.append({
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
    })
    used_names.add('record_id')
    
    i = 0
    
    while i < len(paragraphs):
        current_line = paragraphs[i]
        
        # Seção/Título (termina com ..)
        if current_line.endswith(".."):
            section_text = current_line.rstrip(".")
            field_name = clean_field_name(section_text)
            
            # Garante nome único
            original_name = field_name
            counter = 1
            while field_name in used_names:
                field_name = f"{original_name}_{counter}"[:25].rstrip('_')
                counter += 1
            used_names.add(field_name)
            
            fields.append({
                'variable_name': field_name,
                'form_name': 'lipodistrofia',
                'field_type': 'descriptive',
                'field_label': section_text[:250],
                'choices': '',
                'text_validation': '',
                'validation_min': '',
                'validation_max': '',
                'detected_type': 'descriptive',
                'branching_logic': '',
                'section_header': ''
            })
            
            print(f"📌 Seção: {section_text[:40]}...")
            i += 1
            continue
        
        # Pergunta principal (termina com : ou começa com número)
        is_question = (current_line.endswith(':') or 
                      re.match(r'^\d+\.', current_line) or
                      (current_line.endswith('?') and len(current_line) < 100))
        
        if is_question:
            # Remove número no início se houver
            question_text = re.sub(r'^\d+\.\s*', '', current_line)
            # Remove : no final se houver
            question_text = question_text.rstrip(':').strip()
            
            field_name = clean_field_name(question_text)
            
            # Garante nome único
            original_name = field_name
            counter = 1
            while field_name in used_names:
                field_name = f"{original_name}_{counter}"[:25].rstrip('_')
                counter += 1
            used_names.add(field_name)
            
            # Coleta opções
            options = []
            subquestions_to_add = []  # LISTA PARA ARMAZENAR SUBPERGUNTAS TEMPORARIAMENTE
            has_multiple_questions = False
            j = i + 1
            
            while j < len(paragraphs) and re.match(r'^\((\d+)\)', paragraphs[j]):
                option_line = paragraphs[j]
                
                # Verifica se tem múltiplas perguntas inline
                if '→' in option_line and '?' in option_line:
                    option_num, option_label, questions = extract_multiple_questions_from_option(option_line)
                    
                    if questions:
                        has_multiple_questions = True
                        print(f"\n🔍 PERGUNTAS ENCONTRADAS NA OPÇÃO:")
                        print(f"   Pergunta principal: {question_text}")
                        print(f"   Na opção: {option_line}")
                        print(f"   Extraiu {len(questions)} pergunta(s):")
                        for q_idx, q in enumerate(questions):
                            print(f"     {q_idx+1}. '{q}'")
                        
                        # Adiciona a opção principal (sem as subperguntas)
                        clean_option_label = option_label
                        if '→' in option_line:
                            clean_option_label = option_line.split('→')[0].strip()
                            clean_option_label = re.sub(r'^\(\d+\)\s*', '', clean_option_label)
                        
                        options.append((option_num, clean_option_label))
                        
                        # CORREÇÃO: Cria as subperguntas mas NÃO as adiciona ainda
                        for q_idx, question in enumerate(questions):
                            field_data, sub_name = create_subquestion_field(
                                field_name, option_num, question, used_names
                            )
                            # Armazena temporariamente para adicionar DEPOIS do campo principal
                            subquestions_to_add.append(field_data)
                        
                    else:
                        # Opção normal ou com subpergunta única
                        match = re.match(r'^\((\d+)\)\s*(.+)', option_line)
                        if match:
                            option_text = match.group(2).strip()
                            if '→' in option_text:
                                option_text = option_text.split('→')[0].strip()
                            options.append((match.group(1), option_text))
                else:
                    # Opção normal
                    match = re.match(r'^\((\d+)\)\s*(.+)', option_line)
                    if match:
                        options.append((match.group(1), match.group(2).strip()))
                
                j += 1
            
            # Determina tipo de campo principal
            field_type = detect_field_type(question_text, len(options))
            
            # IMPORTANTE: Se for radio/dropdown, NÃO pode ter validação
            if field_type in ['radio', 'dropdown']:
                validation = {'text_validation': '', 'min': '', 'max': ''}
            else:
                validation = get_field_validation(field_type, question_text)
            
            # Formata choices se for radio/dropdown
            choices = ""
            if field_type in ['radio', 'dropdown'] and options:
                choices = " | ".join([f"{num}, {desc}" for num, desc in options])
            
            # CORREÇÃO: Cria o campo PRINCIPAL PRIMEIRO
            main_field_data = {
                'variable_name': field_name,
                'form_name': 'lipodistrofia',
                'field_type': field_type,
                'field_label': question_text[:250],
                'choices': choices,
                'text_validation': validation['text_validation'],
                'validation_min': validation['min'],
                'validation_max': validation['max'],
                'detected_type': field_type,
                'branching_logic': '',
                'section_header': ''
            }
            
            # Adiciona o campo PRINCIPAL primeiro
            fields.append(main_field_data)
            
            # CORREÇÃO: Agora adiciona as subperguntas DEPOIS do campo principal
            if subquestions_to_add:
                print(f"   🔄 Adicionando {len(subquestions_to_add)} subpergunta(s) DEPOIS do campo principal '{field_name}'")
                for sub_field in subquestions_to_add:
                    fields.append(sub_field)
            
            # Log
            field_type_icon = "📻" if field_type == 'radio' else "📋" if field_type == 'dropdown' else "📝"
            print(f"\n{field_type_icon} Campo PRINCIPAL: {field_name} ('{question_text[:40]}...')")
            if options:
                print(f"   ↳ {len(options)} opções, Tipo: {field_type}")
            if validation['text_validation']:
                print(f"   ↳ Validação: {validation['text_validation']} (min: {validation['min']}, max: {validation['max']})")
            if subquestions_to_add:
                print(f"   ↳ {len(subquestions_to_add)} subpergunta(s) com branching logic")
            
            i = j  # Pula as linhas das opções
        else:
            i += 1
    
    return fields

def validate_fields(fields):
    """Valida os campos antes de gerar CSV"""
    problems = []
    used_names = set()
    
    if not fields:
        problems.append("Nenhum campo encontrado")
        return problems
    
    # Verifica record_id
    if fields[0].get('variable_name') != 'record_id':
        problems.append("Primeiro campo deve ser 'record_id'")
    
    for idx, field in enumerate(fields):
        name = field.get('variable_name', '')
        field_type = field.get('field_type', '')
        text_validation = field.get('text_validation', '')
        
        if not name:
            problems.append(f"Linha {idx+1}: Sem nome")
            continue
            
        if name in used_names and idx > 0:
            problems.append(f"Linha {idx+1}: Nome duplicado '{name}'")
        used_names.add(name)
        
        if not field_type:
            problems.append(f"Linha {idx+1} ({name}): Sem tipo")
            continue
        
        # Apenas campos 'text' podem ter validação
        if field_type != 'text' and text_validation:
            problems.append(f"Linha {idx+1} ({name}): Campo '{field_type}' não pode ter validação '{text_validation}'")
        
        # Verifica se campo 'text' com validação numérica tem max
        if field_type == 'text' and text_validation == 'number':
            max_val = field.get('validation_max', '')
            if not max_val:
                problems.append(f"Linha {idx+1} ({name}): Validação numérica precisa de 'max'")
    
    return problems

def create_redcap_csv(fields, output_path):
    """Cria CSV no formato do RedCap"""
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
                '',  # Section Header
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

# EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    input_file = "Dados de Identificação e Sociodemográficos.docx"
    output_file = "redcap_ordem_correta.csv"
    
    print("=" * 70)
    print("PARSER DOCX -> REDCAP CSV - VERSÃO FINAL CORRIGIDA")
    print("CORREÇÃO: Campo principal vem ANTES da branching logic")
    print("=" * 70)
    
    try:
        fields = parse_document(input_file)
        
        print(f"\n{'='*70}")
        print("🔍 VALIDAÇÃO DA ORDEM DOS CAMPOS")
        print("Verificando ordem correta: campo principal → branching logic...")
        
        # Verifica a ordem específica
        order_problems = []
        last_main_field = None
        
        for idx, field in enumerate(fields):
            var_name = field.get('variable_name', '')
            branching = field.get('branching_logic', '')
            
            if branching:
                # Extrai o nome do campo principal da branching logic
                match = re.search(r'\[(\w+)\]', branching)
                if match:
                    main_field = match.group(1)
                    # Procura se o campo principal existe antes deste campo
                    found_before = False
                    for prev_idx in range(idx):
                        prev_field = fields[prev_idx]
                        if prev_field.get('variable_name') == main_field:
                            found_before = True
                            break
                    
                    if not found_before:
                        order_problems.append(f"Linha {idx+1}: Branching logic de '{var_name}' refere-se a '{main_field}' que não foi definido antes")
        
        if order_problems:
            print(f"\n❌ PROBLEMAS DE ORDEM ({len(order_problems)}):")
            for problem in order_problems[:10]:
                print(f"   ⚠️  {problem}")
        else:
            print("✅ Ordem correta: Todos os campos com branching logic têm seu campo principal definido ANTES")
        
        print(f"\n💾 Gerando CSV: {output_file}")
        create_redcap_csv(fields, output_file)
        
        print(f"\n{'='*70}")
        print("🎉 CONCLUÍDO!")
        print(f"📊 Total de campos gerados: {len(fields)}")
        
        # Mostra exemplo da ordem corrigida
        print(f"\n🔍 EXEMPLO DE ORDEM CORRIGIDA:")
        print("   (Campo principal vem ANTES dos campos com branching logic)")
        
        # Encontra um exemplo com branching logic
        example_found = False
        for idx, field in enumerate(fields):
            if field.get('branching_logic'):
                main_field_name = re.search(r'\[(\w+)\]', field.get('branching_logic', '')).group(1)
                
                # Procura o campo principal
                for main_idx in range(idx):
                    main_field = fields[main_idx]
                    if main_field.get('variable_name') == main_field_name:
                        print(f"\n   📋 EXEMPLO {idx+1}:")
                        print(f"   1. {main_field_name:25} ('{main_field.get('field_label', '')[:30]}...')")
                        print(f"   2. {field.get('variable_name'):25} ('{field.get('field_label', '')[:30]}...')")
                        print(f"      ↳ Branching logic: {field.get('branching_logic')}")
                        example_found = True
                        break
                
                if example_found:
                    break
        
        print(f"\n💡 PRÓXIMOS PASSOS:")
        print(f"   1. Importe '{output_file}' no RedCap")
        print(f"   2. Agora a ordem será: Campo principal → Branching logic")
        print("=" * 70)
        
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo '{input_file}' não encontrado!")
        print("   Certifique-se que o arquivo .docx está na mesma pasta.")
    except Exception as e:
        print(f"❌ ERRO: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()