use regex::Regex;

/// Configuration for log filtering
pub struct LogFilterConfig {
    pub error_patterns: Vec<String>,
    pub buffer_size: usize,
    pub max_lines: usize,
}

impl Default for LogFilterConfig {
    fn default() -> Self {
        LogFilterConfig {
            error_patterns: vec![
                "ERROR".to_string(),
                "FAILED".to_string(),
                "Traceback".to_string(),
                "Exception".to_string(),
            ],
            buffer_size: 1000,
            max_lines: 500,
        }
    }
}

/// Filter logs based on patterns efficiently
pub fn filter_logs(logs: &[String], config: &LogFilterConfig) -> Result<Vec<String>, String> {
    let pattern_str = config.error_patterns.join("|");
    let regex = Regex::new(&pattern_str)
        .map_err(|e| format!("Invalid pattern: {}", e))?;

    let results: Vec<String> = logs
        .iter()
        .filter(|log| regex.is_match(log))
        .take(config.max_lines)
        .cloned()
        .collect();

    Ok(results)
}

/// Extract key information from error logs with metrics
pub fn extract_error_summary(logs: &[String]) -> ErrorSummary {
    let mut error_count = 0;
    let mut warning_count = 0;
    let mut critical_count = 0;

    for log in logs {
        if log.contains("ERROR") || log.contains("Traceback") {
            error_count += 1;
        } else if log.contains("WARNING") {
            warning_count += 1;
        } else if log.contains("CRITICAL") || log.contains("FATAL") {
            critical_count += 1;
        }
    }

    ErrorSummary {
        total_errors: error_count + warning_count + critical_count,
        error_count,
        warning_count,
        critical_count,
        sample_errors: logs.iter().take(5).cloned().collect(),
    }
}

/// Summary of extracted errors
#[derive(Debug, Clone)]
pub struct ErrorSummary {
    pub total_errors: usize,
    pub error_count: usize,
    pub warning_count: usize,
    pub critical_count: usize,
    pub sample_errors: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_filter_logs() {
        let logs = vec![
            "INFO: Starting".to_string(),
            "ERROR: Connection failed".to_string(),
            "INFO: Retrying".to_string(),
            "FAILED: Test suite".to_string(),
        ];
        let config = LogFilterConfig {
            error_patterns: vec!["ERROR".to_string(), "FAILED".to_string()],
            buffer_size: 100,
            max_lines: 100,
        };
        let results = filter_logs(&logs, &config).unwrap();
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_error_summary() {
        let logs = vec![
            "ERROR: Test1".to_string(),
            "WARNING: Test2".to_string(),
            "ERROR: Test3".to_string(),
        ];
        let summary = extract_error_summary(&logs);
        assert_eq!(summary.error_count, 2);
        assert_eq!(summary.warning_count, 1);
    }
}
