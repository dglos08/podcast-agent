variable "aws_region" {
  description = "AWS region for application-owned infrastructure."
  type        = string
  default     = "us-east-1"
}

variable "name_prefix" {
  description = "Prefix applied to application resources."
  type        = string
  default     = "podcast-content-agent"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "tags" {
  description = "Common tags applied to supported AWS resources."
  type        = map(string)

  default = {
    Application = "podcast-content-agent"
    ManagedBy   = "terraform"
  }
}