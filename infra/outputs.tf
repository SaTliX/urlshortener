output "app_url" {
  value       = "http://localhost:${var.app_port}"
  description = "URL de l'application en staging"
}

output "container_id" {
  value       = docker_container.urlshortener_staging.id
  description = "ID du conteneur Docker"
}

output "network_name" {
  value       = data.docker_network.cicd.name
  description = "Nom du réseau Docker partagé"
}
