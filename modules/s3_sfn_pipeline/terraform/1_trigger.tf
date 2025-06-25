resource "aws_s3_bucket" "source_bucket" {
  bucket = "${var.bucket_name_prefix}-${var.environment}"
}
resource "aws_s3_bucket" "source_bucket_processed" {
  bucket = "${var.bucket_name_prefix}-${var.environment}-processed"
}

resource "aws_s3_bucket_notification" "eventbridge_notification" {
  bucket      = aws_s3_bucket.source_bucket.id
  eventbridge = true
}

resource "aws_cloudwatch_event_rule" "s3_object_created_rule" {
  name        = "S3ObjectCreatedRule-${var.environment}"
  description = "Triggers when an object is created in the specified bucket"
  event_pattern = jsonencode({
    "source"      = ["aws.s3"],
    "detail-type" = ["Object Created"],
    "detail" : {
      "bucket" : {
        "name" : [aws_s3_bucket.source_bucket.id]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "state_machine_target" {
  rule     = aws_cloudwatch_event_rule.s3_object_created_rule.name
  arn      = aws_sfn_state_machine.s3_triggered_pipeline.arn
  role_arn = aws_iam_role.eventbridge_to_sfn_role.arn

  input_transformer {
    input_paths = {
      "s3_bucket" = "$.detail.bucket.name",
      "s3_key"    = "$.detail.object.key"
    }


  input_template = "{ \"s3_uri\": \"s3://<s3_bucket>/<s3_key>\" }"
  }
}
