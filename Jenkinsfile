pipeline {
    agent any

    environment {
        IMAGE_NAME    = "urlshortener"
        REGISTRY      = "ghcr.io/satlix"
        SONAR_PROJECT = "urlshortener"
    }

    stages {

        // ── Stage 1 : Checkout ──────────────────────────────────────────────
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm

                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }

                sh '''
                    echo "=== PWD ==="
                    pwd

                    echo "=== LS ROOT ==="
                    ls -la

                    echo "=== FIND FILES ==="
                    find . -maxdepth 2 -type f | sort

                    echo "=== GIT REMOTE ==="
                    git remote -v

                    echo "=== GIT FILES ==="
                    git ls-files

                    echo "=== CHECK SRC ==="
                    test -d src
                    test -f src/main.py
                    test -f tests/test_main.py

                    echo "SHA: $IMAGE_TAG"
                    git log --oneline -5
                '''
            }
        }

        // ── Stage 2 : Lint ──────────────────────────────────────────────────
        stage('Lint') {
            steps {
                sh '''
                    docker build -t ${IMAGE_NAME}:lint .
                    docker run --rm ${IMAGE_NAME}:lint \
                        sh -c "flake8 src/ --max-line-length=100"
                '''
            }
        }

        // ── Stage 3 : Build & Test ──────────────────────────────────────────
        stage('Build & Test') {
            steps {
                sh '''
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

                    docker rm -f ${IMAGE_NAME}-test || true

                    docker run --name ${IMAGE_NAME}-test ${IMAGE_NAME}:${IMAGE_TAG} \
                        sh -c "PYTHONPATH=/app pytest tests/ -v \
                               --cov=src \
                               --cov-report=xml:/app/coverage.xml \
                               --cov-report=term-missing"

                    docker cp ${IMAGE_NAME}-test:/app/coverage.xml ./coverage.xml
                '''
            }
            post {
                always {
                    sh 'docker rm ${IMAGE_NAME}-test || true'
                }
            }
        }

        // ── Stage 4 : SonarQube Analysis ────────────────────────────────────
        stage('SonarQube Analysis') {
            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        docker rm -f sonar-scan || true

                        docker create \
                            --name sonar-scan \
                            --network cicd-network \
                            -e SONAR_HOST_URL=${SONAR_HOST_URL} \
                            -e SONAR_TOKEN=${SONAR_AUTH_TOKEN} \
                            sonarsource/sonar-scanner-cli \
                            -Dsonar.projectKey=${SONAR_PROJECT} \
                            -Dsonar.sources=src \
                            -Dsonar.python.coverage.reportPaths=coverage.xml \
                            -Dsonar.python.version=3.11

                        docker cp . sonar-scan:/usr/src

                        docker start -a sonar-scan

                        docker rm sonar-scan
                    '''
                }
            }
        }

        // ── Stage 5 : Quality Gate ───────────────────────────────────────────
        stage('Quality Gate') {
            steps {
                waitForQualityGate abortPipeline: true
            }
        }

        // ── Stage 6 : Security Scan ──────────────────────────────────────────
        stage('Security Scan') {
            steps {
                sh '''
                    docker run --rm \
                        -v /var/run/docker.sock:/var/run/docker.sock \
                        -v $HOME/.cache/trivy:/root/.cache/trivy \
                        aquasec/trivy:latest image \
                        --severity HIGH,CRITICAL \
                        --exit-code 0 \
                        ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }
        }

        // ── Stage 7 : Push ───────────────────────────────────────────────────
        stage('Push') {
            steps {
                withCredentials([string(credentialsId: 'ghcr-token', variable: 'GHCR_TOKEN')]) {
                    sh '''
                        echo ${GHCR_TOKEN} | docker login ghcr.io -u satlix --password-stdin
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY}/${IMAGE_NAME}:latest
                        docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }

        // ── Stage 8 : IaC Apply ──────────────────────────────────────────────
        stage('IaC Apply') {
            steps {
                dir('infra') {
                    sh '''
                        terraform init -input=false
                        terraform apply -auto-approve \
                            -var="image_tag=${IMAGE_TAG}"
                    '''
                }
            }
        }

        // ── Stage 9 : Smoke Test ─────────────────────────────────────────────
        // Jenkins est dans un conteneur Docker → localhost = Jenkins lui-même
        // On appelle les services par leur nom DNS sur cicd-network
        stage('Smoke Test') {
            steps {
                sh '''
                    sleep 10

                    APP_URL="http://urlshortener-staging:8000"
                    PROM_URL="http://prometheus:9090"

                    # 1. Health check
                    docker run --rm --network cicd-network curlimages/curl \
                        -f "$APP_URL/health" || exit 1
                    echo "/health OK"

                    # 2. Métriques exposées
                    docker run --rm --network cicd-network curlimages/curl \
                        -s "$APP_URL/metrics" | \
                        grep -q urlshortener_urls_created_total || exit 1
                    echo "/metrics OK"

                    # 3. Test fonctionnel
                    RESULT=$(docker run --rm --network cicd-network curlimages/curl \
                        -s -X POST "$APP_URL/shorten" \
                        -H "Content-Type: application/json" \
                        -d '{"url": "https://example.com"}')
                    echo "$RESULT" | grep -q "short_code" || exit 1
                    echo "POST /shorten OK"

                    # 4. Prometheus scrape (attendre au moins 1 cycle de 15s)
                    sleep 20
                    docker run --rm --network cicd-network curlimages/curl \
                        -G -s "$PROM_URL/api/v1/query" \
                        --data-urlencode 'query=up{job="urlshortener"}' | \
                        grep -q '"value".*1' || exit 1
                    echo "Prometheus scrape OK"

                    echo "=== Smoke Test PASSED ==="
                '''
            }
            post {
                failure {
                    sh 'docker logs urlshortener-staging || true'
                }
            }
        }
    }

    post {
        always {
            sh 'docker rmi ${IMAGE_NAME}:lint || true'
        }
        success {
            echo "Pipeline complet — image ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG} déployée"
        }
        failure {
            echo "Pipeline échoué — vérifiez les logs ci-dessus"
        }
    }
}
