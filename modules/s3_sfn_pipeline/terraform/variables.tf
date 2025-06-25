variable "bucket_name_prefix" {
  type        = string
  default     = "my-sfn-trigger-bucket"
}

variable "environment" {
  type        = string
  default     = "dev"
}

variable "start_job_filename" {
  type = string
  default = "sfn_start_job"
}

variable "check_status_filename" {
  type = string
  default = "sfn_verify_status"
  
}
variable "lambda_path" {
  type = string
  default = "./modules/s3_sfn_pipeline/lambda"
  
}
variable "python_version" {
  type = string
  default = "python3.12"
}

variable "gemini_api_key" {
  type        = string
  description = "Gemini API Key"
  sensitive   = true
}
