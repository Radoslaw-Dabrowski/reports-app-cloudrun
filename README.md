# Reports App - Cloud Run Edition

**Serverless, on-demand reporting application optimized for Google Cloud Run**

This is a Cloud Run optimized version of the Reports App, designed to:
- ✅ Scale to zero when not in use (cost savings)
- ✅ Auto-scale on demand based on traffic
- ✅ Start quickly with optimized cold start performance
- ✅ Handle stateless execution with Redis caching
- ✅ Integrate with Google Cloud services (Cloud SQL, Secret Manager, Memorystore)

## Architecture

```
User Request
    ↓
Google Cloud Run (stateless containers)
    ↓
    ├──> Cloud SQL (PostgreSQL) - Persistent data
    ├──> AWS S3 - Report files storage
    └──> Cloud Memorystore (Redis) - Caching layer
```

### Key Features

- **Stateless Design**: No data stored in containers, everything persists in Cloud SQL or cache
- **Lazy Loading**: Database connections and S3 clients initialized only when needed
- **Intelligent Caching**: Redis-backed caching with configurable TTL
- **Health Checks**: `/health` and `/ready` endpoints for Cloud Run probes
- **Security**: Non-root container user, Secret Manager integration
- **Observability**: Cloud Logging integration, structured logs

## Prerequisites

- Google Cloud Platform account
- `gcloud` CLI installed and configured
- Docker installed (for local testing)
- Python 3.11+

## Quick Start

### 1. Clone the repository

```bash
git clone <repository-url>
cd reports-app-cloudrun
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Local Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python app/main.py
```

The app will be available at `http://localhost:8080`

### 4. Deploy to Cloud Run

```bash
# Set your project ID
export PROJECT_ID="your-gcp-project-id"
export REGION="europe-west1"

# Setup secrets
./scripts/setup-secrets.sh ${PROJECT_ID}

# Add secret values (example)
echo -n "your-db-password" | gcloud secrets versions add reports-app-db-password --data-file=-

# Deploy
./scripts/deploy.sh ${PROJECT_ID} ${REGION}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Environment (production/development) | `production` |
| `PORT` | Port to run on | `8080` |
| `DB_HOST` | PostgreSQL host | `localhost` |
| `DB_PORT` | PostgreSQL port | `5432` |
| `DB_NAME` | Database name | `reports_db` |
| `DB_USER` | Database user | `postgres` |
| `DB_PASSWORD` | Database password | - |
| `S3_BUCKET_NAME` | S3 bucket for reports | `dhc-reports` |
| `AWS_ACCESS_KEY_ID` | AWS access key | - |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - |
| `REDIS_HOST` | Redis host (Memorystore) | `localhost` |
| `ENABLE_CACHE` | Enable Redis caching | `true` |
| `CACHE_TTL` | Cache TTL in seconds | `3600` |

### Cloud Run Scaling

The service is configured to:
- **Min instances**: 0 (scale to zero when idle)
- **Max instances**: 10 (auto-scale up to 10 containers)
- **Concurrency**: 80 requests per container
- **Timeout**: 300 seconds (5 minutes)
- **Resources**: 2 CPU, 2GB RAM per container

Modify these in `cloudrun.yaml` or during deployment.

## Project Structure

```
reports-app-cloudrun/
├── app/
│   ├── __init__.py           # Flask app factory
│   ├── main.py               # Entry point
│   ├── config.py             # Configuration
│   ├── blueprints/           # Flask blueprints
│   │   └── main.py           # Main routes
│   ├── utils/                # Utilities
│   │   ├── database.py       # Database manager
│   │   ├── s3_client.py      # S3 operations
│   │   └── cache.py          # Caching utilities
│   ├── static/               # Static files
│   └── templates/            # Jinja2 templates
├── scripts/
│   ├── deploy.sh             # Deployment script
│   └── setup-secrets.sh      # Secrets setup
├── config/                   # Configuration files
├── tests/                    # Unit tests
├── Dockerfile                # Multi-stage Docker build
├── cloudrun.yaml             # Cloud Run service config
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── .dockerignore             # Docker ignore rules
├── .gcloudignore             # gcloud ignore rules
└── README.md                 # This file
```

## Development

### Running Tests

```bash
pytest tests/
```

### Building Docker Image Locally

```bash
docker build -t reports-app:local .
docker run -p 8080:8080 --env-file .env reports-app:local
```

### Database Migrations

```bash
# Connect to Cloud SQL
gcloud sql connect INSTANCE_NAME --user=postgres

# Run migrations (implement as needed)
python scripts/migrate.py
```

## Deployment

### Manual Deployment

```bash
# Build and push image
gcloud builds submit --tag gcr.io/${PROJECT_ID}/reports-app:latest

# Deploy to Cloud Run
gcloud run deploy reports-app \
    --image gcr.io/${PROJECT_ID}/reports-app:latest \
    --platform managed \
    --region europe-west1 \
    --allow-unauthenticated
```

### CI/CD Pipeline

Set up GitHub Actions or Cloud Build for automated deployments on push to main branch.

Example GitHub Actions workflow (`.github/workflows/deploy.yml`):

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - uses: google-github-actions/setup-gcloud@v0
        with:
          project_id: ${{ secrets.GCP_PROJECT_ID }}
          service_account_key: ${{ secrets.GCP_SA_KEY }}
      
      - run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/reports-app
          gcloud run deploy reports-app --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/reports-app --region europe-west1
```

## Cost Optimization

Cloud Run pricing is based on:
- **CPU time**: Only charged when container is processing requests
- **Memory**: Only charged during request processing
- **Requests**: $0.40 per million requests

**Key cost-saving features:**
- Scale to zero: No charges when idle
- Optimized cold starts: Fast initialization reduces CPU time
- Caching: Reduces database queries and processing time
- Efficient resource allocation: Right-sized CPU and memory

**Estimated costs** (100,000 requests/month, avg 200ms response time):
- Requests: ~$0.04
- CPU/Memory: ~$5-10
- **Total: ~$5-15/month**

## Monitoring

### Cloud Logging

```bash
# View logs
gcloud run services logs tail reports-app --region=europe-west1

# Follow logs
gcloud run services logs tail reports-app --region=europe-west1 --follow
```

### Metrics

Monitor in Cloud Console:
- Request count
- Request latency
- Container instance count
- Memory usage
- CPU utilization

## Troubleshooting

### Cold Start Issues

If experiencing slow cold starts:
1. Keep min instances at 1 (costs more, but eliminates cold starts)
2. Reduce Docker image size
3. Optimize database connection pooling

### Database Connection Errors

Check:
1. Cloud SQL instance is running
2. Secrets are correctly configured
3. Service account has Cloud SQL Client role

### Memory Issues

If running out of memory:
1. Increase memory allocation in `cloudrun.yaml`
2. Reduce cache size
3. Optimize DataFrame operations

## Security

- Container runs as non-root user
- Secrets stored in Secret Manager
- HTTPS only (enforced by Cloud Run)
- Security headers enabled
- No sensitive data in logs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and test locally
4. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [link]
- Email: [your-email]
