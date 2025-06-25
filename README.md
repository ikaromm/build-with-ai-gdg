# Build with AI - GDG

![AWS](https://img.shields.io/badge/AWS-Serverless-orange)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![Terraform](https://img.shields.io/badge/Terraform-IaC-purple)
![License](https://img.shields.io/badge/License-MIT-green)

A serverless data pipeline on AWS that demonstrates the integration between AWS services and generative AI APIs (Gemini). This project was developed for a presentation at Google Developer Group (GDG) about building solutions with AI.

## 🏗️ Architecture Overview

This project implements a fully serverless pipeline that processes CSV files containing questions and enriches them using Google's Gemini AI API.

### Components

- **S3 Bucket**: Storage for CSV files with questions and processed results
- **EventBridge**: Detects S3 uploads and triggers the pipeline
- **Step Functions**: Orchestrates the processing flow with exponential backoff retry logic
- **Lambda Functions**: 
  - `sfn_start_job`: Reads CSV, processes with Gemini, and saves results
  - `sfn_verify_status`: Monitors processing status
- **Secrets Manager**: Securely stores Gemini API key
- **IAM Roles**: Access control between services

### Processing Flow

1. CSV file uploaded to S3 bucket
2. EventBridge detects the event and triggers Step Function
3. Step Function starts Lambda processing function
4. Lambda reads CSV with native csv module, extracts questions
5. Sends questions to Gemini API with specialized prompt
6. Saves processed response back to S3
7. Step Function monitors status with exponential backoff retry

## 🛠️ Technologies Used

- **Infrastructure as Code**: Terraform
- **Runtime**: Python 3.12
- **Libraries**: boto3, google-genai (optimized without pandas)
- **Architecture**: Serverless (Lambda + Step Functions)
- **Monitoring**: CloudWatch integrated
- **Security**: IAM roles with least privilege principle

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform >= 1.0
- Docker (for building Lambda layers)
- Google Gemini API key

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd build-with-ai-gdg
```

### 2. Set Up Environment

Create a `terraform.tfvars` file:

```hcl
gemini_api_key = "your-gemini-api-key-here"
```

### 3. Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply changes
terraform apply
```

### 4. Test the Pipeline

Upload a CSV file to the created S3 bucket:

```bash
aws s3 cp data_test.csv s3://pipeline-data-gemini-dev/
```

## 📁 Project Structure

```
build-with-ai-gdg/
├── main.tf                           # Main Terraform configuration
├── variables.tf                      # Root variables
├── terraform.tfvars                  # Environment variables (not in repo)
├── data_test.csv                     # Sample test data
├── modules/
│   └── s3_sfn_pipeline/
│       ├── lambda/
│       │   ├── requirements.txt      # Python dependencies
│       │   ├── sfn_start_job/
│       │   │   └── sfn_start_job.py  # Main processing Lambda
│       │   └── sfn_verify_status/
│       │       └── sfn_verify_status.py # Status check Lambda
│       └── terraform/
│           ├── 1_trigger.tf          # S3 and EventBridge setup
│           ├── 2_lambda.tf           # Lambda functions and layers
│           ├── 3_sfn.tf              # Step Functions definition
│           ├── 4_iam.tf              # IAM roles and policies
│           ├── 5_secrets.tf          # Secrets Manager setup
│           ├── variables.tf          # Module variables
│           └── outputs.tf            # Module outputs
└── build/                            # Generated build artifacts
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `bucket_name_prefix` | S3 bucket name prefix | `my-sfn-trigger-bucket` |
| `environment` | Deployment environment | `dev` |
| `gemini_api_key` | Google Gemini API key | Required |

### Lambda Configuration

- **Runtime**: Python 3.12
- **Architecture**: x86_64
- **Timeout**: 60 seconds
- **Memory**: 512MB
- **Layer**: Optimized dependencies (boto3, google-genai)

### Step Functions Configuration

- **Retry Logic**: Exponential backoff
- **Max Retries**: 20 attempts
- **Initial Wait**: 15 seconds
- **Backoff Rate**: 2.0x

## 📊 Input Format

The pipeline expects CSV files with a column named `pergunta` (question) or any column containing the word "pergunta". Example:

```csv
pergunta
qual o objetivo do seminario?
quais foram as tecnologias utilizadas?
como posso fazer isso no GCP?
Posso utilizar essa mesma estrutura e utilizar a OPENAI?
```

## 📤 Output Format

Processed results are saved to S3 in JSON format:

```json
{
  "timestamp": "2025-06-23T16:00:00.000Z",
  "gemini_analysis": "AI-generated responses...",
  "data_summary": {
    "total_rows": 4,
    "columns": ["pergunta"],
    "sample_data": [...]
  },
  "processing_metadata": {
    "total_rows_processed": 4,
    "columns_analyzed": ["pergunta"]
  }
}
```

## 🔍 Monitoring

### CloudWatch Logs

- Lambda function logs: `/aws/lambda/gemini-start-job-dev`
- Step Function execution logs: Available in Step Functions console

### Step Function States

- `StartGeminiJob`: Initial processing
- `CheckJobStatus`: Status verification
- `JobCompleted`: Successful completion
- `JobFailed`: Processing failure
- `MaxRetriesExceeded`: Timeout after max retries

## 🛡️ Security Features

- **Secrets Management**: API keys stored in AWS Secrets Manager
- **IAM Least Privilege**: Minimal required permissions
- **Encryption**: S3 server-side encryption enabled by default

## 🔧 Troubleshooting

### Common Issues

1. **Lambda Timeout**: Increase timeout in `2_lambda.tf`
2. **Layer Build Fails**: Ensure Docker is running
3. **API Key Issues**: Verify Secrets Manager configuration
4. **S3 Permissions**: Check IAM policies in `4_iam.tf`

### Debug Commands

```bash
# Check Step Function execution
aws stepfunctions list-executions --state-machine-arn <state-machine-arn>

# View Lambda logs
aws logs tail /aws/lambda/gemini-start-job-dev --follow

# List S3 objects
aws s3 ls s3://ikaro-pipeline-data-dev/ --recursive
```

## 🚀 Advanced Usage

### Custom Prompts

Modify the prompt in `sfn_start_job.py` to customize AI responses:

```python
prompt = f"""
Your custom prompt here...
Questions: {json.dumps(data_processed["questions"])}
"""
```

### Scaling Considerations

- **Concurrent Executions**: Configure Lambda reserved concurrency
- **Large Files**: Consider S3 multipart upload for files > 5GB
- **High Throughput**: Use SQS for decoupling if needed

## 📝 Development

### Local Testing

```bash
# Install dependencies
pip install -r modules/s3_sfn_pipeline/lambda/requirements.txt

# Run tests (if available)
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Acknowledgments

- Google Developer Group (GDG) for the presentation opportunity
- AWS for the serverless services
- Google for the Gemini AI API

## 📞 Support

For questions or issues:
- Create an issue in the repository
- Contact the development team
- Check AWS documentation for service-specific issues

---

**Built with ❤️ for the GDG community**
