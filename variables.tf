variable "gemini_api_key" {
  type        = string
  description = "Gemini API Key for the pipeline"
  sensitive   = true
}

variable "aws_region" {
  type        = string
  description = "AWS region for the pipeline"
  default = "us-east-2"
  
}
variable "environment" {
  type = string
  description = "Environment for the pipeline"
  default = "dev"
}
variable "s3_bucket_data_prefix_name" {
  type = string
  description = "S3 bucket prefix for the data"
  default = "pipeline-data-gemini"
}

variable "pipeline_path" {
  type = string
  description = "Path to the pipeline folder"
  default = "./modules/s3_sfn_pipeline/terraform" 
}