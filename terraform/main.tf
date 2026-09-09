terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Knowledge base: OpenAPI specifications and compatibility rules.
resource "google_storage_bucket" "knowledge" {
  name                        = "${var.project_id}-api-diff-kb"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

# Uploads every file in ../knowledge. Replaces upload_knowledge.py.
resource "google_storage_bucket_object" "knowledge" {
  for_each = fileset("../knowledge", "*")

  name   = each.value
  bucket = google_storage_bucket.knowledge.name
  source = "../knowledge/${each.value}"
}

# Identity the Cloud Run service runs as.
resource "google_service_account" "runner" {
  account_id   = "api-diff-runner"
  display_name = "API Diff Assistant runtime"
}

# Read-only access to the knowledge base.
resource "google_storage_bucket_iam_member" "runner_reads_knowledge" {
  bucket = google_storage_bucket.knowledge.name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.runner.email}"
}

# Permission to call Gemini. Needs setIamPolicy on the project, which lab
# accounts usually lack; an administrator can grant the same role by hand.
resource "google_project_iam_member" "runner_uses_vertex_ai" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.runner.email}"
}

resource "google_artifact_registry_repository" "containers" {
  location      = var.region
  repository_id = "cloud-run-source-deploy"
  format        = "DOCKER"
}

resource "google_cloud_run_v2_service" "assistant" {
  name                = "api-diff-assistant"
  location            = var.region
  deletion_protection = false

  template {
    service_account = google_service_account.runner.email

    containers {
      image = var.image

      ports {
        container_port = 8080
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = "global"
      }
      env {
        name  = "GOOGLE_GENAI_USE_VERTEXAI"
        value = "True"
      }
      env {
        name  = "KNOWLEDGE_SOURCE"
        value = "cloud"
      }
      env {
        name  = "KNOWLEDGE_BUCKET"
        value = google_storage_bucket.knowledge.name
      }
    }
  }
}

# Public access.
resource "google_cloud_run_v2_service_iam_member" "public" {
  location = google_cloud_run_v2_service.assistant.location
  name     = google_cloud_run_v2_service.assistant.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
