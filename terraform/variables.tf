variable "project_id" {
  description = "Google Cloud project."
  type        = string
}

variable "region" {
  description = "Region for the bucket, registry and Cloud Run service."
  type        = string
  default     = "europe-central2"
}

variable "image" {
  description = "Container image, built and pushed outside Terraform."
  type        = string
}
