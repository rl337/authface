# AuthFace

A memory-compact Rust service for multi-website authentication and authorization using OIDC providers.

## Features

- **OIDC Authentication**: Support for multiple OIDC providers (Google, GitHub, etc.)
- **JWT Token Issuance**: Secure JWT tokens with user tiers and expiration
- **In-Memory Storage**: Fast, memory-efficient session storage with TTL
- **Cloudflare KV Integration**: Persistent session storage with automatic serialization
- **User Tiers**: Admin, Preferred, Normal, and Free user tiers
- **Health Monitoring**: Built-in health and status endpoints
- **Docker Support**: Container-ready with health checks

## Architecture

### Core Components

- **OIDC Manager**: Handles authentication flows with various providers
- **JWT Manager**: Creates and verifies JWT tokens with RSA signing
- **Session Store**: In-memory storage with automatic cleanup
- **Cloudflare KV Manager**: Persistent storage for session data

### User Tiers

- `admin`: Full access to all features
- `preferred`: Enhanced features and priority
- `normal`: Standard access level
- `free`: Basic access level

## API Endpoints

### Health & Status
- `GET /health` - Service health check
- `GET /status` - Service status with metrics

### Authentication
- `GET /auth/:provider` - Initiate OIDC authentication
- `GET /callback/:provider` - OIDC callback handler
- `POST /token` - Generate JWT token from session
- `POST /verify` - Verify JWT token

## Configuration

The service can be configured via environment variables or configuration files:

```bash
# Cloudflare KV (optional)
CLOUDFLARE_ACCOUNT_ID=your_account_id
CLOUDFLARE_NAMESPACE_ID=your_namespace_id
CLOUDFLARE_API_TOKEN=your_api_token

# JWT Keys (required)
# Private key should be at /etc/authface/jwt_private_key.pem
# Public key should be at /etc/authface/jwt_public_key.pem
```

## Development

### Prerequisites

- Docker
- Rust (for local development)

### Running Locally

```bash
# Build and run with Docker
docker build -t authface .
docker run -p 8080:8080 authface

# Or run locally with Rust
cargo run
```

### Testing

```bash
# Run all checks
./run_checks.sh

# Run tests only
cargo test
```

## Docker Deployment

The service is designed to run in a Docker container with the following requirements:

- **Base Image**: `rl337/callableapis:base`
- **Port**: 8080
- **Health Check**: `/health` endpoint
- **Status Check**: `/status` endpoint

### Health Endpoints

- **Health**: Returns `{"status": "healthy"}` when service is operational
- **Status**: Returns `{"status": "running"}` with session metrics

## Security

- JWT tokens are signed with RSA private keys
- OIDC authentication follows standard security practices
- Session data is stored securely in memory with TTL
- Cloudflare KV provides encrypted persistent storage

## Monitoring

The service integrates with the status monitoring system at https://status.callableapis.com/ when:

- Health endpoint returns `{"status": "healthy"}`
- Status endpoint returns `{"status": "running"}`
- Service is deployed to monitored nodes
- Port 8080 is accessible

## License

MIT License