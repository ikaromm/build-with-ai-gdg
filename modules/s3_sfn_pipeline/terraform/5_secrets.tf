resource "aws_secretsmanager_secret" "gemini_api_key" {
  name        = "gemini-api-key-${var.environment}-2"
  description = "Gemini API Key for data pipeline"
  
  tags = {
    Environment = var.environment
    Project     = "gemini-pipeline"
  }
}

resource "aws_secretsmanager_secret_version" "gemini_api_key" {
  secret_id     = aws_secretsmanager_secret.gemini_api_key.id
  secret_string = jsonencode({
    api_key = var.gemini_api_key
  })
}
