# URLShortener — Projet DevOps Groupe

API de raccourcissement d'URLs construite avec FastAPI, conteneurisée avec Docker,
et déployée via un pipeline Jenkins CI/CD complet.

## Application

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/health` | GET | Statut de l'application + nombre d'URLs stockées |
| `/shorten` | POST | Raccourcir une URL (`{"url": "https://..."}`) |
| `/r/{code}` | GET | Redirection vers l'URL originale |
| `/urls` | GET | Liste de toutes les URLs stockées |
| `/metrics` | GET | Métriques Prometheus |

## Membres du groupe

- SANTARELLI Alexi
- BOUZARIA Farès
- ROUX Alexis
- BARRAK Jason

## Lancer localement

```bash
# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
uvicorn src.main:app --reload --port 8000

# Tester
curl http://localhost:8000/health
curl -X POST http://localhost:8000/shorten \
     -H "Content-Type: application/json" \
     -d '{"url": "https://github.com"}'
```

## Lancer les tests

```bash
pytest tests/ -v --cov=src --cov-report=xml
```

## Lancer le pipeline complet

### Pré-requis
- Jenkins avec le plugin SonarQube Scanner
- SonarQube sur le réseau `cicd-network`
- Terraform installé dans le conteneur Jenkins
- Credential `ghcr-token` configuré dans Jenkins
- Le réseau `cicd-network` déjà créé (ou importé dans Terraform)

### Démarrer Jenkins et SonarQube
```bash
docker start jenkins sonarqube
```

### ⚠️ Réseau cicd-network
Si le réseau existe déjà depuis les TPs :
```bash
# Ne PAS faire docker network create cicd-network
# À la place, importer dans Terraform :
cd infra/
terraform init
docker network inspect cicd-network --format "{{.Id}}"
terraform import docker_network.cicd <ID>
terraform apply -var="image_tag=latest"
```

### Lancer le monitoring
```bash
cd monitoring/
docker compose up -d
```

## Structure du projet

```
urlshortener/
├── src/
│   └── main.py              # Application FastAPI
├── tests/
│   └── test_main.py         # 10 tests unitaires
├── infra/
│   ├── main.tf              # Ressources Docker (Terraform)
│   ├── variables.tf
│   └── outputs.tf
├── monitoring/
│   ├── prometheus.yml       # Config Prometheus
│   ├── alerts.yml           # Règles d'alerte
│   └── docker-compose.yml   # Stack Prometheus + Grafana
├── Dockerfile               # Multi-stage, image slim, tests inclus
├── docker-compose.yml       # Stack staging
├── Jenkinsfile              # Pipeline 9 stages
├── sonar-project.properties
├── .coveragerc
└── requirements.txt
```

## Pipeline CI/CD — 9 Stages

| # | Stage | Outil | Critère |
|---|-------|-------|---------|
| 1 | Checkout | Git | SHA calculé via `git rev-parse --short HEAD` |
| 2 | Lint | flake8 | 0 erreur |
| 3 | Build & Test | Docker + pytest | Tests verts + coverage.xml extrait via `docker cp` |
| 4 | SonarQube Analysis | sonar-scanner | Analyse envoyée |
| 5 | Quality Gate | waitForQualityGate | Gate vert |
| 6 | Security Scan | Trivy | Rapport CVE dans les logs |
| 7 | Push | docker push | Image sur ghcr.io/satlix |
| 8 | IaC Apply | Terraform | Staging provisionné port 8001 |
| 9 | Smoke Test | curl | /health + /metrics + /shorten + Prometheus UP |

## Dashboard Grafana

Après avoir lancé la stack monitoring, configurer Grafana sur `http://localhost:3000` (admin/admin) :

1. **Datasource** : `http://prometheus:9090` (pas localhost)
2. **Panel 1 — Requêtes/s** : `rate(http_requests_total{handler="/shorten"}[1m])`
3. **Panel 2 — URLs créées** : `urlshortener_urls_created_total`
4. **Panel 3 — Latence p99** : `histogram_quantile(0.99, rate(urlshortener_shorten_duration_seconds_bucket[5m]))`
5. **Panel 4 — Taux d'erreurs** : `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100`
