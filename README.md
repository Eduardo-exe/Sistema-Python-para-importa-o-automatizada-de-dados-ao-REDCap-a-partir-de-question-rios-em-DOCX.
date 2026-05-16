# 📋 DOCX → REDCap CSV Parser

Sistema em Python para geração automática de dicionários de dados e importação de questionários no formato REDCap a partir de arquivos `.docx`.

---

## 💡 O que faz

- Lê questionários estruturados em arquivos Word (`.docx`)
- Detecta automaticamente perguntas, opções de resposta e tipos de campo
- Gera um arquivo `.csv` pronto para importação no REDCap
- Suporta branching logic (exibir campo condicionalmente com base em resposta anterior)
- Valida automaticamente campos como datas, telefones, CPF, CEP, e-mail e valores numéricos

---

## 🚀 Como usar

### 1. Instale as dependências

```bash
pip install python-docx unidecode
```

### 2. Execute o script

```bash
python parser.py
```

### 3. Informe os dados quando solicitado

```
Informe o nome do arquivo DOCX (com extensão): questionario.docx
Informe o nome do formulário no REDCap: dados_paciente
```

### 4. Resultado

Um arquivo `dados_paciente_redcap.csv` será gerado na mesma pasta, pronto para importar no REDCap.

---

## 🗂️ Estrutura esperada do DOCX

```
Seção de identificação..

1. Nome completo:
2. Data de nascimento:
3. Possui diabetes?
(1) Sim → Quanto tempo? Em quantos anos?
(2) Não
```

- Seções terminam com `..`
- Perguntas começam com número seguido de ponto ou terminam com `:`
- Opções de resposta seguem o padrão `(1) Opção`
- Subperguntas condicionais usam `→` após a opção

---

## 🔍 Tipos de campo detectados automaticamente

| Tipo | Quando é usado |
|---|---|
| `radio` | Até 5 opções de resposta |
| `dropdown` | Mais de 5 opções |
| `text` | Respostas abertas |
| `notes` | Campos com "descreva", "observação", etc. |
| `descriptive` | Títulos de seção (terminam com `..`) |

---

## ✅ Validações automáticas

| Campo | Validação aplicada |
|---|---|
| Data, nascimento | `date_dmy` |
| Telefone, celular | `phone` |
| CPF | `cpf` |
| CEP | `zipcode` |
| E-mail | `email` |
| Idade, peso, altura, pressão, IMC | `number` com min/max |

---

## 📁 Saída gerada

O CSV gerado segue o formato padrão do REDCap Data Dictionary, com as colunas:

```
Variable / Field Name, Form Name, Section Header, Field Type,
Field Label, Choices, Field Note, Text Validation Type,
Text Validation Min, Text Validation Max, Identifier?,
Branching Logic, Required Field?, ...
```

---

## 🛠️ Tecnologias

- Python 3.x
- [python-docx](https://python-docx.readthedocs.io/)
- [unidecode](https://pypi.org/project/Unidecode/)
- csv (biblioteca padrão)
- re (biblioteca padrão)

---

## 👨‍💻 Autor

**Eduardo dos Santos Oliveira**  
Estudante de Engenharia da Computação — UFMA  
[linkedin.com/in/eduardo-santos-oliveira-zip](https://linkedin.com/in/eduardo-santos-oliveira-zip)
