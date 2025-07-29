# 🚀 GmGnAPI Deployment Guide

Welcome to the complete deployment guide for **GmGnAPI** - your professional Python client for GMGN.ai WebSocket API.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Documentation Website](#documentation-website)
- [PyPI Publishing](#pypi-publishing)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Monitoring & Observability](#monitoring--observability)

## 🏃‍♂️ Quick Start

### 1. Install from PyPI (Coming Soon)

```bash
pip install gmgnapi
```

### 2. Install from Source

```bash
git clone https://github.com/theshadow76/GmGnAPI.git
cd GmGnAPI
pip install -e .
```

### 3. Basic Usage

```python
import asyncio
from gmgnapi import GmGnClient

async def main():
    async with GmGnClient() as client:
        await client.subscribe_new_pools()
        
        @client.on_new_pool
        async def handle_pool(data):
            print(f"New pool detected: {data}")
        
        await client.listen()

if __name__ == "__main__":
    asyncio.run(main())
```

## 📚 Documentation Website

The comprehensive documentation website is located in the `docs/` directory with the following pages:

### Available Pages

1. **index.html** - Landing page with features and quick start
2. **getting-started.html** - Detailed installation and setup guide
3. **api-reference.html** - Complete API documentation
4. **examples.html** - Practical usage examples
5. **advanced.html** - Advanced features and enterprise usage

### Local Testing

To test the documentation locally:

```bash
cd docs
python -m http.server 8000
```

Then visit `http://localhost:8000` in your browser.

### Hosting Options

#### GitHub Pages

1. Push to GitHub repository
2. Go to Settings → Pages
3. Select source: `Deploy from a branch`
4. Choose `main` branch and `/docs` folder
5. Your docs will be available at: `https://yourusername.github.io/GmGnAPI/`

#### Netlify

1. Drag and drop the `docs` folder to [Netlify](https://app.netlify.com)
2. Get instant deployment with custom domain options

#### Vercel

1. Connect your GitHub repository to [Vercel](https://vercel.com)
2. Set build settings:
   - Framework Preset: Other
   - Root Directory: `docs`
   - Build Command: (leave empty)
   - Output Directory: (leave empty)

## 📦 PyPI Publishing

### Prerequisites

1. Create PyPI account at [pypi.org](https://pypi.org)
2. Generate API token in account settings
3. Configure `.pypirc` file

### Automated Publishing

Use the provided script:

```bash
python scripts/publish_to_pypi.py
```

### Manual Publishing

```bash
# Install publishing tools
pip install build twine

# Build the package
python -m build

# Upload to PyPI
twine upload dist/*
```

### Environment Variables

Set these environment variables for automated publishing:

```bash
export PYPI_TOKEN="your-pypi-token"
export GITHUB_TOKEN="your-github-token"  # For creating releases
```

## 🏭 Production Deployment

### Environment Setup

1. **Create production environment file:**

```bash
# .env.production
GMGN_ACCESS_TOKEN=your_production_token
LOG_LEVEL=INFO
MAX_CONNECTIONS=100
RECONNECT_ATTEMPTS=5
HEARTBEAT_INTERVAL=30
DATABASE_URL=postgresql://user:pass@localhost/gmgnapi
REDIS_URL=redis://localhost:6379
MONITORING_ENABLED=true
METRICS_PORT=9090
```

2. **Production configuration:**

```python
# config/production.py
import os
from gmgnapi import GmGnConfig

config = GmGnConfig(
    access_token=os.getenv('GMGN_ACCESS_TOKEN'),
    max_reconnect_attempts=int(os.getenv('RECONNECT_ATTEMPTS', 5)),
    heartbeat_interval=int(os.getenv('HEARTBEAT_INTERVAL', 30)),
    enable_monitoring=os.getenv('MONITORING_ENABLED', 'false').lower() == 'true'
)
```

### Production Checklist

- [ ] API tokens securely stored
- [ ] Logging configured
- [ ] Monitoring enabled
- [ ] Error alerting setup
- [ ] Database configured
- [ ] Backup strategy in place
- [ ] Performance metrics tracked
- [ ] Security scanning completed

## 🐳 Docker Deployment

### Single Container

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 gmgnapi && chown -R gmgnapi:gmgnapi /app
USER gmgnapi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import gmgnapi; print('OK')" || exit 1

CMD ["python", "main.py"]
```

### Docker Compose

```yaml
version: '3.8'

services:
  gmgnapi:
    build: .
    restart: unless-stopped
    environment:
      - GMGN_ACCESS_TOKEN=${GMGN_ACCESS_TOKEN}
      - DATABASE_URL=postgresql://postgres:password@db:5432/gmgnapi
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
    networks:
      - gmgn-network

  db:
    image: postgres:15
    restart: unless-stopped
    environment:
      - POSTGRES_DB=gmgnapi
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - gmgn-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    networks:
      - gmgn-network

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    networks:
      - gmgn-network

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
    networks:
      - gmgn-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  gmgn-network:
    driver: bridge
```

## ☸️ Kubernetes Deployment

### Namespace

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: gmgnapi
```

### Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: gmgn-secrets
  namespace: gmgnapi
type: Opaque
data:
  access-token: <base64-encoded-token>
  database-url: <base64-encoded-db-url>
```

### Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: gmgnapi
  namespace: gmgnapi
  labels:
    app: gmgnapi
spec:
  replicas: 3
  selector:
    matchLabels:
      app: gmgnapi
  template:
    metadata:
      labels:
        app: gmgnapi
    spec:
      containers:
      - name: gmgnapi
        image: gmgnapi:latest
        ports:
        - containerPort: 8080
        env:
        - name: GMGN_ACCESS_TOKEN
          valueFrom:
            secretKeyRef:
              name: gmgn-secrets
              key: access-token
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: gmgn-secrets
              key: database-url
        resources:
          limits:
            memory: "1Gi"
            cpu: "500m"
          requests:
            memory: "512Mi"
            cpu: "250m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
```

### Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: gmgnapi-service
  namespace: gmgnapi
spec:
  selector:
    app: gmgnapi
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: ClusterIP
```

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gmgnapi-hpa
  namespace: gmgnapi
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: gmgnapi
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## 📊 Monitoring & Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'gmgnapi'
    static_configs:
      - targets: ['gmgnapi:8080']
    metrics_path: /metrics
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
```

### Grafana Dashboard

Create dashboards for:
- **Message Processing Rate** - Messages per second
- **Connection Health** - Active connections, reconnections
- **Error Rates** - Failed connections, processing errors
- **Resource Usage** - CPU, memory, disk usage
- **Database Performance** - Query times, connection pool

### Logging

Structured logging with JSON format:

```python
import structlog
import logging

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

### Alerting

Set up alerts for:
- Connection failures
- High error rates
- Memory usage > 80%
- CPU usage > 70%
- Disk space < 20%
- Failed health checks

## 🎯 Next Steps

1. **Deploy Documentation** - Host your docs on GitHub Pages or Netlify
2. **Publish to PyPI** - Make your package available for `pip install`
3. **Set Up CI/CD** - Automate testing and deployment
4. **Monitor Performance** - Track metrics and optimize
5. **Scale as Needed** - Add more instances or optimize code

## 📞 Support

- **Documentation**: [Your hosted docs URL]
- **Issues**: [GitHub Issues](https://github.com/theshadow76/GmGnAPI/issues)
- **Discussions**: [GitHub Discussions](https://github.com/theshadow76/GmGnAPI/discussions)
- **Email**: contact@gmgnapi.dev

---

**🎉 Congratulations!** You now have a professional-grade, production-ready GMGN API client with beautiful documentation and deployment infrastructure!
