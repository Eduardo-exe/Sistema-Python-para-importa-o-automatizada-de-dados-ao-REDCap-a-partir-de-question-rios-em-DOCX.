import pandas as pd
import numpy as np
import re
from datetime import datetime

def clean_column_name(col_name):
    """Limpa nomes de colunas para padrão RedCap"""
    if pd.isna(col_name):
        return "unnamed"
    
    # Remove caracteres especiais e espaços
    col_name = str(col_name).strip().lower()
    col_name = re.sub(r'[^\w\s]', '', col_name)
    col_name = re.sub(r'\s+', '_', col_name)
    
    # Abreviações específicas
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
        'medicacao': 'med',
        'quanto_tempo': 'tempo'
    }
    
    for long, short in abbrevs.items():
        if long in col_name:
            col_name = col_name.replace(long, short)
    
    # Remove caracteres não alfanuméricos no final
    col_name = re.sub(r'_+$', '', col_name)
    
    return col_name[:30]

def normalize_data_types(df):
    """Normaliza os tipos de dados das colunas"""
    
    # Lista de colunas que devem ser numéricas
    numeric_columns = [
        'idade_na_entrevista', 'idade_atual', 'peso', 'altura', 'imc', 
        'ca', 'cq', 'cp', 'ccd', 'cce', 'pas', 'pad', 'fc',
        'prega_de_coxa', 'prega_de_braco_esquerdo', 'prega_suescapular',
        'prega_da_panturrilha', 'indice_de_kob', 'mr', 'escore_ca', 'igf1',
        'homair', 'insulina', 'peptideo_c', 'gj', 'hba1c', 'leptina',
        'ur', 'cr', 'tgo', 'tgp', 'ggt', 'fa', 'tsh', 't4l', 'cpk',
        'ct', 'ldl', 'hdl', 'tg', 'nhdl', 'vldl', 'ttgo', 'albumimuria',
        'microalbumimuria', 'racr', 'dmo', 'imma', 'img', 'gv', 'androide',
        'gtgp', 'ag', 'ginoide', 'mma', 'mm_tronco', 'mgmmii', 'mmmmi',
        'mgmmss', 'mmmss', 'mmtro', 'mgtr'
    ]
    
    # Converte colunas numéricas
    for col in numeric_columns:
        if col in df.columns:
            # Substitui vírgula por ponto para números decimais
            df[col] = df[col].astype(str).str.replace(',', '.')
            
            # Remove caracteres não numéricos exceto ponto e sinal negativo
            df[col] = df[col].apply(lambda x: re.sub(r'[^\d\.\-]', '', str(x)) if pd.notna(x) else x)
            
            # Converte para numérico, forçando erros para NaN
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Colunas de data
    date_columns = ['data_da_entrevista', 'data_de_nascimento']
    for col in date_columns:
        if col in df.columns:
            # Tenta converter várias formas de data
            df[col] = pd.to_datetime(df[col], errors='coerce', dayfirst=True)
    
    # Colunas categóricas
    categorical_columns = [
        'sexo', 'cor', 'estado_civil', 'escolaridade', 'amp_dm', 'amp_has',
        'amp_dislipidemia', 'dai', 'tabagismo', 'etilismo', 'menstruacao',
        'menopausa', 'exercico', 'hf_dm1', 'hf_dm2', 'hf_dislipidemia',
        'hf_has', 'doenca_cardiovascular', 'obesidade', 'doenca_autoimune',
        'pais_consanguineos', 'classificacao'
    ]
    
    # Limpa valores categóricos
    for col in categorical_columns:
        if col in df.columns:
            # Remove espaços extras e converte para string
            df[col] = df[col].astype(str).str.strip()
            
            # Converte valores vazios para NaN
            df[col] = df[col].replace(['', 'nan', 'None', 'NaT', 'NA'], np.nan)
    
    return df

def handle_multiple_choice_columns(df):
    """Lida com colunas que contêm múltiplas escolhas separadas por ; ou /"""
    
    multi_choice_cols = ['local', 'an']
    
    for col in multi_choice_cols:
        if col in df.columns:
            # Separa valores múltiplos
            df[col] = df[col].astype(str).str.replace(';', ',').str.replace('/', ',')
    
    return df

def normalize_medication_columns(df):
    """Normaliza colunas de medicação que podem ter múltiplos valores"""
    
    med_cols = ['medicacao', 'dose']
    
    for col in med_cols:
        if col in df.columns:
            # Remove espaços extras
            df[col] = df[col].astype(str).str.strip()
            
            # Substitui múltiplos espaços por um único
            df[col] = df[col].str.replace(r'\s+', ' ', regex=True)
    
    return df

def normalize_naturalidade_profissao(df):
    """Normaliza colunas de texto livre"""
    
    text_cols = ['naturalidade', 'profissao', 'nome']
    
    for col in text_cols:
        if col in df.columns:
            # Capitaliza primeira letra de cada palavra
            df[col] = df[col].astype(str).str.title()
            
            # Remove espaços extras
            df[col] = df[col].str.strip()
    
    return df

def normalize_telefone(df):
    """Normaliza números de telefone"""
    
    if 'fone' in df.columns:
        # Remove todos os caracteres não numéricos
        df['fone'] = df['fone'].astype(str).str.replace(r'[^\d]', '', regex=True)
        
        # Mantém apenas os primeiros 11 dígitos (DDD + número)
        df['fone'] = df['fone'].str[:11]
    
    return df

def add_record_id(df):
    """Adiciona coluna record_id baseada no índice"""
    # Se já existe uma coluna com nome similar, renomeia
    if 'record_id' in df.columns:
        df = df.rename(columns={'record_id': 'record_id_original'})
    
    # Cria novo record_id começando de 1
    df.insert(0, 'record_id', range(1, len(df) + 1))
    return df

def normalize_csv_for_redcap(input_file, output_file):
    """
    Normaliza um arquivo CSV para importação no RedCap
    
    Args:
        input_file: Caminho para o arquivo CSV de entrada
        output_file: Caminho para o arquivo CSV de saída
    """
    
    print(f"📖 Lendo arquivo: {input_file}")
    
    try:
        # Lê o CSV, pulando linhas em branco no final
        df = pd.read_csv(input_file, encoding='utf-8', sep=',', skip_blank_lines=True)
        
        print(f"✅ Arquivo carregado: {len(df)} linhas, {len(df.columns)} colunas")
        
        # Remove linhas totalmente vazias
        df = df.dropna(how='all')
        
        print(f"📊 Depois de remover linhas vazias: {len(df)} linhas")
        
        # Normaliza nomes das colunas
        print("🔄 Normalizando nomes das colunas...")
        df.columns = [clean_column_name(col) for col in df.columns]
        
        # Garante que todas as colunas tenham nomes únicos
        seen = {}
        new_columns = []
        for col in df.columns:
            if col in seen:
                seen[col] += 1
                new_columns.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 1
                new_columns.append(col)
        df.columns = new_columns
        
        # Remove a linha de cabeçalho duplicado (se houver)
        # Procura por linhas que parecem ser cabeçalho
        header_pattern = r'data_da_entrevista|prontuario|nome|fone'
        mask = df.apply(lambda row: any(
            re.search(header_pattern, str(cell), re.IGNORECASE) 
            for cell in row.values
        ), axis=1)
        
        if mask.sum() > 1:  # Mais de uma linha parece ser cabeçalho
            df = df[~mask.duplicated()]  # Mantém apenas a primeira
        
        print("🔄 Normalizando tipos de dados...")
        df = normalize_data_types(df)
        
        print("🔄 Normalizando colunas de múltipla escolha...")
        df = handle_multiple_choice_columns(df)
        
        print("🔄 Normalizando colunas de medicação...")
        df = normalize_medication_columns(df)
        
        print("🔄 Normalizando colunas de texto livre...")
        df = normalize_naturalidade_profissao(df)
        
        print("🔄 Normalizando números de telefone...")
        df = normalize_telefone(df)
        
        print("🔄 Adicionando record_id...")
        df = add_record_id(df)
        
        # Reordena colunas para ter record_id primeiro
        cols = ['record_id'] + [col for col in df.columns if col != 'record_id']
        df = df[cols]
        
        # Salva o arquivo normalizado
        print(f"💾 Salvando arquivo normalizado: {output_file}")
        df.to_csv(output_file, index=False, encoding='utf-8')
        
        # Gera um relatório
        print(f"\n{'='*70}")
        print("📈 RELATÓRIO DE NORMALIZAÇÃO")
        print(f"{'='*70}")
        print(f"Total de registros: {len(df)}")
        print(f"Total de colunas: {len(df.columns)}")
        print(f"\n📋 Primeiras colunas:")
        for i, col in enumerate(df.columns[:15], 1):
            non_null = df[col].notna().sum()
            print(f"  {i:2d}. {col:30s} - {non_null:3d} valores não nulos")
        
        if len(df.columns) > 15:
            print(f"  ... e mais {len(df.columns) - 15} colunas")
        
        print(f"\n🔍 Exemplo de dados (primeiras 5 linhas):")
        print(df[['record_id', 'nome', 'idade_na_entrevista', 'sexo']].head().to_string())
        
        print(f"\n💡 PRÓXIMOS PASSOS:")
        print(f"   1. Arquivo '{output_file}' está pronto para importação no RedCap")
        print(f"   2. Verifique o dicionário de dados gerado pelo parser")
        print(f"   3. Ajuste os tipos de campo no RedCap conforme necessário")
        print("=" * 70)
        
        return df
        
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo '{input_file}' não encontrado!")
        return None
    except Exception as e:
        print(f"❌ ERRO: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_data_dictionary_comparison(parsed_fields, normalized_df):
    """
    Compara os campos do dicionário de dados com as colunas normalizadas
    
    Args:
        parsed_fields: Lista de campos do parser
        normalized_df: DataFrame normalizado
    """
    
    print(f"\n{'='*70}")
    print("🔍 COMPARAÇÃO: Dicionário de Dados vs Dados Normalizados")
    print(f"{'='*70}")
    
    # Extrai nomes de variáveis do dicionário
    dict_vars = {field['variable_name'] for field in parsed_fields}
    
    # Extrai nomes de colunas do DataFrame
    df_cols = set(normalized_df.columns)
    
    # Campos no dicionário mas não nos dados
    missing_in_data = dict_vars - df_cols
    if missing_in_data:
        print(f"\n⚠️  Campos no dicionário MAS NÃO nos dados ({len(missing_in_data)}):")
        for var in sorted(missing_in_data)[:20]:
            print(f"  - {var}")
        if len(missing_in_data) > 20:
            print(f"  ... e mais {len(missing_in_data) - 20} campos")
    
    # Campos nos dados mas não no dicionário
    missing_in_dict = df_cols - dict_vars
    if missing_in_dict:
        print(f"\n⚠️  Campos nos dados MAS NÃO no dicionário ({len(missing_in_dict)}):")
        for col in sorted(missing_in_dict)[:20]:
            print(f"  - {col}")
        if len(missing_in_dict) > 20:
            print(f"  ... e mais {len(missing_in_dict) - 20} campos")
    
    # Campos comuns
    common = dict_vars & df_cols
    print(f"\n✅ Campos comuns ({len(common)}):")
    print(f"  Ambos os conjuntos têm {len(common)} campos em comum")
    
    return {
        'dict_vars': dict_vars,
        'df_cols': df_cols,
        'common': common,
        'missing_in_data': missing_in_data,
        'missing_in_dict': missing_in_dict
    }

# EXECUÇÃO PRINCIPAL
if __name__ == "__main__":
    # Arquivos de entrada e saída
    input_csv = "LIPODISTROFIA 14-10-2025.csv"
    output_csv = "lipodistrofia_normalizado.csv"
    data_dict_csv = "redcap_ordem_correta.csv"  # Arquivo gerado pelo parser
    
    print("=" * 70)
    print("NORMALIZADOR DE DADOS CSV -> REDCAP")
    print("Versão 1.0 - Com record_id obrigatório")
    print("=" * 70)
    
    # Normaliza os dados
    normalized_df = normalize_csv_for_redcap(input_csv, output_csv)
    
    if normalized_df is not None:
        # Se quiser comparar com o dicionário de dados gerado pelo parser
        try:
            # Carrega o dicionário de dados
            data_dict_df = pd.read_csv(data_dict_csv, encoding='utf-8')
            
            # Converte para o formato do parser (se necessário)
            parsed_fields = []
            for _, row in data_dict_df.iterrows():
                field = {
                    'variable_name': row['Variable / Field Name'],
                    'field_label': row['Field Label'],
                    'field_type': row['Field Type']
                }
                parsed_fields.append(field)
            
            # Faz a comparação
            comparison = create_data_dictionary_comparison(parsed_fields, normalized_df)
            
            # Sugere ações
            print(f"\n💡 SUGESTÕES:")
            if comparison['missing_in_dict']:
                print(f"   1. Adicione {len(comparison['missing_in_dict'])} campos ao dicionário de dados")
            
            if comparison['missing_in_data']:
                print(f"   2. Verifique se {len(comparison['missing_in_data'])} campos do dicionário existem nos dados")
            
            print(f"   3. Importe '{output_csv}' no RedCap usando o dicionário existente")
            
        except FileNotFoundError:
            print(f"\nℹ️  Dicionário de dados '{data_dict_csv}' não encontrado.")
            print(f"   Execute o parser primeiro para gerar o dicionário.")
        except Exception as e:
            print(f"\n⚠️  Não foi possível comparar com o dicionário: {e}")
    
    print("\n🎉 Processo de normalização concluído!")