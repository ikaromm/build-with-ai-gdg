resource "aws_sfn_state_machine" "s3_triggered_pipeline" {
  name     = "S3TriggeredGeminiPipeline-${var.environment}"
  role_arn = aws_iam_role.sfn_execution_role.arn

  definition = jsonencode({
    Comment = "Pipeline to enrich data with Gemini, triggered by S3 - Optimized with exponential backoff",
    StartAt = "StartGeminiJob",
    States = {
      StartGeminiJob = {
        Type     = "Task",
        Resource = aws_lambda_function.start_job_lambda.arn,
        ResultPath = "$.job_details",
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"],
            IntervalSeconds = 2,
            MaxAttempts = 3,
            BackoffRate = 2.0
          }
        ],
        Catch = [
          {
            ErrorEquals = ["States.ALL"],
            Next = "JobStartFailed",
            ResultPath = "$.error"
          }
        ],
        Next = "InitializeRetryCounter"
      },
      
      InitializeRetryCounter = {
        Type = "Pass",
        Result = {
          "retry_count": 0,
          "max_retries": 5,
          "initial_wait": 15,
          "wait_seconds": 15
        },
        ResultPath = "$.retry_config",
        Next = "WaitBeforeCheck"
      },
      
      WaitBeforeCheck = {
        Type = "Wait",
        SecondsPath = "$.retry_config.wait_seconds",
        Next = "CheckJobStatus"
      },
      
      CheckJobStatus = {
        Type     = "Task",
        Resource = aws_lambda_function.check_status_lambda.arn,
        ResultPath = "$.status_check",
        Retry = [
          {
            ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException"],
            IntervalSeconds = 1,
            MaxAttempts = 2,
            BackoffRate = 2.0
          }
        ],
        Catch = [
          {
            ErrorEquals = ["States.ALL"],
            Next = "StatusCheckFailed",
            ResultPath = "$.error"
          }
        ],
        Next = "EvaluateJobStatus"
      },
      
      EvaluateJobStatus = {
        Type = "Choice",
        Choices = [
          {
            Variable = "$.status_check.status",
            StringEquals = "COMPLETED",
            Next = "JobCompleted"
          },
          {
            Variable = "$.status_check.status",
            StringEquals = "ERROR",
            Next = "JobFailed"
          },
          {
            And = [
              {
                Variable = "$.status_check.status",
                StringEquals = "IN_PROGRESS"
              },
              {
                Variable = "$.retry_config.retry_count",
                NumericLessThan = 20
              }
            ],
            Next = "CalculateNextWait"
          }
        ],
        Default = "MaxRetriesExceeded"
      },
      
      CalculateNextWait = {
        Type = "Pass",
        Parameters = {
          "retry_count.$": "States.MathAdd($.retry_config.retry_count, 1)",
          "max_retries.$": "$.retry_config.max_retries",
          "initial_wait.$": "$.retry_config.initial_wait",
          "wait_seconds": 45
        },
        ResultPath = "$.retry_config",
        Next = "WaitBeforeCheck"
      },
      
      JobCompleted = {
        Type = "Pass",
        Parameters = {
          "status": "SUCCESS",
          "job_id.$": "$.job_details.job_id",
          "result.$": "$.status_check.result",
          "total_retries.$": "$.retry_config.retry_count",
          "completed_at.$": "$$.State.EnteredTime"
        },
        Next = "Success"
      },
      
      JobFailed = {
        Type = "Pass",
        Parameters = {
          "status": "FAILED",
          "job_id.$": "$.job_details.job_id",
          "error.$": "$.status_check.error",
          "total_retries.$": "$.retry_config.retry_count"
        },
        Next = "Fail"
      },
      
      JobStartFailed = {
        Type = "Pass",
        Parameters = {
          "status": "START_FAILED",
          "error.$": "$.error"
        },
        Next = "Fail"
      },
      
      StatusCheckFailed = {
        Type = "Pass",
        Parameters = {
          "status": "STATUS_CHECK_FAILED",
          "job_id.$": "$.job_details.job_id",
          "error.$": "$.error",
          "total_retries.$": "$.retry_config.retry_count"
        },
        Next = "Fail"
      },
      
      MaxRetriesExceeded = {
        Type = "Pass",
        Parameters = {
          "status": "TIMEOUT",
          "job_id.$": "$.job_details.job_id",
          "total_retries.$": "$.retry_config.retry_count",
          "message": "Job exceeded maximum retry attempts"
        },
        Next = "Fail"
      },
      
      Success = {
        Type = "Succeed"
      },
      
      Fail = {
        Type = "Fail"
      }
    }
  })

  depends_on = [aws_iam_role_policy_attachment.attach_lambda_invoke_to_sfn_role]
}