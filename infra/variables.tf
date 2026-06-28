variable "image_tag" {
  description = "Tag de l'image Docker à déployer (SHA Git court)"
  type        = string
  default     = "latest"
}

variable "app_port" {
  description = "Port exposé en staging (8080 réservé à Jenkins)"
  type        = number
  default     = 8001
}

variable "container_name" {
  description = "Nom du conteneur staging"
  type        = string
  default     = "urlshortener-staging"
}

variable "docker_host" {
  description = "Socket Docker (Linux Jenkins: unix:///var/run/docker.sock, Windows: npipe:////./pipe/docker_engine)"
  type        = string
  default     = "unix:///var/run/docker.sock"
}
