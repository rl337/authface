use crate::models::{JwtClaims, OidcIdentity, UserTier};
use chrono::{Duration, Utc};
use jsonwebtoken::{decode, encode, Algorithm, DecodingKey, EncodingKey, Header, Validation};
use serde_json;
use std::fs;
use uuid::Uuid;

#[derive(Debug, thiserror::Error)]
pub enum JwtError {
    #[error("JWT encoding error: {0}")]
    EncodingError(jsonwebtoken::errors::Error),
    #[error("JWT decoding error: {0}")]
    DecodingError(jsonwebtoken::errors::Error),
    #[error("Key file not found: {0}")]
    KeyFileNotFound(String),
    #[error("Invalid key format: {0}")]
    InvalidKeyFormat(String),
}

pub struct JwtManager {
    encoding_key: EncodingKey,
    decoding_key: DecodingKey,
    algorithm: Algorithm,
}

impl JwtManager {
    pub fn new(private_key_path: &str, public_key_path: &str) -> Result<Self, JwtError> {
        // Read private key
        let private_key = fs::read_to_string(private_key_path)
            .map_err(|_| JwtError::KeyFileNotFound(private_key_path.to_string()))?;
        
        // Read public key
        let public_key = fs::read_to_string(public_key_path)
            .map_err(|_| JwtError::KeyFileNotFound(public_key_path.to_string()))?;

        let encoding_key = EncodingKey::from_rsa_pem(private_key.as_bytes())
            .map_err(|e| JwtError::InvalidKeyFormat(format!("Private key: {}", e)))?;
        
        let decoding_key = DecodingKey::from_rsa_pem(public_key.as_bytes())
            .map_err(|e| JwtError::InvalidKeyFormat(format!("Public key: {}", e)))?;

        Ok(Self {
            encoding_key,
            decoding_key,
            algorithm: Algorithm::RS256,
        })
    }

    /// Create a JWT token from an OIDC identity
    pub fn create_token(&self, identity: &OidcIdentity, ttl_hours: u32) -> Result<String, JwtError> {
        let now = Utc::now();
        let exp = now + Duration::hours(ttl_hours as i64);
        
        let claims = JwtClaims {
            sub: identity.sub.clone(),
            name: identity.name.clone(),
            email: identity.email.clone(),
            tier: identity.tier.as_str().to_string(),
            provider: identity.provider.clone(),
            iat: now.timestamp(),
            exp: exp.timestamp(),
            jti: Uuid::new_v4().to_string(),
        };

        let header = Header::new(self.algorithm);
        encode(&header, &claims, &self.encoding_key)
            .map_err(JwtError::EncodingError)
    }

    /// Verify and decode a JWT token
    pub fn verify_token(&self, token: &str) -> Result<JwtClaims, JwtError> {
        let validation = Validation::new(self.algorithm);
        
        let token_data = decode::<JwtClaims>(token, &self.decoding_key, &validation)
            .map_err(JwtError::DecodingError)?;

        // Check if token is expired
        let now = Utc::now().timestamp();
        if token_data.claims.exp < now {
            return Err(JwtError::DecodingError(
                jsonwebtoken::errors::ErrorKind::ExpiredSignature.into()
            ));
        }

        Ok(token_data.claims)
    }

    /// Extract user tier from JWT claims
    pub fn extract_tier(claims: &JwtClaims) -> UserTier {
        match claims.tier.as_str() {
            "admin" => UserTier::Admin,
            "preferred" => UserTier::Preferred,
            "normal" => UserTier::Normal,
            "free" => UserTier::Free,
            _ => UserTier::Free, // Default to free tier
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::OidcIdentity;
    use chrono::Utc;

    fn create_test_identity() -> OidcIdentity {
        OidcIdentity {
            sub: "test_user_123".to_string(),
            name: Some("Test User".to_string()),
            email: Some("test@example.com".to_string()),
            provider: "google".to_string(),
            tier: UserTier::Normal,
            created_at: Utc::now(),
            expires_at: Utc::now() + Duration::days(7),
        }
    }

    #[test]
    fn test_jwt_creation_and_verification() {
        // This test would require actual RSA keys
        // In a real test environment, you'd generate test keys
        // or use a test key pair
        let identity = create_test_identity();
        
        // Test would verify that:
        // 1. Token can be created from identity
        // 2. Token can be verified and decoded
        // 3. Claims match the original identity
        // 4. Expired tokens are rejected
    }
}