use std::path::Path;

pub struct FileWatcherConfig {
    pub watch_paths: Vec<String>,
    pub extensions: Vec<String>,
    pub debounce_ms: u64,
}

impl Default for FileWatcherConfig {
    fn default() -> Self {
        FileWatcherConfig {
            watch_paths: vec![".".to_string()],
            extensions: vec!["py".to_string(), "rs".to_string(), "js".to_string()],
            debounce_ms: 500,
        }
    }
}

/// Check if file matches watched extensions
pub fn check_file_extension(path: &str, extensions: &[String]) -> bool {
    let p = Path::new(path);
    p.extension()
        .map_or(false, |ext| {
            extensions.iter().any(|e| ext.to_str().unwrap_or("") == e)
        })
}

/// Extract file information for monitoring
pub fn extract_file_info(path: &str) -> FileInfo {
    let p = Path::new(path);
    FileInfo {
        path: path.to_string(),
        name: p.file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .to_string(),
        extension: p.extension()
            .and_then(|n| n.to_str())
            .unwrap_or("")
            .to_string(),
        is_python: path.ends_with(".py"),
        is_rust: path.ends_with(".rs"),
    }
}

#[derive(Debug, Clone)]
pub struct FileInfo {
    pub path: String,
    pub name: String,
    pub extension: String,
    pub is_python: bool,
    pub is_rust: bool,
}

/// Smart linting actions based on file type
pub fn get_lint_command(path: &str) -> Option<String> {
    let info = extract_file_info(path);
    
    if info.is_python {
        Some(format!("ruff format {}", path))
    } else if info.is_rust {
        Some(format!("rustfmt {}", path))
    } else {
        None
    }
}

fn main() {
    println!("🔍 File Watcher Module - Async File Monitoring");
    
    let config = FileWatcherConfig::default();
    println!("Watching extensions: {:?}", config.extensions);
    println!("Debounce interval: {}ms", config.debounce_ms);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_check_file_extension() {
        let exts = vec!["py".to_string(), "rs".to_string()];
        assert!(check_file_extension("script.py", &exts));
        assert!(check_file_extension("main.rs", &exts));
        assert!(!check_file_extension("style.css", &exts));
    }

    #[test]
    fn test_extract_file_info() {
        let info = extract_file_info("/path/to/script.py");
        assert_eq!(info.name, "script.py");
        assert_eq!(info.extension, "py");
        assert!(info.is_python);
    }

    #[test]
    fn test_lint_command() {
        let cmd = get_lint_command("test.py");
        assert!(cmd.is_some());
        
        let cmd = get_lint_command("test.rs");
        assert!(cmd.is_some());
    }
}
