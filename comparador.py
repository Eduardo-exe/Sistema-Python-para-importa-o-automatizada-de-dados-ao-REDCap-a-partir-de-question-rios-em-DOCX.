import pandas as pd
import numpy as np
import re
from datetime import datetime
import unidecode
import os

def load_data_dictionary(dict_csv_path):
    """Carrega o dicionário de dados gerado pelo parser"""
    print(f"📚 Carregando dicionário de dados: {dict_csv_path}")
    
    try:
        df_dict = pd.read_csv(dict_csv_path, encoding='utf-8')
        
        # Verifica se tem o formato do RedCap
        if 'Variable / Field Name' in df_dict.columns:
            variables = df_dict['Variable / Field Name'].tolist()
            print(f"✅ Dicionário carregado: {len(variables)} variáveis")
            
            # Cria um dicionário com mais informações
            field_info = {}
            for _, row in df_dict.iterrows():
                var_name = row['Variable / Field Name']
                field_info[var_name] = {
                    'field_label': row.get('Field Label', ''),
                    'field_type': row.get('Field Type', ''),
                    'choices': row.get('Choices, Calculations, OR Slider Labels', ''),
                    'text_validation': row.get('Text Validation Type OR Show Slider Number', ''),
                    'validation_min': row.get('Text Validation Min', ''),
                    'validation_max': row.get('Text Validation Max', ''),
                    'branching_logic': row.get('Branching Logic (Show field only if...)', '')
                }
            
            return variables, field_info
        else:
            print("❌ Formato do dicionário não reconhecido")
            return [], {}
            
    except Exception as e:
        print(f"❌ Erro ao carregar dicionário: {e}")
        return [], {}

def clean_column_name_exact_match(col_name, dict_variables):
    """Limpa nome de coluna tentando encontrar correspondência exata no dicionário"""
    
    # Se já está no dicionário, retorna como está
    if col_name in dict_variables:
        return col_name
    
    # Tenta limpar como o parser faz
    name = unidecode.unidecode(str(col_name))
    name = re.sub(r'^\d+\.?\s*', '', name)
    name = name.lower().strip()
    name = re.sub(r'[^\w\s]', '', name)
    name = re.sub(r'\s+', '_', name)
    name = name.rstrip('_')
    
    # Abreviações específicas do parser
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
    
    name = name[:25].rstrip('_')
    
    # Verifica se após limpeza está no dicionário
    if name in dict_variables:
        return name
    
    # Se não encontrou, procura por similaridade
    for dict_var in dict_variables:
        # Remove sufixos numéricos para comparação
        base_dict = re.sub(r'_\d+$', '', dict_var)
        base_name = re.sub(r'_\d+$', '', name)
        
        if (base_dict == base_name or 
            dict_var in name or 
            name in dict_var or
            dict_var.startswith(base_name) or 
            base_name.startswith(dict_var)):
            return dict_var  # Retorna o nome exato do dicionário
    
    return name  # Retorna o nome limpo

def find_best_match(data_col, dict_variables):
    """Encontra a melhor correspondência para uma coluna"""
    
    data_col_lower = str(data_col).lower()
    
    # Lista de correspondências comuns
    common_mappings = {
        'prontuário': 'record_id',
        'prontuario': 'record_id',
        'data da entrevista': 'data_entrevista',
        'data de nascimento': 'data_nascimento',
        'idade na entrevista': 'idade_entrevista',
        'idade atual': 'idade_atual',
        'naturalidade': 'naturalidade',
        'profissão': 'profissao',
        'profissao': 'profissao',
        'estado civil': 'estado_civil',
        'escolaridade': 'escolaridade',
        'sinais e sintomas': 'sinais_sintomas',
        'amp - dm': 'amp_dm',
        'amp - has': 'amp_has',
        'amp - dislipidemia': 'amp_dislipidemia',
        'tempo': 'tempo',
        'medicação': 'medicacao',
        'dose': 'dose',
        'dai': 'dai',
        'qual': 'qual',
        'tabagismo': 'tabagismo',
        'etilismo': 'etilismo',
        'menstruação': 'menstruacao',
        'gestação': 'gestacao',
        'g': 'g',
        'p': 'p',
        'a': 'a',
        'menopausa': 'menopausa',
        'exercício': 'exercicio',
        'hf - dm1': 'hf_dm1',
        'hf - dm2': 'hf_dm2',
        'hf - dislipidemia': 'hf_dislipidemia',
        'hf - has': 'hf_has',
        'doenca cardiovascular': 'doenca_cardiovascular',
        'obesidade': 'obesidade',
        'doença autoimune': 'doenca_autoimune',
        'pais consanguineos': 'pais_consanguineos',
        'peso': 'peso',
        'altura': 'altura',
        'imc': 'imc',
        'ca': 'ca',
        'classificação': 'classificacao',
        'cq': 'cq',
        'cp': 'cp',
        'ccd': 'ccd',
        'cce': 'cce',
        'pas': 'pas',
        'pad': 'pad',
        'fc': 'fc',
        'an': 'an',
        'local': 'local',
        'prega de coxa': 'prega_coxa',
        'prega de braço esquerdo': 'prega_braco_esquerdo',
        'prega suescapular': 'prega_suescapular',
        'prega da panturrilha': 'prega_panturrilha',
        'índice de köb': 'indice_kob',
        'mr': 'mr',
        'escore ca': 'escore_ca',
        'igf-1': 'igf1',
        'homa-ir': 'homa_ir',
        'insulina': 'insulina',
        'peptideo c': 'peptideo_c',
        'gj': 'gj',
        'hba1c': 'hba1c',
        'leptina': 'leptina',
        'ur': 'ur',
        'cr': 'cr',
        'função renal': 'funcao_renal',
        'tgo': 'tgo',
        'tgp': 'tgp',
        'ggt': 'ggt',
        'fa': 'fa',
        'tsh': 'tsh',
        't4l': 't4l',
        'cpk': 'cpk',
        'ct': 'ct',
        'ldl': 'ldl',
        'hdl': 'hdl',
        'tg': 'tg',
        'n-hdl': 'n_hdl',
        'vldl': 'vldl',
        'ttgo': 'ttgo',
        'albumimuria': 'albumimuria',
        'microalbumimuria': 'microalbumimuria',
        'ra/cr': 'ra_cr',
        'us de abdome': 'us_abdome',
        'dmo': 'dmo',
        'imma': 'imma',
        'img': 'img',
        'gv': 'gv',
        'androide': 'androide',
        'gt/gp': 'gt_gp',
        'a/g': 'a_g',
        'ginoide': 'ginoide',
        'mma': 'mma',
        'mm - tronco': 'mm_tronco',
        'mgmmii': 'mgmmii',
        'mmmmi': 'mmmmi',
        'mgmmss': 'mgmmss',
        'mmmss': 'mmmss',
        'mmtro': 'mmtro',
        'mgtr': 'mgtr',
        'eco': 'eco',
        'elastografia': 'elastografia',
        'elastografia por ultrassonografia': 'elastografia_us',
        'doppler de carótidas': 'doppler_carotidas',
        'us de tiroide': 'us_tiroide',
        'teste genético': 'teste_genetico'
    }
    
    # Procura na lista de correspondências comuns
    for key, value in common_mappings.items():
        if key in data_col_lower or data_col_lower in key:
            if value in dict_variables:
                return value
    
    # Procura por similaridade textual
    for dict_var in dict_variables:
        dict_var_lower = dict_var.lower()
        
        # Verifica várias formas de similaridade
        if (data_col_lower == dict_var_lower or
            data_col_lower.replace(' ', '_') == dict_var_lower or
            dict_var_lower in data_col_lower or
            data_col_lower in dict_var_lower):
            return dict_var
    
    return None

def create_column_mapping(data_columns, dict_variables):
    """Cria mapeamento de colunas dos dados para variáveis do dicionário"""
    
    mapping = {}
    unmapped_data_cols = []
    
    print(f"\n🔍 Criando mapeamento de colunas...")
    print(f"   Colunas nos dados: {len(data_columns)}")
    print(f"   Variáveis no dicionário: {len(dict_variables)}")
    
    for data_col in data_columns:
        dict_var = clean_column_name_exact_match(data_col, dict_variables)
        
        if dict_var in dict_variables:
            mapping[data_col] = dict_var
            print(f"   ✅ {data_col} → {dict_var}")
        else:
            # Tenta encontrar correspondência manualmente
            dict_var = find_best_match(data_col, dict_variables)
            if dict_var:
                mapping[data_col] = dict_var
                print(f"   🔄 {data_col} → {dict_var} (correspondência)")
            else:
                unmapped_data_cols.append(data_col)
                print(f"   ❌ {data_col} → NÃO MAPEADO")
    
    return mapping, unmapped_data_cols

# FUNÇÕES DE NORMALIZAÇÃO CORRIGIDAS
def normalize_dates(series):
    """Normaliza datas para formato dd/mm/aaaa"""
    def parse_date(date_val):
        if pd.isna(date_val):
            return np.nan
        
        date_str = str(date_val).strip()
        
        if date_str == '' or date_str.lower() == 'nan':
            return np.nan
        
        # Tenta vários formatos
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y', '%d-%m-%y',
            '%d.%m.%Y', '%d.%m.%y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%d/%m/%Y')
            except:
                continue
        
        # Se tem formato 1/1/2024 (sem zeros à esquerda)
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}', date_str):
            try:
                return datetime.strptime(date_str, '%d/%m/%Y').strftime('%d/%m/%Y')
            except:
                pass
        
        return date_str  # Retorna original se não conseguir parse
    
    return series.apply(parse_date)

def normalize_numbers(series):
    """Normaliza números (substitui vírgula por ponto)"""
    def parse_number(num_val):
        if pd.isna(num_val):
            return np.nan
        
        num_str = str(num_val).strip()
        
        if num_str == '' or num_str.lower() in ['nan', 'na', 'n/a']:
            return np.nan
        
        # Remove caracteres não numéricos exceto ponto, vírgula e sinal negativo
        num_str = re.sub(r'[^\d\.,\-]', '', num_str)
        
        if num_str == '':
            return np.nan
        
        # Substitui vírgula por ponto
        num_str = num_str.replace(',', '.')
        
        # Remove múltiplos pontos
        if num_str.count('.') > 1:
            parts = num_str.split('.')
            num_str = parts[0] + '.' + ''.join(parts[1:])
        
        try:
            return float(num_str)
        except:
            try:
                # Tenta como inteiro
                return int(float(num_str))
            except:
                return np.nan
    
    return series.apply(parse_number)

def normalize_phones(series):
    """Normaliza números de telefone"""
    def parse_phone(phone_val):
        if pd.isna(phone_val):
            return np.nan
        
        phone_str = str(phone_val).strip()
        
        if phone_str == '' or phone_str.lower() in ['nan', 'na', 'n/a']:
            return np.nan
        
        # Remove todos os caracteres não numéricos
        phone_str = re.sub(r'[^\d]', '', phone_str)
        
        if phone_str == '':
            return np.nan
        
        # Formata: (XX) XXXXX-XXXX
        if len(phone_str) == 11:
            return f'({phone_str[:2]}) {phone_str[2:7]}-{phone_str[7:]}'
        elif len(phone_str) == 10:
            return f'({phone_str[:2]}) {phone_str[2:6]}-{phone_str[6:]}'
        else:
            return phone_str
    
    return series.apply(parse_phone)

def normalize_text(series):
    """Normaliza texto (remove espaços extras)"""
    def clean_text(text_val):
        if pd.isna(text_val):
            return np.nan
        
        text_str = str(text_val)
        
        if text_str.lower() in ['nan', 'na', 'n/a', '']:
            return np.nan
        
        text_str = text_str.strip()
        text_str = re.sub(r'\s+', ' ', text_str)  # Remove múltiplos espaços
        
        return text_str
    
    return series.apply(clean_text)

def normalize_categorical(series, choices):
    """Normaliza valores categóricos baseado nas choices do dicionário"""
    if pd.isna(choices) or choices == '' or str(choices).strip() == '':
        return series
    
    # Extrai mapeamento de choices (ex: "1, Sim | 2, Não")
    choice_map = {}
    
    for choice in str(choices).split('|'):
        choice = choice.strip()
        if ',' in choice:
            key, value = choice.split(',', 1)
            key = key.strip()
            value = value.strip()
            choice_map[key] = value
    
    def map_value(val):
        if pd.isna(val):
            return np.nan
        
        val_str = str(val).strip()
        
        if val_str == '' or val_str.lower() in ['nan', 'na', 'n/a']:
            return np.nan
        
        val_lower = val_str.lower()
        
        # Se já é uma chave, mantém
        if val_str in choice_map:
            return val_str
        
        # Procura pelo valor (case insensitive)
        for key, value in choice_map.items():
            if value.lower() == val_lower:
                return key
        
        # Tenta mapear comuns
        common_mappings = {
            'sim': '1', 's': '1', 'yes': '1', 'y': '1', 'true': '1',
            'não': '2', 'nao': '2', 'n': '2', 'no': '2', 'false': '2',
            'masculino': '1', 'm': '1', 'homem': '1', 'male': '1',
            'feminino': '2', 'f': '2', 'mulher': '2', 'female': '2',
            'solteiro': '1', 'casado': '2', 'separado': '3', 
            'união estável': '4', 'uniao estavel': '4', 'divorciado': '5'
        }
        
        if val_lower in common_mappings:
            return common_mappings[val_lower]
        
        return val_str  # Retorna original se não mapear
    
    return series.apply(map_value)

def normalize_yesno(series):
    """Normaliza valores YesNo (1/0)"""
    def map_yesno(val):
        if pd.isna(val):
            return np.nan
        
        val_str = str(val).strip()
        
        if val_str == '' or val_str.lower() in ['nan', 'na', 'n/a']:
            return np.nan
        
        val_lower = val_str.lower()
        
        if val_lower in ['1', 'sim', 's', 'yes', 'y', 'verdadeiro', 'true', 'verdade']:
            return '1'
        elif val_lower in ['0', '2', 'não', 'nao', 'n', 'no', 'falso', 'false']:
            return '0'
        
        return val_str
    
    return series.apply(map_yesno)

def normalize_data_values(df, field_info):
    """Normaliza valores dos dados conforme tipos do dicionário"""
    
    print(f"\n🔄 Normalizando valores conforme dicionário...")
    
    for column in df.columns:
        if column in field_info:
            field_type = field_info[column]['field_type']
            text_validation = field_info[column]['text_validation']
            
            print(f"   📝 Processando: {column} ({field_type})")
            
            try:
                # Aplica normalização baseada no tipo de campo
                if field_type == 'text':
                    if text_validation == 'date_dmy':
                        df[column] = normalize_dates(df[column])
                        print(f"      ↳ Datas normalizadas")
                    elif text_validation == 'number':
                        df[column] = normalize_numbers(df[column])
                        print(f"      ↳ Números normalizados")
                    elif text_validation == 'phone':
                        df[column] = normalize_phones(df[column])
                        print(f"      ↳ Telefones normalizados")
                    else:
                        df[column] = normalize_text(df[column])
                        print(f"      ↳ Texto normalizado")
                
                elif field_type in ['radio', 'dropdown', 'checkbox']:
                    df[column] = normalize_categorical(df[column], field_info[column]['choices'])
                    print(f"      ↳ Valores categóricos mapeados")
                
                elif field_type == 'yesno':
                    df[column] = normalize_yesno(df[column])
                    print(f"      ↳ Sim/Não normalizado")
                
                elif field_type == 'descriptive':
                    # Campos descritivos não precisam de normalização
                    print(f"      ↳ Campo descritivo (ignorado)")
                
                else:
                    # Tipo desconhecido, aplica normalização básica de texto
                    df[column] = normalize_text(df[column])
                    print(f"      ↳ Tipo '{field_type}' - Texto básico")
            
            except Exception as e:
                print(f"      ⚠️  Erro ao normalizar {column}: {str(e)[:50]}...")
                # Continua com a próxima coluna
    
    return df

def add_missing_columns(df, dict_variables):
    """Adiciona colunas ausentes que existem no dicionário"""
    
    missing_cols = set(dict_variables) - set(df.columns)
    
    if missing_cols:
        print(f"\n➕ Adicionando {len(missing_cols)} colunas ausentes:")
        for col in sorted(missing_cols):
            df[col] = np.nan
            print(f"   + {col}")
    
    return df

def reorder_columns(df, dict_variables):
    """Reordena colunas na mesma ordem do dicionário"""
    
    # Garante que todas as variáveis do dicionário estão no DataFrame
    df = add_missing_columns(df, dict_variables)
    
    # Cria lista ordenada: primeiro as do dicionário, depois as extras
    ordered_cols = []
    
    # Adiciona na ordem do dicionário
    for var in dict_variables:
        if var in df.columns:
            ordered_cols.append(var)
    
    # Adiciona colunas extras que não estão no dicionário
    for col in df.columns:
        if col not in ordered_cols:
            ordered_cols.append(col)
    
    return df[ordered_cols]

def normalize_data_to_match_dictionary(data_csv_path, dict_csv_path, output_csv_path):
    """Normaliza dados para corresponder exatamente ao dicionário"""
    
    print("=" * 70)
    print("🔄 NORMALIZADOR DE DADOS PARA REDCAP")
    print("Garantindo correspondência exata com dicionário")
    print("=" * 70)
    
    # 1. Carregar dicionário
    dict_variables, field_info = load_data_dictionary(dict_csv_path)
    
    if not dict_variables:
        print("❌ Não foi possível carregar o dicionário. Encerrando.")
        return None
    
    # 2. Carregar dados
    print(f"\n📊 Carregando dados: {data_csv_path}")
    try:
        df = pd.read_csv(data_csv_path, encoding='utf-8', sep=',')
        print(f"✅ Dados carregados: {len(df)} linhas, {len(df.columns)} colunas")
        
        # Mostra primeiras colunas
        print(f"\n📋 Primeiras 10 colunas originais:")
        for i, col in enumerate(df.columns[:10], 1):
            print(f"   {i:2d}. {col}")
        
        if len(df.columns) > 10:
            print(f"   ... e mais {len(df.columns) - 10} colunas")
            
    except Exception as e:
        print(f"❌ Erro ao carregar dados: {e}")
        return None
    
    # 3. Remover linhas totalmente vazias ou de cabeçalho duplicado
    initial_rows = len(df)
    df = df.dropna(how='all')
    
    # Remove linhas que parecem ser cabeçalho duplicado
    header_pattern = r'data_da_entrevista|prontuario|nome|fone'
    mask = df.apply(lambda row: any(
        re.search(header_pattern, str(cell), re.IGNORECASE) 
        for cell in row.values
    ), axis=1)
    
    if mask.sum() > 1:
        df = df[~mask.duplicated()]
        print(f"\n📝 Removidas {mask.sum() - 1} linhas de cabeçalho duplicado")
    
    print(f"📝 Dados após limpeza: {len(df)} linhas (removidas {initial_rows - len(df)})")
    
    # 4. Criar mapeamento de colunas
    original_columns = df.columns.tolist()
    mapping, unmapped = create_column_mapping(original_columns, dict_variables)
    
    # 5. Renomear colunas conforme mapeamento
    df = df.rename(columns=mapping)
    
    # 6. Reportar colunas não mapeadas
    if unmapped:
        print(f"\n⚠️  {len(unmapped)} colunas não mapeadas:")
        for col in unmapped[:10]:
            print(f"   - {col}")
        if len(unmapped) > 10:
            print(f"   ... e mais {len(unmapped) - 10} colunas")
        
        # Pergunta se quer mantê-las
        keep = input(f"\nManter estas {len(unmapped)} colunas não mapeadas? (s/n): ").lower()
        if keep != 's':
            df = df.drop(columns=unmapped, errors='ignore')
            print(f"🗑️  Colunas não mapeadas removidas")
    
    # 7. Normalizar valores baseado no dicionário
    df = normalize_data_values(df, field_info)
    
    # 8. Reordenar colunas conforme dicionário
    df = reorder_columns(df, dict_variables)
    
    # 9. Adicionar record_id se não existir
    if 'record_id' not in df.columns:
        df.insert(0, 'record_id', range(1, len(df) + 1))
        print(f"\n🔢 Adicionada coluna record_id (1 a {len(df)})")
    else:
        # Garante que record_id está como primeira coluna
        cols = ['record_id'] + [col for col in df.columns if col != 'record_id']
        df = df[cols]
    
    # 10. Salvar dados normalizados
    print(f"\n💾 Salvando dados normalizados: {output_csv_path}")
    df.to_csv(output_csv_path, index=False, encoding='utf-8')
    
    # 11. Gerar relatório
    generate_normalization_report(df, dict_variables, field_info, output_csv_path)
    
    return df

def generate_normalization_report(df, dict_variables, field_info, output_path):
    """Gera relatório detalhado da normalização"""
    
    print(f"\n{'='*70}")
    print("📈 RELATÓRIO DE NORMALIZAÇÃO")
    print(f"{'='*70}")
    
    print(f"\n📊 ESTATÍSTICAS FINAIS:")
    print(f"   Total de registros: {len(df)}")
    print(f"   Total de colunas: {len(df.columns)}")
    
    dict_cols_in_data = len(set(df.columns) & set(dict_variables))
    extra_cols = len(set(df.columns) - set(dict_variables))
    
    print(f"   Colunas do dicionário presentes: {dict_cols_in_data}/{len(dict_variables)} ({dict_cols_in_data/len(dict_variables)*100:.1f}%)")
    print(f"   Colunas extras: {extra_cols}")
    
    print(f"\n📋 PRIMEIRAS 10 COLUNAS (na ordem do dicionário):")
    for i, col in enumerate(df.columns[:10], 1):
        non_null = df[col].notna().sum()
        pct_non_null = (non_null / len(df)) * 100
        field_type = field_info.get(col, {}).get('field_type', 'N/A')
        print(f"   {i:2d}. {col:25s} - {non_null:3d} valores ({pct_non_null:5.1f}%) | Tipo: {field_type}")
    
    print(f"\n👀 EXEMPLO DE DADOS (primeiras 2 linhas):")
    print(df.head(2).to_string())
    
    print(f"\n✅ VERIFICAÇÃO DE INTEGRIDADE:")
    
    # Verifica colunas com muitos valores ausentes
    print(f"\n📊 COLUNAS COM MAIS DE 50% DE VALORES AUSENTES:")
    cols_with_many_nulls = []
    for col in df.columns:
        null_pct = df[col].isna().sum() / len(df) * 100
        if null_pct > 50:
            cols_with_many_nulls.append((col, null_pct))
    
    if cols_with_many_nulls:
        for col, pct in sorted(cols_with_many_nulls, key=lambda x: x[1], reverse=True)[:10]:
            print(f"   - {col}: {pct:.1f}% ausentes")
    else:
        print("   ✅ Nenhuma coluna com mais de 50% de valores ausentes")
    
    print(f"\n💡 PRÓXIMOS PASSOS:")
    print(f"   1. Importe '{output_path}' no RedCap")
    print(f"   2. Use o dicionário de dados original para configurar os campos")
    print(f"   3. Verifique campos com muitos valores nulos")
    
    # Salva relatório detalhado
    report_path = "relatorio_normalizacao.txt"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("RELATÓRIO DE NORMALIZAÇÃO DE DADOS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Arquivo de saída: {output_path}\n")
        f.write(f"Data da normalização: {datetime.now().strftime('%d/%m/%Y %H:%M')}\n\n")
        f.write(f"ESTATÍSTICAS:\n")
        f.write(f"- Total de registros: {len(df)}\n")
        f.write(f"- Total de colunas: {len(df.columns)}\n")
        f.write(f"- Colunas do dicionário: {dict_cols_in_data}/{len(dict_variables)} ({dict_cols_in_data/len(dict_variables)*100:.1f}%)\n")
        f.write(f"- Colunas extras: {extra_cols}\n\n")
        
        f.write("COLUNAS (primeiras 30):\n")
        for i, col in enumerate(df.columns[:30], 1):
            non_null = df[col].notna().sum()
            null_pct = 100 - (non_null / len(df) * 100)
            field_type = field_info.get(col, {}).get('field_type', 'N/A')
            f.write(f"{i:2d}. {col}: {non_null} não nulos ({null_pct:.1f}% nulos) | Tipo: {field_type}\n")
        
        f.write("\nVALORES AUSENTES (>50%):\n")
        for col in df.columns:
            null_pct = df[col].isna().sum() / len(df) * 100
            if null_pct > 50:
                f.write(f"- {col}: {null_pct:.1f}% ausentes\n")
    
    print(f"\n📄 Relatório detalhado salvo em: {report_path}")
    print(f"{'='*70}")

# EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    # Configuração dos arquivos
    DATA_CSV = "LIPODISTROFIA 14-10-2025.csv"
    DICT_CSV = "redcap_ordem_correta.csv"  # Arquivo gerado pelo parser
    OUTPUT_CSV = "dados_normalizados_redcap.csv"
    
    print("=" * 70)
    print("🎯 NORMALIZAÇÃO DE DADOS PARA REDCAP")
    print("Garantindo correspondência EXATA com dicionário")
    print("=" * 70)
    
    # Verifica se arquivos existem
    if not os.path.exists(DATA_CSV):
        print(f"❌ Arquivo de dados não encontrado: {DATA_CSV}")
        exit(1)
    
    if not os.path.exists(DICT_CSV):
        print(f"❌ Arquivo de dicionário não encontrado: {DICT_CSV}")
        print(f"   Execute primeiro o parser para gerar o dicionário.")
        exit(1)
    
    # Pergunta se quer ver prévia do mapeamento
    print(f"\n📋 ARQUIVOS ENCONTRADOS:")
    print(f"   Dados: {DATA_CSV}")
    print(f"   Dicionário: {DICT_CSV}")
    print(f"   Saída: {OUTPUT_CSV}")
    
    preview = input("\nVer prévia do mapeamento antes de normalizar? (s/n): ").lower()
    
    if preview == 's':
        # Carrega dicionário
        dict_vars, _ = load_data_dictionary(DICT_CSV)
        
        # Carrega cabeçalho dos dados
        df_sample = pd.read_csv(DATA_CSV, encoding='utf-8', sep=',', nrows=0)
        data_cols = df_sample.columns.tolist()
        
        # Mostra prévia do mapeamento
        print(f"\n🔍 PRÉVIA DO MAPEAMENTO (primeiras 20 colunas):")
        mapping, unmapped = create_column_mapping(data_cols[:20], dict_vars)
        
        proceed = input("\nContinuar com a normalização? (s/n): ").lower()
        if proceed != 's':
            print("👋 Operação cancelada.")
            exit(0)
    
    # Executa normalização
    normalized_df = normalize_data_to_match_dictionary(DATA_CSV, DICT_CSV, OUTPUT_CSV)
    
    if normalized_df is not None:
        print(f"\n🎉 NORMALIZAÇÃO CONCLUÍDA COM SUCESSO!")
        print(f"   Arquivo gerado: {OUTPUT_CSV}")
        print(f"   Total de registros: {len(normalized_df)}")
        print(f"   Total de colunas: {len(normalized_df.columns)}")
        
        # Mostra algumas colunas do resultado
        print(f"\n📋 COLUNAS NO ARQUIVO FINAL (primeiras 15):")
        for i, col in enumerate(normalized_df.columns[:15], 1):
            print(f"   {i:2d}. {col}")
        
        if len(normalized_df.columns) > 15:
            print(f"   ... e mais {len(normalized_df.columns) - 15} colunas")
        
        print(f"\n✅ Pronto para importação no RedCap!")