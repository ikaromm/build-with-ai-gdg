output "state_machine_arn" {
  value       = aws_sfn_state_machine.s3_triggered_pipeline.arn
}

output "s3_bucket_id" {
  value       = aws_s3_bucket.source_bucket.id
}

output "s3_bucket_processed_id" {
  value       = aws_s3_bucket.source_bucket_processed.id
}

output "lambda_layer_arn" {
  description = "The ARN of the project dependencies Lambda Layer"
  value       = aws_lambda_layer_version.project_dependencies_layer.arn
}