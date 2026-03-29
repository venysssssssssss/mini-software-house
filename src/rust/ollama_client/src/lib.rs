use serde::{Deserialize, Serialize};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;
use std::time::Duration;

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct OllamaRequest {
    pub model: String,
    pub prompt: String,
    #[serde(default)]
    pub stream: bool,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct OllamaResponse {
    #[serde(default)]
    pub response: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub total_duration: u64,
    #[serde(default)]
    pub load_duration: u64,
    #[serde(default)]
    pub prompt_eval_count: u32,
}

/// Connection pool for Ollama API with configurable timeout
#[derive(Clone)]
pub struct OllamaPool {
    base_url: String,
    timeout_secs: u64,
    pool_size: usize,
    keep_alive_ms: u64,
    client: reqwest::blocking::Client,
}

impl OllamaPool {
    pub fn new(base_url: &str, timeout_secs: u64) -> Self {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .pool_max_idle_per_host(4)
            .build()
            .expect("failed to create HTTP client");

        OllamaPool {
            base_url: base_url.to_string(),
            timeout_secs,
            pool_size: 4,
            keep_alive_ms: 300,
            client,
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

    /// Send a chat/generate request to Ollama and return the response.
    pub fn chat(&self, request: &OllamaRequest) -> Result<OllamaResponse, String> {
        let url = format!("{}/api/generate", self.base_url);

        let body = serde_json::json!({
            "model": request.model,
            "prompt": request.prompt,
            "stream": false,
        });

        let resp = self
            .client
            .post(&url)
            .json(&body)
            .send()
            .map_err(|e| format!("HTTP error: {}", e))?;

        if !resp.status().is_success() {
            return Err(format!("Ollama returned status {}", resp.status()));
        }

        let ollama_resp: OllamaResponse = resp
            .json()
            .map_err(|e| format!("JSON decode error: {}", e))?;

        Ok(ollama_resp)
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

// ---- C FFI ----

use std::sync::OnceLock;

static GLOBAL_POOL: OnceLock<OllamaPool> = OnceLock::new();

fn get_or_init_pool() -> &'static OllamaPool {
    GLOBAL_POOL.get_or_init(OllamaPool::default)
}

/// C FFI: Send a chat request. Returns a malloc'd JSON string or null on error.
/// Caller must free the result with `ollama_free_string`.
#[no_mangle]
pub extern "C" fn ollama_chat(model: *const c_char, prompt: *const c_char) -> *mut c_char {
    if model.is_null() || prompt.is_null() {
        return std::ptr::null_mut();
    }

    let model_str = unsafe { CStr::from_ptr(model) };
    let prompt_str = unsafe { CStr::from_ptr(prompt) };

    let model_str = match model_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };
    let prompt_str = match prompt_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let request = OllamaRequest {
        model: model_str.to_string(),
        prompt: prompt_str.to_string(),
        stream: false,
    };

    let pool = get_or_init_pool();
    match pool.chat(&request) {
        Ok(resp) => match serde_json::to_string(&resp) {
            Ok(json) => match CString::new(json) {
                Ok(cstr) => cstr.into_raw(),
                Err(_) => std::ptr::null_mut(),
            },
            Err(_) => std::ptr::null_mut(),
        },
        Err(_) => std::ptr::null_mut(),
    }
}

/// C FFI: Free a string allocated by ollama_chat.
#[no_mangle]
pub extern "C" fn ollama_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        unsafe {
            let _ = CString::from_raw(ptr);
        }
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

    #[test]
    fn test_request_serialization() {
        let req = OllamaRequest {
            model: "qwen2.5:3b".to_string(),
            prompt: "Hello".to_string(),
            stream: false,
        };
        let json = serde_json::to_string(&req).unwrap();
        assert!(json.contains("qwen2.5:3b"));
        assert!(json.contains("Hello"));
    }

    #[test]
    fn test_response_deserialization() {
        let json = r#"{"response":"Hi there","model":"qwen2.5:3b","total_duration":1000,"load_duration":500,"prompt_eval_count":10}"#;
        let resp: OllamaResponse = serde_json::from_str(json).unwrap();
        assert_eq!(resp.response, "Hi there");
        assert_eq!(resp.model, "qwen2.5:3b");
        assert_eq!(resp.prompt_eval_count, 10);
    }

    #[test]
    fn test_ffi_null_safety() {
        let result = ollama_chat(std::ptr::null(), std::ptr::null());
        assert!(result.is_null());
    }
}
