terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
  backend "s3" {
    bucket         = "backend-terraform-state-gdg"
    key            = "gemini-pipeline/terraform.tfstate"
    region         = "us-east-2"
    use_lockfile   = true                                          
  }
}

provider "aws" {
  region = "${var.aws_region}"
}

module "data_pipeline" {
  source = "./modules/s3_sfn_pipeline/terraform"
  bucket_name_prefix = "${var.s3_bucket_data_prefix_name}"
  environment = "${var.environment}"
  gemini_api_key = "${var.gemini_api_key}"
}

# Outputs
output "input_bucket_name" {
  description = "Name of the S3 bucket for input files"
  value       = module.data_pipeline.s3_bucket_id
}

output "output_bucket_name" {
  description = "Name of the S3 bucket for processed output files"
  value       = module.data_pipeline.s3_bucket_processed_id
}

output "state_machine_arn" {
  description = "ARN of the Step Functions state machine"
  value       = module.data_pipeline.state_machine_arn
}

