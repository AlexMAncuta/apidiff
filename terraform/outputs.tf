output "service_url" {
  value = google_cloud_run_v2_service.assistant.uri
}

output "knowledge_bucket" {
  value = google_storage_bucket.knowledge.name
}

output "runtime_service_account" {
  value = google_service_account.runner.email
}
