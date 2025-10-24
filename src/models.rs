use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// User tier enumeration
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum UserTier {
    Admin,
    Preferred,
    Normal,
    Free,
}

impl UserTier {
    pub fn as_str(&self) -> &'static str {
        match self {
            UserTier::Admin => "admin",
            UserTier::Preferred => "preferred",
            UserTier::Normal => "normal",
            UserTier::Free => "free",
        }
    }
}

/// OIDC identity information
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OidcIdentity {
    pub sub: String,           // Subject identifier
    pub name: Option<String>,  // Full name
    pub email: Option<String>, // Email address
    pub provider: String,     // OIDC provider name
    pub tier: UserTier,       // User tier
    pub created_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
}

/// JWT token claims
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JwtClaims {
    pub sub: String,           // Subject identifier
    pub name: Option<String>,  // Full name
    pub email: Option<String>, // Email address
    pub tier: String,          // User tier as string
    pub provider: String,      // OIDC provider name
    pub iat: i64,              // Issued at
    pub exp: i64,              // Expiration time
    pub jti: String,           // JWT ID
}

/// OIDC provider configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OidcProvider {
    pub client_id: String,
    pub client_secret: String,
    pub discovery_url: String,
    pub name: String,
}

/// Application configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub server: ServerConfig,
    pub auth: AuthConfig,
    pub cloudflare: CloudflareConfig,
    pub security: SecurityConfig,
    pub oidc_providers: HashMap<String, OidcProvider>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerConfig {
    pub host: String,
    pub port: u16,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AuthConfig {
    pub oidc_ttl_days: u32,
    pub jwt_ttl_hours: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CloudflareConfig {
    pub account_id: String,
    pub namespace_id: String,
    pub api_token: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecurityConfig {
    pub jwt_private_key_path: String,
    pub jwt_public_key_path: String,
}

/// In-memory storage for active sessions
#[derive(Debug, Clone)]
pub struct SessionStore {
    pub sessions: HashMap<String, OidcIdentity>,
    pub last_cleanup: DateTime<Utc>,
}

impl SessionStore {
    pub fn new() -> Self {
        Self {
            sessions: HashMap::new(),
            last_cleanup: Utc::now(),
        }
    }

    /// Add a new session
    pub fn add_session(&mut self, session_id: String, identity: OidcIdentity) {
        self.sessions.insert(session_id, identity);
    }

    /// Get a session by ID
    pub fn get_session(&self, session_id: &str) -> Option<&OidcIdentity> {
        self.sessions.get(session_id)
    }

    /// Remove expired sessions
    pub fn cleanup_expired(&mut self) -> usize {
        let now = Utc::now();
        let initial_count = self.sessions.len();
        
        self.sessions.retain(|_, identity| identity.expires_at > now);
        
        let removed_count = initial_count - self.sessions.len();
        self.last_cleanup = now;
        removed_count
    }

    /// Get all active sessions for serialization
    pub fn get_all_sessions(&self) -> &HashMap<String, OidcIdentity> {
        &self.sessions
    }

    /// Load sessions from serialized data
    pub fn load_sessions(&mut self, sessions: HashMap<String, OidcIdentity>) {
        self.sessions = sessions;
        self.last_cleanup = Utc::now();
    }
}