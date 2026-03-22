use serde::{Serialize, Deserialize};
use std::time::Duration;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct OllamaRequest {
    pub model: String,
    pub prompt: String,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct OllamaResponse {
    pub response: String,
    pub model: String,
    pub total_duration: u64,
    pub load_duration: u64,
    pub prompt_eval_count: u32,
}

/// Connection pool for Ollama API with configurable timeout
#[derive(Clone)]
pub struct OllamaPool {
    base_url: String,
    timeout_secs: u64,
    pool_size: usize,
    keep_alive_ms: u64,
}

impl OllamaPool {
    pub fn new(base_url: &str, timeout_secs: u64) -> Self {
        OllamaPool {
            base_url: base_url.to_string(),
            timeout_secs,
            pool_size: 4,
            keep_alive_ms: 300,
        }
    }

    pub fn with_pool_size(mut self, size: usize) -> Self {
        self.pool_size = size;
        self
    }

    pub fn with_keep_alive(mut self, ms: u64) -> Self {
        self.keep_alive_ms = ms;
        self
    }

    pub fn get_base_url(&self) -> &str {
        &self.base_url
    }

    pub fn get_timeout(&self) -> Duration {
        Duration::from_secs(self.timeout_secs)
    }

    pub fn get_pool_config(&self) -> PoolConfig {
        PoolConfig {
            pool_size: self.pool_size,
            keep_alive_ms: self.keep_alive_ms,
            timeout_secs: self.timeout_secs,
        }
    }
}

#[derive(Debug, Clone)]
pub struct PoolConfig {
    pub pool_size: usize,
    pub keep_alive_ms: u64,
    pub timeout_secs: u64,
}

impl Default for OllamaPool {
    fn default() -> Self {
        OllamaPool::new("http://localhost:11434", 30)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_pool_creation() {
        let pool = OllamaPool::new("http://localhost:11434", 30);
        assert_eq!(pool.get_base_url(), "http://localhost:11434");
        assert_eq!(pool.get_timeout().as_secs(), 30);
    }

    #[test]
    fn test_pool_configuration() {
        let pool = OllamaPool::new("http://localhost:11434", 30)
            .with_pool_size(8)
            .with_keep_alive(500);
        
        let config = pool.get_pool_config();
        assert_eq!(config.pool_size, 8);
        assert_eq!(config.keep_alive_ms, 500);
    }

    #[test]
    fn test_default_pool() {
        let pool = OllamaPool::default();
        assert_eq!(pool.get_base_url(), "http://localhost:11434");
    }
}
