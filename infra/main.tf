terraform {
  required_providers {
    docker = {
      source = "kreuzwerker/docker"
    }
  }
}

provider "docker" {}

# -------------------------
# Network
# -------------------------
resource "docker_network" "app_net" {
  name = "app-network"
}

# -------------------------
# Build (CLI実行)
# -------------------------
resource "null_resource" "docker_build" {
  provisioner "local-exec" {
    command = "docker build -t data-analysis-app ${path.module}/.."
  }

  # 変更検知用（Dockerfileが変わったら再build）
  triggers = {
    dockerfile_hash = filemd5("${path.module}/../Dockerfile")
  }
}

# -------------------------
# Redis
# -------------------------
resource "docker_container" "redis" {
  name  = "redis"
  image = "redis:7"

  networks_advanced {
    name = docker_network.app_net.name
  }
}

# -------------------------
# FastAPI ×2
# -------------------------
resource "docker_container" "app" {
  count = 2

  name  = "analysis-${count.index}"
  image = "data-analysis-app:latest"

  networks_advanced {
    name = docker_network.app_net.name
  }

  depends_on = [
    null_resource.docker_build,
    docker_container.redis
  ]
}

resource "docker_container" "nginx" {
  name  = "lb"
  image = "nginx:latest"

  ports {
    internal = 80
    external = 80
  }

  networks_advanced {
    name = docker_network.app_net.name
  }

  volumes {
    host_path      = abspath("${path.module}/../nginx.conf")
    container_path = "/etc/nginx/nginx.conf"
  }

  depends_on = [docker_container.app]
}