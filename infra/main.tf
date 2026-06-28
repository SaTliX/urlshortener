terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = var.docker_host
}

# Réseau existant (créé par Jenkins/SonarQube au démarrage)
# → ne pas recréer, juste le lire
data "docker_network" "cicd" {
  name = "cicd-network"
}

resource "docker_image" "urlshortener" {
  name         = "urlshortener:${var.image_tag}"
  keep_locally = true
}

resource "docker_container" "urlshortener_staging" {
  name    = var.container_name
  image   = docker_image.urlshortener.image_id
  restart = "unless-stopped"

  networks_advanced {
    name = data.docker_network.cicd.name
  }

  ports {
    internal = 8000
    external = var.app_port
  }

  env = [
    "ENV=staging",
    "LOG_LEVEL=INFO",
  ]

  healthcheck {
    test     = ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
    interval = "30s"
    timeout  = "10s"
    retries  = 3
  }
}
