variable "layer_name" {
  default = "gemini-dependencies"
}

resource "null_resource" "install_layer_dependencies" {
  triggers = {
    requirements_hash = filemd5("${var.lambda_path}/requirements.txt")
    always_run = timestamp()
  }

  provisioner "local-exec" {
    command = <<EOT
      # Remove build folder if it exists
      rm -rf "${path.root}/build"
      
      # Create directory structure
      mkdir -p "${path.root}/build/layer/python"
      
      # Use Docker with Python base image to install dependencies for x86_64
      docker run --rm \
        --platform linux/amd64 \
        -v "${path.root}/build/layer/python:/opt/python" \
        -v "${var.lambda_path}/requirements.txt:/requirements.txt" \
        -w /opt \
        python:3.12-slim \
        bash -c "pip install -r /requirements.txt -t /opt/python --no-cache-dir"
      
      # Check if dependencies were installed
      if [ ! "$(ls -A ${path.root}/build/layer/python)" ]; then
        echo "Error: No dependencies were installed"
        exit 1
      fi
    EOT
  }
}

data "archive_file" "layer_zip" {
  depends_on = [null_resource.install_layer_dependencies]

  type        = "zip"
  source_dir  = "${path.root}/build/layer"
  output_path = "${path.root}/build/layer.zip"
}

resource "aws_lambda_layer_version" "project_dependencies_layer" {
  depends_on = [data.archive_file.layer_zip]

  filename               = data.archive_file.layer_zip.output_path
  source_code_hash       = data.archive_file.layer_zip.output_base64sha256
  layer_name             = "${var.layer_name}-${var.environment}"
  compatible_runtimes    = [var.python_version]
  compatible_architectures = ["x86_64"]
}

data "archive_file" "start_job_zip" {
  type        = "zip"
  source_file = "${var.lambda_path}/${var.start_job_filename}/${var.start_job_filename}.py"
  output_path = "${var.lambda_path}/${var.start_job_filename}/${var.start_job_filename}.zip"
}

resource "aws_lambda_function" "start_job_lambda" {
  function_name = "gemini-start-job-${var.environment}"
  handler       = "${var.start_job_filename}.handler"
  runtime       = var.python_version
  role          = aws_iam_role.lambda_execution_role.arn
  architectures = ["x86_64"]
  timeout       = 60
  memory_size   = 512

  filename         = data.archive_file.start_job_zip.output_path
  source_code_hash = data.archive_file.start_job_zip.output_base64sha256
  
  layers = [
    aws_lambda_layer_version.project_dependencies_layer.arn
  ]
}

data "archive_file" "check_status_zip" {
  type        = "zip"
  source_file = "${var.lambda_path}/${var.check_status_filename}/${var.check_status_filename}.py"
  output_path = "${var.lambda_path}/${var.check_status_filename}/${var.check_status_filename}.zip"
}

resource "aws_lambda_function" "check_status_lambda" {
  function_name = "gemini-check-status-${var.environment}"
  handler       = "${var.check_status_filename}.handler"
  runtime       = var.python_version
  role          = aws_iam_role.lambda_execution_role.arn
  architectures = ["x86_64"]
  timeout       = 60
  memory_size   = 512

  filename         = data.archive_file.check_status_zip.output_path
  source_code_hash = data.archive_file.check_status_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.project_dependencies_layer.arn
  ]
}