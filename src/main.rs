mod models;
mod jwt;
mod oidc;
mod cloudflare;
mod tests;

use axum::{
    extract::{Query, State},
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::RwLock;
use tower_http::cors::CorsLayer;
use tower_http::trace::TraceLayer;
use tracing::{info, Level};
use tracing_subscriber;

use models::{AppConfig, SessionStore, OidcIdentity, UserTier};
use jwt::JwtManager;
use oidc::OidcManager;
use cloudflare::CloudflareKvManager;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthResponse {
    pub status: String,
    pub timestamp: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StatusResponse {
    pub status: String,
    pub active_sessions: usize,
    pub uptime: String,
}

#[derive(Debug, Clone)]
pub struct AppState {
    pub session_store: Arc<RwLock<SessionStore>>,
    pub jwt_manager: JwtManager,
    pub oidc_manager: OidcManager,
    pub kv_manager: Option<CloudflareKvManager>,
    pub config: AppConfig,
    pub start_time: std::time::Instant,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize tracing
    tracing_subscriber::fmt()
        .with_max_level(Level::INFO)
        .init();

    info!("Starting AuthFace service");

    // Load configuration
    let config = load_config().await?;

    // Initialize JWT manager
    let jwt_manager = JwtManager::new(
        &config.security.jwt_private_key_path,
        &config.security.jwt_public_key_path,
    )?;

    // Initialize OIDC manager
    let oidc_manager = OidcManager::new(config.oidc_providers.clone());

    // Initialize Cloudflare KV manager (if configured)
    let kv_manager = if !config.cloudflare.account_id.is_empty() {
        Some(CloudflareKvManager::new(
            config.cloudflare.account_id.clone(),
            config.cloudflare.namespace_id.clone(),
            config.cloudflare.api_token.clone(),
        ).await?)
    } else {
        None
    };

    // Create session store
    let mut session_store = SessionStore::new();

    // Load existing sessions from KV store if available
    if let Some(ref kv_manager) = kv_manager {
        if let Err(e) = session_store.load_from_kv(kv_manager).await {
            tracing::warn!("Failed to load sessions from KV store: {}", e);
        }
    }

    // Create application state
    let app_state = AppState {
        session_store: Arc::new(RwLock::new(session_store)),
        jwt_manager,
        oidc_manager,
        kv_manager,
        config,
        start_time: std::time::Instant::now(),
    };

    // Start cleanup task
    let session_store_clone = app_state.session_store.clone();
    let kv_manager_clone = app_state.kv_manager.clone();
    tokio::spawn(async move {
        let mut interval = tokio::time::interval(tokio::time::Duration::from_secs(3600)); // Every hour
        loop {
            interval.tick().await;
            
            let mut store = session_store_clone.write().await;
            let removed_count = store.cleanup_expired();
            
            if removed_count > 0 {
                tracing::info!("Cleaned up {} expired sessions", removed_count);
                
                // Serialize to KV store if available
                if let Some(ref kv_manager) = kv_manager_clone {
                    if let Err(e) = store.serialize_to_kv(kv_manager).await {
                        tracing::error!("Failed to serialize sessions to KV store: {}", e);
                    }
                }
            }
        }
    });

    // Build our application with routes
    let app = Router::new()
        .route("/health", get(health_handler))
        .route("/status", get(status_handler))
        .route("/auth/:provider", get(auth_handler))
        .route("/callback/:provider", get(callback_handler))
        .route("/token", post(token_handler))
        .route("/verify", post(verify_handler))
        .route("/", get(root_handler))
        .layer(CorsLayer::permissive())
        .layer(TraceLayer::new_for_http())
        .with_state(app_state);

    // Run the server
    let listener = tokio::net::TcpListener::bind("0.0.0.0:8080").await?;
    info!("AuthFace service listening on port 8080");
    
    axum::serve(listener, app).await?;
    Ok(())
}

async fn health_handler() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "healthy".to_string(),
        timestamp: chrono::Utc::now().to_rfc3339(),
    })
}

async fn status_handler(State(state): State<AppState>) -> Json<StatusResponse> {
    let sessions = state.session_store.read().await;
    let uptime = format!("{:?}", state.start_time.elapsed());
    
    Json(StatusResponse {
        status: "running".to_string(),
        active_sessions: sessions.sessions.len(),
        uptime,
    })
}

async fn auth_handler(
    axum::extract::Path(provider): axum::extract::Path<String>,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let redirect_uri = format!("http://localhost:8080/callback/{}", provider);
    
    match state.oidc_manager.get_authorization_url(&provider, &redirect_uri) {
        Ok(auth_url) => Ok(Json(serde_json::json!({
            "auth_url": auth_url,
            "provider": provider
        }))),
        Err(_) => Err(StatusCode::BAD_REQUEST),
    }
}

async fn callback_handler(
    axum::extract::Path(provider): axum::extract::Path<String>,
    Query(params): Query<HashMap<String, String>>,
    State(state): State<AppState>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let code = params.get("code").ok_or(StatusCode::BAD_REQUEST)?;
    let redirect_uri = format!("http://localhost:8080/callback/{}", provider);
    
    match state.oidc_manager.exchange_code(&provider, code, &redirect_uri).await {
        Ok(identity) => {
            let session_id = uuid::Uuid::new_v4().to_string();
            
            // Store session
            {
                let mut store = state.session_store.write().await;
                store.add_session(session_id.clone(), identity.clone());
            }
            
            // Create JWT token
            match state.jwt_manager.create_token(&identity, state.config.auth.jwt_ttl_hours) {
                Ok(token) => Ok(Json(serde_json::json!({
                    "token": token,
                    "session_id": session_id,
                    "user": {
                        "sub": identity.sub,
                        "name": identity.name,
                        "email": identity.email,
                        "tier": identity.tier.as_str(),
                        "provider": identity.provider
                    }
                }))),
                Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
            }
        }
        Err(_) => Err(StatusCode::BAD_REQUEST),
    }
}

async fn token_handler(
    State(state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let session_id = payload.get("session_id")
        .and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?;
    
    let store = state.session_store.read().await;
    if let Some(identity) = store.get_session(session_id) {
        match state.jwt_manager.create_token(identity, state.config.auth.jwt_ttl_hours) {
            Ok(token) => Ok(Json(serde_json::json!({
                "token": token,
                "expires_in": state.config.auth.jwt_ttl_hours * 3600
            }))),
            Err(_) => Err(StatusCode::INTERNAL_SERVER_ERROR),
        }
    } else {
        Err(StatusCode::UNAUTHORIZED)
    }
}

async fn verify_handler(
    State(state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> Result<Json<serde_json::Value>, StatusCode> {
    let token = payload.get("token")
        .and_then(|v| v.as_str())
        .ok_or(StatusCode::BAD_REQUEST)?;
    
    match state.jwt_manager.verify_token(token) {
        Ok(claims) => Ok(Json(serde_json::json!({
            "valid": true,
            "claims": claims
        }))),
        Err(_) => Ok(Json(serde_json::json!({
            "valid": false
        }))),
    }
}

async fn root_handler() -> &'static str {
    "AuthFace - Multi-website Authentication and Authorization Service"
}

async fn load_config() -> Result<AppConfig, Box<dyn std::error::Error>> {
    // For now, return a default configuration
    // In a real implementation, you'd load from config files or environment variables
    Ok(AppConfig {
        server: models::ServerConfig {
            host: "0.0.0.0".to_string(),
            port: 8080,
        },
        auth: models::AuthConfig {
            oidc_ttl_days: 7,
            jwt_ttl_hours: 24,
        },
        cloudflare: models::CloudflareConfig {
            account_id: std::env::var("CLOUDFLARE_ACCOUNT_ID").unwrap_or_default(),
            namespace_id: std::env::var("CLOUDFLARE_NAMESPACE_ID").unwrap_or_default(),
            api_token: std::env::var("CLOUDFLARE_API_TOKEN").unwrap_or_default(),
        },
        security: models::SecurityConfig {
            jwt_private_key_path: "/etc/authface/jwt_private_key.pem".to_string(),
            jwt_public_key_path: "/etc/authface/jwt_public_key.pem".to_string(),
        },
        oidc_providers: std::collections::HashMap::new(),
    })
}