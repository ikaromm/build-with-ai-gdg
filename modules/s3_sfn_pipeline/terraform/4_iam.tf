resource "aws_iam_role" "eventbridge_to_sfn_role" {
  name = "EventBridgeToSfnRole-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "events.amazonaws.com" },
    }],
  })
}

resource "aws_iam_policy" "allow_sfn_start_execution_policy" {
  name = "AllowSfnStartExecutionPolicy-${var.environment}"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action   = "states:StartExecution",
      Effect   = "Allow",
      Resource = aws_sfn_state_machine.s3_triggered_pipeline.arn,
    }],
  })
}

resource "aws_iam_role_policy_attachment" "attach_sfn_start_to_eventbridge_role" {
  role       = aws_iam_role.eventbridge_to_sfn_role.name
  policy_arn = aws_iam_policy.allow_sfn_start_execution_policy.arn
}


resource "aws_iam_role" "sfn_execution_role" {
  name = "SfnExecutionRole-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "states.amazonaws.com" },
    }],
  })
}

resource "aws_iam_policy" "sfn_invoke_lambda_policy" {
  name = "SfnInvokeLambdaPolicy-${var.environment}"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow"
        Action   = "lambda:InvokeFunction"
        Resource = [
          aws_lambda_function.start_job_lambda.arn,
          aws_lambda_function.check_status_lambda.arn,
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_lambda_invoke_to_sfn_role" {
  role       = aws_iam_role.sfn_execution_role.name
  policy_arn = aws_iam_policy.sfn_invoke_lambda_policy.arn
}

resource "aws_iam_role" "lambda_execution_role" {
  name = "LambdaExecutionRole-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" },
    }],
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}


resource "aws_iam_policy" "lambda_secrets_access" {
  name        = "LambdaSecretsAccess-${var.environment}"
  description = "Allow Lambda functions to access Secrets Manager"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = aws_secretsmanager_secret.gemini_api_key.arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_secrets_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_secrets_access.arn
}

# Policy to allow Lambda to access S3 buckets
resource "aws_iam_policy" "lambda_s3_access" {
  name        = "LambdaS3Access-${var.environment}"
  description = "Allow Lambda functions to read and write to S3 buckets"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion",
          "s3:PutObject",
          "s3:PutObjectAcl",
          "s3:DeleteObject"
        ]
        Resource = [
          "${aws_s3_bucket.source_bucket.arn}/*",
          "${aws_s3_bucket.source_bucket_processed.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.source_bucket.arn,
          aws_s3_bucket.source_bucket_processed.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_s3_attachment" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = aws_iam_policy.lambda_s3_access.arn
}
