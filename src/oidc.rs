use crate::models::{OidcIdentity, OidcProvider, UserTier};
use chrono::{Duration, Utc};
use oauth2::{
    basic::BasicClient, reqwest::async_http_client, AuthUrl, AuthorizationCode, ClientId, ClientSecret,
    RedirectUrl, Scope, TokenResponse, TokenUrl,
};
use reqwest::Client;
use serde_json::Value;
use std::collections::HashMap;
use url::Url;

#[derive(Debug, thiserror::Error)]
pub enum OidcError {
    #[error("HTTP request failed: {0}")]
    HttpError(reqwest::Error),
    #[error("JSON parsing error: {0}")]
    JsonError(serde_json::Error),
    #[error("URL parsing error: {0}")]
    UrlError(url::ParseError),
    #[error("OAuth2 error: {0}")]
    OAuth2Error(oauth2::RequestTokenError<oauth2::reqwest::Error<reqwest::Error>>),
    #[error("Provider not found: {0}")]
    ProviderNotFound(String),
    #[error("Invalid token response")]
    InvalidTokenResponse,
    #[error("User info request failed")]
    UserInfoRequestFailed,
}

pub struct OidcManager {
    providers: HashMap<String, OidcProvider>,
    http_client: Client,
}

impl OidcManager {
    pub fn new(providers: HashMap<String, OidcProvider>) -> Self {
        Self {
            providers,
            http_client: Client::new(),
        }
    }

    /// Get authorization URL for a provider
    pub fn get_authorization_url(&self, provider_name: &str, redirect_uri: &str) -> Result<String, OidcError> {
        let provider = self.providers.get(provider_name)
            .ok_or_else(|| OidcError::ProviderNotFound(provider_name.to_string()))?;

        // Create OAuth2 client
        let client = BasicClient::new(
            ClientId::new(provider.client_id.clone()),
            Some(ClientSecret::new(provider.client_secret.clone())),
            AuthUrl::new(provider.discovery_url.clone())
                .map_err(|e| OidcError::UrlError(e))?,
            Some(TokenUrl::new(provider.discovery_url.clone())
                .map_err(|e| OidcError::UrlError(e))?),
        )
        .set_redirect_uri(RedirectUrl::new(redirect_uri.to_string())
            .map_err(|e| OidcError::UrlError(e))?);

        // Generate authorization URL
        let (auth_url, _) = client
            .authorize_url(oauth2::CsrfToken::new_random)
            .add_scope(Scope::new("openid".to_string()))
            .add_scope(Scope::new("profile".to_string()))
            .add_scope(Scope::new("email".to_string()))
            .url();

        Ok(auth_url.to_string())
    }

    /// Exchange authorization code for tokens
    pub async fn exchange_code(&self, provider_name: &str, code: &str, redirect_uri: &str) -> Result<OidcIdentity, OidcError> {
        let provider = self.providers.get(provider_name)
            .ok_or_else(|| OidcError::ProviderNotFound(provider_name.to_string()))?;

        // Create OAuth2 client
        let client = BasicClient::new(
            ClientId::new(provider.client_id.clone()),
            Some(ClientSecret::new(provider.client_secret.clone())),
            AuthUrl::new(provider.discovery_url.clone())
                .map_err(|e| OidcError::UrlError(e))?,
            Some(TokenUrl::new(provider.discovery_url.clone())
                .map_err(|e| OidcError::UrlError(e))?),
        )
        .set_redirect_uri(RedirectUrl::new(redirect_uri.to_string())
            .map_err(|e| OidcError::UrlError(e))?);

        // Exchange code for token
        let token_result = client
            .exchange_code(AuthorizationCode::new(code.to_string()))
            .request_async(async_http_client)
            .await
            .map_err(OidcError::OAuth2Error)?;

        let access_token = token_result.access_token().secret();

        // Get user info
        let user_info = self.get_user_info(provider, access_token).await?;

        // Create OIDC identity
        let identity = OidcIdentity {
            sub: user_info.get("sub")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string(),
            name: user_info.get("name")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string()),
            email: user_info.get("email")
                .and_then(|v| v.as_str())
                .map(|s| s.to_string()),
            provider: provider_name.to_string(),
            tier: self.determine_user_tier(&user_info),
            created_at: Utc::now(),
            expires_at: Utc::now() + Duration::days(7), // Default 7 days
        };

        Ok(identity)
    }

    /// Get user information from OIDC provider
    async fn get_user_info(&self, provider: &OidcProvider, access_token: &str) -> Result<Value, OidcError> {
        // For now, we'll use a simplified approach
        // In a real implementation, you'd fetch from the userinfo endpoint
        // This is a placeholder that would need to be implemented based on
        // the specific OIDC provider's userinfo endpoint
        
        // Example for Google:
        let userinfo_url = if provider.name == "google" {
            "https://www.googleapis.com/oauth2/v2/userinfo"
        } else {
            // Default userinfo endpoint (would need to be discovered)
            "https://api.provider.com/userinfo"
        };

        let response = self.http_client
            .get(userinfo_url)
            .bearer_auth(access_token)
            .send()
            .await
            .map_err(OidcError::HttpError)?;

        if !response.status().is_success() {
            return Err(OidcError::UserInfoRequestFailed);
        }

        let user_info: Value = response.json().await.map_err(OidcError::JsonError)?;
        Ok(user_info)
    }

    /// Determine user tier based on user info
    fn determine_user_tier(&self, user_info: &Value) -> UserTier {
        // This is a simplified implementation
        // In a real system, you'd have more sophisticated logic
        // based on user attributes, organization membership, etc.
        
        // Check if user has admin email domain
        if let Some(email) = user_info.get("email").and_then(|v| v.as_str()) {
            if email.ends_with("@admin.company.com") {
                return UserTier::Admin;
            }
            if email.ends_with("@preferred.company.com") {
                return UserTier::Preferred;
            }
        }

        // Default to normal tier
        UserTier::Normal
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    fn create_test_provider() -> OidcProvider {
        OidcProvider {
            client_id: "test_client_id".to_string(),
            client_secret: "test_client_secret".to_string(),
            discovery_url: "https://accounts.google.com/.well-known/openid_configuration".to_string(),
            name: "google".to_string(),
        }
    }

    #[test]
    fn test_oidc_manager_creation() {
        let mut providers = HashMap::new();
        providers.insert("google".to_string(), create_test_provider());
        
        let manager = OidcManager::new(providers);
        assert_eq!(manager.providers.len(), 1);
    }

    #[test]
    fn test_user_tier_determination() {
        let manager = OidcManager::new(HashMap::new());
        
        // Test admin tier
        let admin_user = serde_json::json!({
            "email": "admin@admin.company.com"
        });
        assert_eq!(manager.determine_user_tier(&admin_user), UserTier::Admin);
        
        // Test preferred tier
        let preferred_user = serde_json::json!({
            "email": "user@preferred.company.com"
        });
        assert_eq!(manager.determine_user_tier(&preferred_user), UserTier::Preferred);
        
        // Test normal tier
        let normal_user = serde_json::json!({
            "email": "user@example.com"
        });
        assert_eq!(manager.determine_user_tier(&normal_user), UserTier::Normal);
    }
}