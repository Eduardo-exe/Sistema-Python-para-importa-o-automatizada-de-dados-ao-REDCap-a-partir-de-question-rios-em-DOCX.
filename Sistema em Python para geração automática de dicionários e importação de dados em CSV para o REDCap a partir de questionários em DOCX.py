# -*- coding: utf-8 -*-
"""
Parser DOCX -> REDCap CSV
Versão adaptável: nome do formulário e do arquivo DOCX são definidos em tempo de execução.
"""

from docx import Document
import csv
import re
import unidecode


def clean_field_name(name):
    """Limpa nomes para padrão REDCap."""
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
        'sistolica': 'sist',
    }
    for long, short in abbrevs.items():
        name = name.replace(long, short)

    if re.match(r'^\d', name):
        name = 'q_' + name

    return name[:25].rstrip('_')


def extract_multiple_questions_from_option(option_text):
    """Extrai múltiplas perguntas de uma opção como '(1) Sim → Quanto tempo? Medicação? Dose?'."""
    match = re.match(r'^\((\d+)\)\s*(.+?)\s*→\s*(.+)', option_text)
    if match:
        option_num = match.group(1)
        option_label = match.group(2)
        questions_text = match.group(3)

        print(f"    DEBUG: Extraindo de: '{questions_text}'")

        # Transforma "(anos)" em pergunta completa
        questions_text = re.sub(
            r'(\?)\s*\((anos|meses|dias|horas)\)',
            r'\1 Em quantos \2?',
            questions_text,
        )

        questions = []
        current = ""
        inside_parens = 0

        for i, char in enumerate(questions_text):
            current += char

            if char == '(':
                inside_parens += 1
            elif char == ')':
                inside_parens -= 1

            if (
                char == '?'
                and inside_parens == 0
                and (i == len(questions_text) - 1 or questions_text[i + 1] != '(')
            ):
                questions.append(current.strip())
                current = ""

        if current.strip():
            questions.append(current.strip())

        print(f"    DEBUG: Separou em: {questions}")
        return option_num, option_label, questions

    return None, None, []


def detect_field_type(question_text, options_count=0):
    """Detecta automaticamente o tipo de campo."""
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

    # Campos de texto longo
    long_text_keywords = [
        'descreva',
        'observação',
        'observacao',
        'comentário',
        'comentario',
        'justifique',
        'explique',
        'locais',
    ]
    if any(keyword in question_lower for keyword in long_text_keywords):
        return 'notes'

    # Default
    return 'text'


def get_field_validation(field_type, question_text):
    """Retorna validação apropriada para o tipo de campo (apenas para 'text')."""
    question_lower = question_text.lower()

    if field_type != 'text':
        return {'text_validation': '', 'min': '', 'max': ''}

    # Datas
    if any(word in question_lower for word in ['data', 'nascimento', 'entrevista']):
        return {'text_validation': 'date_dmy', 'min': '', 'max': ''}

    # Telefone
    if any(word in question_lower for word in ['telefone', 'celular', 'fone']):
        return {'text_validation': 'phone', 'min': '', 'max': ''}

    # Numéricos
    num_keywords = [
        'idade',
        'peso',
        'altura',
        'anos',
        'tempo',
        'pressão',
        'pressao',
        'circunferência',
        'circunferencia',
        'imc',
        'frequência',
        'frequencia',
        'kg',
        'cm',
        'mmhg',
        'bpm',
        'em quantos anos',
        'em quantos meses',
    ]
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
        elif (
            'tempo' in question_lower
            or 'anos' in question_lower
            or 'em quantos anos' in question_lower
        ):
            validation['max'] = '100'

        return validation

    # Email
    if 'email' in question_lower or 'e-mail' in question_lower:
        return {'text_validation': 'email', 'min': '', 'max': ''}

    # CPF
    if 'cpf' in question_lower:
        return {'text_validation': 'cpf', 'min': '', 'max': ''}

    # CEP
    if 'cep' in question_lower:
        return {'text_validation': 'zipcode', 'min': '', 'max': ''}

    # Percentual
    if (
        '%' in question_text
        or 'percentual' in question_lower
        or 'porcentagem' in question_lower
    ):
        return {'text_validation': 'number', 'min': '0', 'max': '100'}

    return {'text_validation': '', 'min': '', 'max': ''}


def create_subquestion_field(parent_field_name, option_num, question, used_names, form_name):
    """Cria um campo de subpergunta com branching logic."""
    print(f"    DEBUG: Criando subpergunta: '{question}'")

    field_name = clean_field_name(question)

    if field_name.endswith('_'):
        field_name = field_name[:-1]

    if len(field_name) < 3 or field_name in ['em', 'quantos', 'anos', 'meses', 'dias']:
        words = re.findall(r'\b\w+\b', question.lower())
        main_word = next((w for w in words if w not in ['em', 'quantos', 'qual', 'que']), 'tempo')
        field_name = f"{parent_field_name}_{main_word}"

    original_name = field_name
    counter = 1
    while field_name in used_names:
        field_name = f"{original_name}_{counter}"[:25].rstrip('_')
        counter += 1
    used_names.add(field_name)

    branching = f"[{parent_field_name}] = '{option_num}'"

    field_type = 'text'
    validation = get_field_validation(field_type, question)

    field_label = question
    if not field_label.endswith('?') and not field_label.endswith(':'):
        field_label = field_label + '?'

    field_data = {
        'variable_name': field_name,
        'form_name': form_name,
        'field_type': field_type,
        'field_label': field_label[:250],
        'choices': '',
        'text_validation': validation['text_validation'],
        'validation_min': validation['min'],
        'validation_max': validation['max'],
        'detected_type': field_type,
        'branching_logic': branching,
        'section_header': '',
    }

    print(f"    ✅ Subpergunta criada: {field_name}")
    print(f"       ↳ Label: '{field_label[:40]}...'")
    if validation['text_validation']:
        print(
            f"       ↳ Validação: {validation['text_validation']} "
            f"(min: {validation['min']}, max: {validation['max']})"
        )
    print(f"       ↳ Branching: {branching}")

    return field_data, field_name


def parse_document(doc_path, form_name):
    """Lê o DOCX e gera a lista de campos estruturados."""
    doc = Document(doc_path)
    fields = []
    used_names = set()

    print("📖 Lendo documento Word...")
    print("🔍 ATENÇÃO: Branching logic será colocada DEPOIS do campo principal")

    paragraphs = []
    for p in doc.paragraphs:
        for line in p.text.splitlines():
            if line.strip():
                paragraphs.append(line.strip())

    # record_id
    fields.append({
        'variable_name': 'record_id',
        'form_name': form_name,
        'field_type': 'text',
        'field_label': 'Record ID',
        'choices': '',
        'text_validation': '',
        'validation_min': '',
        'validation_max': '',
        'detected_type': 'text',
        'branching_logic': '',
        'section_header': '',
    })
    used_names.add('record_id')

    i = 0
    while i < len(paragraphs):
        current_line = paragraphs[i]

        # Seção (termina com ..)
        if current_line.endswith(".."):
            section_text = current_line.rstrip(".")
            field_name = clean_field_name(section_text)

            original_name = field_name
            counter = 1
            while field_name in used_names:
                field_name = f"{original_name}_{counter}"[:25].rstrip('_')
                counter += 1
            used_names.add(field_name)

            fields.append({
                'variable_name': field_name,
                'form_name': form_name,
                'field_type': 'descriptive',
                'field_label': section_text[:250],
                'choices': '',
                'text_validation': '',
                'validation_min': '',
                'validation_max': '',
                'detected_type': 'descriptive',
                'branching_logic': '',
                'section_header': '',
            })

            print(f"📌 Seção: {section_text[:40]}...")
            i += 1
            continue

        # Pergunta principal
        is_question = (
            current_line.endswith(':')
            or re.match(r'^\d+\.', current_line)
            or (current_line.endswith('?') and len(current_line) < 100)
        )

        if is_question:
            question_text = re.sub(r'^\d+\.\s*', '', current_line)
            question_text = question_text.rstrip(':').strip()

            field_name = clean_field_name(question_text)

            original_name = field_name
            counter = 1
            while field_name in used_names:
                field_name = f"{original_name}_{counter}"[:25].rstrip('_')
                counter += 1
            used_names.add(field_name)

            options = []
            subquestions_to_add = []
            j = i + 1

            while j < len(paragraphs) and re.match(r'^\((\d+)\)', paragraphs[j]):
                option_line = paragraphs[j]

                if '→' in option_line and '?' in option_line:
                    option_num, option_label, questions = extract_multiple_questions_from_option(option_line)

                    if questions:
                        print(f"\n🔍 PERGUNTAS ENCONTRADAS NA OPÇÃO:")
                        print(f"   Pergunta principal: {question_text}")
                        print(f"   Na opção: {option_line}")
                        print(f"   Extraiu {len(questions)} pergunta(s):")
                        for q_idx, q in enumerate(questions):
                            print(f"     {q_idx + 1}. '{q}'")

                        clean_option_label = option_label
                        if '→' in option_line:
                            clean_option_label = option_line.split('→')[0].strip()
                            clean_option_label = re.sub(r'^\(\d+\)\s*', '', clean_option_label)

                        options.append((option_num, clean_option_label))

                        for q_idx, question in enumerate(questions):
                            field_data, sub_name = create_subquestion_field(
                                field_name, option_num, question, used_names, form_name
                            )
                            subquestions_to_add.append(field_data)
                    else:
                        match = re.match(r'^\((\d+)\)\s*(.+)', option_line)
                        if match:
                            option_text = match.group(2).strip()
                            if '→' in option_text:
                                option_text = option_text.split('→')[0].strip()
                            options.append((match.group(1), option_text))
                else:
                    match = re.match(r'^\((\d+)\)\s*(.+)', option_line)
                    if match:
                        options.append((match.group(1), match.group(2).strip()))

                j += 1

            field_type = detect_field_type(question_text, len(options))

            if field_type in ['radio', 'dropdown']:
                validation = {'text_validation': '', 'min': '', 'max': ''}
            else:
                validation = get_field_validation(field_type, question_text)

            choices = ""
            if field_type in ['radio', 'dropdown'] and options:
                choices = " | ".join([f"{num}, {desc}" for num, desc in options])

            main_field_data = {
                'variable_name': field_name,
                'form_name': form_name,
                'field_type': field_type,
                'field_label': question_text[:250],
                'choices': choices,
                'text_validation': validation['text_validation'],
                'validation_min': validation['min'],
                'validation_max': validation['max'],
                'detected_type': field_type,
                'branching_logic': '',
                'section_header': '',
            }

            fields.append(main_field_data)

            if subquestions_to_add:
                print(
                    f"   🔄 Adicionando {len(subquestions_to_add)} subpergunta(s) "
                    f"DEPOIS do campo principal '{field_name}'"
                )
                for sub_field in subquestions_to_add:
                    fields.append(sub_field)

            field_type_icon = "📻" if field_type == 'radio' else "📋" if field_type == 'dropdown' else "📝"
            print(f"\n{field_type_icon} Campo PRINCIPAL: {field_name} ('{question_text[:40]}...')")
            if options:
                print(f"   ↳ {len(options)} opções, Tipo: {field_type}")
            if validation['text_validation']:
                print(
                    f"   ↳ Validação: {validation['text_validation']} "
                    f"(min: {validation['min']}, max: {validation['max']})"
                )
            if subquestions_to_add:
                print(f"   ↳ {len(subquestions_to_add)} subpergunta(s) com branching logic")

            i = j
        else:
            i += 1

    return fields


def create_redcap_csv(fields, output_path):
    """Cria CSV no formato do REDCap."""
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
            "Matrix Group Name", "Matrix Ranking?", "Field Annotation",
        ])
        for field in fields:
            writer.writerow([
                field.get('variable_name', ''),
                field.get('form_name', ''),
                "",
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
                "",
            ])


if __name__ == "__main__":
    docx_name = input("Informe o nome do arquivo DOCX (com extensão): ").strip()
    form_name = input("Informe o nome do formulário no REDCap: ").strip()

    if not form_name:
        form_name = "form1"

    output_file = f"{form_name}_redcap.csv"

    print("=" * 70)
    print("PARSER DOCX -> REDCAP CSV - VERSÃO ADAPTÁVEL")
    print("=" * 70)

    try:
        fields = parse_document(docx_name, form_name=form_name)

        print(f"\n{'=' * 70}")
        print("💾 Gerando CSV:", output_file)
        create_redcap_csv(fields, output_file)

        print(f"\n{'=' * 70}")
        print("🎉 CONCLUÍDO!")
        print(f"📊 Total de campos gerados: {len(fields)}")
        print(f"📁 Arquivo criado: {output_file}")
        print("=" * 70)

    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo '{docx_name}' não encontrado!")
        print("    Verifique o nome e se o .docx está na mesma pasta.")
    except Exception as e:
        print(f"❌ ERRO: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
