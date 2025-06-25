import json
import boto3
import uuid
import csv
from datetime import datetime
from google import genai
from botocore.exceptions import ClientError
import io
from pydantic import BaseModel
from typing import List


# Pydantic models for structured output
class QuestionAnswer(BaseModel):
    question: str
    answer: str
    category: str
    technical_level: str
    aws_services_mentioned: List[str]


class GeminiAnalysis(BaseModel):
    total_questions: int
    questions_answers: List[QuestionAnswer]
    summary: str
    key_topics: List[str]


def handler(event, context):
    try:
        print("Starting Gemini job...")
        print(f"Event received: {json.dumps(event)}")

        # Configure clients
        gemini_api_key = get_gemini_api_key()
        client = genai.Client(api_key=gemini_api_key)
        s3_client = boto3.client("s3")

        # Extract S3 information
        s3_uri = event.get("s3_uri", "")
        if not s3_uri:
            raise ValueError("s3_uri is required")

        bucket_name = s3_uri.split("/")[2]
        object_key = "/".join(s3_uri.split("/")[3:])

        print(f"Reading file from S3: {s3_uri}")

        # Read data from S3 with native Python csv
        data_processed = read_and_process_csv_from_s3(
            s3_uri, s3_client, bucket_name, object_key
        )

        # Process with Gemini - iterate over each question
        print("Processing questions individually with Gemini...")
        gemini_response = process_questions_with_gemini_structured(
            client, data_processed
        )

        # Generate job ID
        job_id = f"gemini-job-{uuid.uuid4().hex[:8]}-{int(datetime.now().timestamp())}"

        # Save result to S3
        output_key = f"processed/{job_id}/gemini_output.json"
        output_s3_uri = save_gemini_response_to_s3(
            s3_client, bucket_name, output_key, gemini_response, data_processed
        )

        print(f"Result saved to: {output_s3_uri}")

        job_metadata = {
            "job_id": job_id,
            "status": "COMPLETED",
            "input_s3_uri": s3_uri,
            "output_s3_uri": output_s3_uri,
            "bucket_name": bucket_name,
            "input_object_key": object_key,
            "output_object_key": output_key,
            "started_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat(),
            "ttl": int(datetime.now().timestamp()) + 86400,
        }

        return {
            "statusCode": 200,
            "job_id": job_id,
            "status": "COMPLETED",
            "metadata": job_metadata,
            "gemini_response": gemini_response,
            "output_s3_uri": output_s3_uri,
        }

    except Exception as e:
        print(f"Error processing job: {str(e)}")
        return {
            "statusCode": 500,
            "error": str(e),
            "job_id": f"failed-{uuid.uuid4().hex[:8]}",
            "status": "FAILED",
        }


def read_and_process_csv_from_s3(s3_uri, s3_client, bucket_name, object_key):
    """Reads CSV file from S3 and processes with native Python csv"""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        file_content = response["Body"].read().decode("utf-8")

        # Use csv.DictReader to read the CSV
        csv_reader = csv.DictReader(io.StringIO(file_content))

        data_rows = list(csv_reader)

        columns = list(data_rows[0].keys()) if data_rows else []
        total_rows = len(data_rows)

        questions = []
        for row in data_rows:
            # Look for columns that might contain questions
            for key, value in row.items():
                if key.lower() in ["pergunta"] and value:
                    questions.append(value.strip())
                elif "pergunta" in key.lower() and value:
                    questions.append(value.strip())

        if not questions:
            for row in data_rows:
                for value in row.values():
                    if value and value.strip():
                        questions.append(value.strip())

        questions = list(dict.fromkeys(questions))

        # Create data summary
        data_summary = {
            "total_rows": total_rows,
            "columns": columns,
            "sample_data": data_rows if data_rows else [],
        }

        return {
            "questions": questions,
            "data_summary": data_summary,
            "total_rows": total_rows,
            "columns": columns,
            "raw_data": data_rows,
        }

    except Exception as e:
        print(f"Error processing CSV data: {e}")
        raise


def process_questions_with_gemini_structured(client, data_processed):
    """Processes each question individually with Gemini API using structured output"""
    try:
        questions = data_processed["questions"]

        if not questions:
            return {
                "total_questions": 0,
                "questions_answers": [],
                "summary": "No questions found in the CSV file.",
                "key_topics": [],
            }

        # Create comprehensive prompt for structured analysis
        prompt = f"""
        Você é um especialista em arquitetura de dados e inteligência artificial na AWS, apresentando sobre o projeto "Build with AI - GDG" para o Google Developer Group. 

        ## CONTEXTO DO PROJETO:
        Este é um projeto de demonstração de um pipeline de dados serverless completo na AWS que processa arquivos CSV contendo perguntas e os enriquece usando a API do Google Gemini AI. O projeto foi construído com princípios de Infrastructure as Code e padrões serverless modernos para demonstrar uma solução de IA pronta para produção.

        ## OBJETIVO DA APRESENTAÇÃO:
        Demonstrar de forma prática como construir e orquestrar soluções de inteligência artificial generativa utilizando uma arquitetura serverless robusta na AWS, capacitando a audiência do GDG a aplicar esses conceitos em seus próprios projetos de IA, enfatizando facilidade de desenvolvimento, segurança e resiliência operacional.

        ## ARQUITETURA SERVERLESS COMPLETA:
        
        ### 🔄 Componentes da Arquitetura Event-Driven:
        1. **S3 Buckets**: Armazenamento de entrada e saída com criptografia
        2. **EventBridge**: Detecção automática de eventos e roteamento
        3. **Step Functions**: Orquestração de workflow com retry exponencial (até 20 tentativas)
        4. **Lambda Functions** (Python 3.12, 512MB, 60s timeout):
           - `sfn_start_job`: Processamento principal com Gemini AI
           - `sfn_verify_status`: Monitoramento de status
        5. **Secrets Manager**: Gerenciamento seguro da chave API do Gemini
        6. **IAM Roles**: Controle de acesso com princípio de privilégio mínimo
        7. **CloudWatch**: Monitoramento e observabilidade integrados

        ### 📊 Fluxo de Processamento Detalhado:
        1. **Upload**: Arquivo CSV carregado no bucket S3 de entrada
        2. **Detecção**: EventBridge detecta evento S3 ObjectCreated
        3. **Orquestração**: Step Functions inicia state machine
        4. **Processamento**: Lambda lê CSV, extrai perguntas da coluna "pergunta"
        5. **IA**: Integração com Gemini AI usando structured output e Pydantic
        6. **Retry**: Lógica de retry exponencial (15s inicial, backoff 2.0x, max 900s)
        7. **Armazenamento**: Resultado JSON estruturado salvo no bucket de saída
        8. **Monitoramento**: Status verificado via Lambda de verificação

        ### 🛠️ Stack Tecnológico:
        - **Infrastructure as Code**: Terraform (completa automação)
        - **Runtime**: Python 3.12 com arquitetura x86_64
        - **Dependências Principais** (version-pinned):
          - `boto3==1.38.42` (AWS SDK)
          - `google-genai==1.21.1` (Gemini AI client)
          - `pydantic==2.11.7` (validação de dados)
          - `requests==2.32.4` (HTTP client)
        - **Padrões**: Serverless, event-driven, microservices
        - **Segurança**: Encryption at rest, IAM least privilege, secrets management

        ### 🔒 Características de Segurança e Produção:
        - Criptografia server-side no S3
        - Chaves API armazenadas no Secrets Manager
        - IAM roles com permissões mínimas necessárias
        - Structured logging para auditoria
        - Retry logic para resiliência
        - Monitoramento via CloudWatch

        ### 💰 Modelo de Custos Pay-per-Use:
        - Lambda: Cobrança por invocação e duração
        - S3: Armazenamento e transferência
        - Step Functions: Por transição de estado
        - Gemini API: Por token processado
        - Sem custos de infraestrutura ociosa

        ### 🌐 Flexibilidade e Adaptabilidade:
        - **Cloud Agnostic**: Princípios aplicáveis ao GCP (Cloud Storage, Cloud Functions, Workflows)
        - **AI Provider Agnostic**: Facilmente adaptável para OpenAI, Anthropic, etc.
        - **Escalabilidade**: Auto-scaling nativo dos serviços serverless
        - **Extensibilidade**: Modular para adicionar novos processamentos

        ## FORMATO DE ENTRADA E SAÍDA:
        
        ### Entrada (CSV):
        ```csv
        pergunta
        qual o objetivo do seminario?
        quais foram as tecnologias utilizadas?
        ```

        ### Saída (JSON Estruturado):
        - Análise estruturada com Pydantic models
        - Categorização automática das perguntas
        - Identificação de serviços AWS mencionados
        - Níveis técnicos (basic/intermediate/advanced)
        - Resumo executivo e tópicos-chave
        - Metadados de processamento

        ## INSTRUÇÕES PARA ANÁLISE:
        Para cada pergunta fornecida, você deve:
        1. **Responder tecnicamente** considerando o contexto completo do projeto
        2. **Categorizar** (Objetivo, Tecnologias, Arquitetura, Implementação, Comparação, Adaptabilidade, Custos, Segurança, etc.)
        3. **Classificar nível técnico** (basic, intermediate, advanced)
        4. **Identificar serviços AWS** mencionados ou relevantes à resposta
        5. **Manter foco educacional** para audiência do GDG
        6. **Enfatizar aspectos práticos** e aplicabilidade real
        7. **Destacar benefícios** da arquitetura serverless e IA generativa

        ## PERGUNTAS A ANALISAR:
        {json.dumps(questions, indent=2, ensure_ascii=False)}

        Analise cada pergunta individualmente fornecendo respostas detalhadas que demonstrem o valor prático desta arquitetura serverless com IA para desenvolvedores e arquitetos de soluções.
        """

        # Use structured output with Pydantic model
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": GeminiAnalysis,
            },
        )

        # Parse the structured response
        analysis: GeminiAnalysis = response.parsed

        # Convert to dict for JSON serialization
        return {
            "total_questions": analysis.total_questions,
            "questions_answers": [
                {
                    "question": qa.question,
                    "answer": qa.answer,
                    "category": qa.category,
                    "technical_level": qa.technical_level,
                    "aws_services_mentioned": qa.aws_services_mentioned,
                }
                for qa in analysis.questions_answers
            ],
            "summary": analysis.summary,
            "key_topics": analysis.key_topics,
            "raw_response_text": response.text,  # Keep original text as backup
        }

    except Exception as e:
        print(f"Error processing with Gemini: {e}")
        # Fallback to simple processing if structured fails
        return process_questions_fallback(client, data_processed)


def process_questions_fallback(client, data_processed):
    """Fallback method if structured processing fails"""
    try:
        questions = data_processed["questions"]

        # Simple prompt for fallback
        prompt = f"""
        Responda as seguintes perguntas sobre o projeto Build with AI - GDG (pipeline serverless AWS + Gemini):
        
        Perguntas:
        {json.dumps(questions, indent=2, ensure_ascii=False)}
        
        Para cada pergunta, forneça uma resposta clara e técnica.
        """

        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )

        return {
            "total_questions": len(questions),
            "questions_answers": [
                {
                    "question": q,
                    "answer": "Resposta processada via fallback - veja raw_response_text",
                    "category": "general",
                    "technical_level": "intermediate",
                    "aws_services_mentioned": [],
                }
                for q in questions
            ],
            "summary": "Processamento via fallback devido a erro na análise estruturada",
            "key_topics": ["aws", "serverless", "gemini", "pipeline"],
            "raw_response_text": response.text,
            "fallback_used": True,
        }

    except Exception as e:
        print(f"Error in fallback processing: {e}")
        raise


def save_gemini_response_to_s3(
    s3_client, bucket_name, output_key, gemini_response, processed_data
):
    """Saves structured Gemini response to S3"""
    try:
        # Create enhanced output structure with structured data
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "structured_analysis": gemini_response,  # This now contains structured data
            "data_summary": processed_data["data_summary"],
            "processing_metadata": {
                "total_rows_processed": processed_data["total_rows"],
                "columns_analyzed": processed_data["columns"],
                "questions_extracted": len(processed_data["questions"]),
                "processing_type": "structured"
                if not gemini_response.get("fallback_used")
                else "fallback",
            },
            "questions_processed": processed_data["questions"],
        }

        output_json = json.dumps(output_data, indent=2, ensure_ascii=False)
        bucket_name = bucket_name + "-processed"
        # Save to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=output_key,
            Body=output_json.encode("utf-8"),
            ContentType="application/json",
        )

        return f"s3://{bucket_name}/{output_key}"

    except Exception as e:
        print(f"Error saving to S3: {e}")
        raise


def get_gemini_api_key():
    environment = "dev"
    secret_name = f"gemini-api-key-{environment}-2"
    region_name = "us-east-2"

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)

        # Parse JSON from secret
        secret = json.loads(get_secret_value_response["SecretString"])
        return secret["api_key"]

    except ClientError as e:
        print(f"Error retrieving secret {secret_name}: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error parsing secret: {e}")
        raise
    except KeyError as e:
        print(f"Key 'api_key' not found in secret: {e}")
        raise
