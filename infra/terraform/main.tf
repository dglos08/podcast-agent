locals {
  resource_name = "${var.name_prefix}-${var.environment}"
}

resource "aws_ecr_repository" "agent" {
  name                 = local.resource_name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_s3_bucket" "content" {
  bucket_prefix = "${local.resource_name}-"
}

resource "aws_s3_bucket_public_access_block" "content" {
  bucket = aws_s3_bucket.content.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "content" {
  bucket = aws_s3_bucket.content.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_sqs_queue" "dead_letter" {
  name = "${local.resource_name}-dlq"

  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "jobs" {
  name = "${local.resource_name}-jobs"

  visibility_timeout_seconds = 900

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dead_letter.arn
    maxReceiveCount     = 3
  })
}

data "aws_iam_policy_document" "worker" {
  statement {
    sid = "ReadWriteContent"

    actions = [
      "s3:GetObject",
      "s3:PutObject"
    ]

    resources = [
      "${aws_s3_bucket.content.arn}/*"
    ]
  }

  statement {
    sid = "ProcessJobs"

    actions = [
      "sqs:ReceiveMessage",
      "sqs:DeleteMessage",
      "sqs:ChangeMessageVisibility",
      "sqs:GetQueueAttributes"
    ]

    resources = [
      aws_sqs_queue.jobs.arn
    ]
  }
}

resource "aws_iam_policy" "worker" {
  name        = "${local.resource_name}-worker"
  description = "Least-privilege access for Podcast Content Agent workers."
  policy      = data.aws_iam_policy_document.worker.json
}