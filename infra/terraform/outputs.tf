output "ecr_repository_url" {
  description = "ECR repository used for application images."
  value       = aws_ecr_repository.agent.repository_url
}

output "content_bucket_name" {
  description = "S3 bucket used for transcript and result persistence."
  value       = aws_s3_bucket.content.id
}

output "job_queue_url" {
  description = "SQS queue used for asynchronous processing jobs."
  value       = aws_sqs_queue.jobs.url
}

output "job_queue_arn" {
  description = "ARN of the asynchronous processing queue."
  value       = aws_sqs_queue.jobs.arn
}

output "dead_letter_queue_arn" {
  description = "ARN of the failed-job dead-letter queue."
  value       = aws_sqs_queue.dead_letter.arn
}

output "worker_iam_policy_arn" {
  description = "IAM policy to attach to the worker workload identity."
  value       = aws_iam_policy.worker.arn
}