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
        Você é um especialista em arquitetura de dados e inteligência artificial na AWS, apresentando sobre o projeto "Build with AI - GDG". 

        ## CONTEXTO DO PROJETO:
        Este é um projeto de pipeline de dados serverless na AWS que demonstra a integração entre serviços AWS e APIs de IA generativa (Gemini). O projeto foi desenvolvido para uma apresentação no Google Developer Group (GDG) sobre como construir soluções com IA.

        ## ARQUITETURA DO PROJETO:
        
        ### Componentes Principais:
        1. **S3 Bucket**: Armazenamento de arquivos CSV com perguntas
        2. **EventBridge**: Detecta uploads no S3 e dispara o pipeline
        3. **Step Functions**: Orquestra o fluxo de processamento com retry logic
        4. **Lambda Functions**: 
           - `sfn_start_job`: Lê CSV, processa com Gemini e salva resultado
           - `sfn_verify_status`: Verifica status do processamento
        5. **Secrets Manager**: Armazena chave da API do Gemini de forma segura
        6. **IAM Roles**: Controle de acesso entre serviços

        ### Fluxo de Processamento:
        1. Upload de arquivo CSV no S3
        2. EventBridge detecta o evento e dispara Step Function
        3. Step Function inicia Lambda de processamento
        4. Lambda lê CSV com módulo csv nativo, extrai perguntas
        5. Envia perguntas para API do Gemini
        6. Salva resposta processada de volta no S3
        7. Step Function monitora status com retry exponencial

        ### Tecnologias Utilizadas:
        - **Infrastructure as Code**: Terraform
        - **Linguagem**: Python 3.12
        - **Bibliotecas**: boto3, google-genai (sem pandas para otimização)
        - **Arquitetura**: Serverless (Lambda + Step Functions)
        - **Monitoramento**: CloudWatch integrado
        - **Segurança**: IAM roles com least privilege

        ## INSTRUÇÕES:
        Para cada pergunta fornecida, você deve:
        1. Responder de forma clara e técnica
        2. Categorizar a pergunta (ex: "arquitetura", "implementação", "comparação", "custos", etc.)
        3. Definir o nível técnico (basic, intermediate, advanced)
        4. Identificar serviços AWS mencionados ou relevantes
        5. Fornecer resposta detalhada considerando o contexto do projeto

        ## PERGUNTAS A ANALISAR:
        {json.dumps(questions, indent=2, ensure_ascii=False)}

        Analise cada pergunta individualmente e forneça uma resposta estruturada. Mantenha o foco na demonstração prática de como construir soluções com IA na AWS.
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
