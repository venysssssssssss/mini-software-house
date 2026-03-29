use serde_json::Value;
use std::slice;

/// Fast JSON parsing wrapper with minimal overhead
pub fn parse_fast(json_str: &str) -> Result<Value, String> {
    serde_json::from_str(json_str)
        .map_err(|e| format!("Parse error: {}", e))
}

/// Serialize to JSON with minimal allocations
pub fn to_json_fast(value: &Value) -> Result<String, String> {
    serde_json::to_string(value)
        .map_err(|e| format!("Serialize error: {}", e))
}

/// C FFI interface for JSON parsing
#[no_mangle]
pub extern "C" fn parse_json_c_ffi(json_str: *const u8, len: usize) -> *mut u8 {
    if json_str.is_null() || len == 0 {
        return std::ptr::null_mut();
    }

    unsafe {
        let slice = slice::from_raw_parts(json_str, len);
        let json_text = match std::str::from_utf8(slice) {
            Ok(s) => s,
            Err(_) => return std::ptr::null_mut(),
        };

        match serde_json::from_str::<Value>(json_text) {
            Ok(val) => {
                // Return serialized result as malloc'd string
                if let Ok(result) = serde_json::to_string(&val) {
                    let result_bytes = result.into_bytes();
                    let ptr = libc::malloc(result_bytes.len()) as *mut u8;
                    if !ptr.is_null() {
                        std::ptr::copy_nonoverlapping(
                            result_bytes.as_ptr(),
                            ptr,
                            result_bytes.len(),
                        );
                    }
                    ptr
                } else {
                    std::ptr::null_mut()
                }
            }
            Err(_) => std::ptr::null_mut(),
        }
    }
}

/// Free C-allocated memory
#[no_mangle]
pub extern "C" fn free_json_string(ptr: *mut u8) {
    if !ptr.is_null() {
        unsafe {
            libc::free(ptr as *mut libc::c_void);
        }
    }
}

/// Benchmark JSON parsing
pub fn benchmark_parse_iterations(iterations: usize) -> f64 {
    let json_data = r#"{"status":"completed","output":{"files":["app.py"],"time":3.2},"metadata":{"version":"1.0","author":"rust"}}"#;
    
    let start = std::time::Instant::now();
    for _ in 0..iterations {
        let _ = parse_fast(json_data);
    }
    start.elapsed().as_secs_f64()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple() {
        let json = r#"{"key":"value"}"#;
        let result = parse_fast(json).unwrap();
        assert_eq!(result["key"], "value");
    }

    #[test]
    fn test_parse_complex() {
        let json = r#"{"nested":{"array":[1,2,3]},"bool":true}"#;
        let result = parse_fast(json).unwrap();
        assert_eq!(result["nested"]["array"][0], 1);
    }

    #[test]
    fn test_serialization() {
        let val = serde_json::json!({"test": "data"});
        let result = to_json_fast(&val);
        assert!(result.is_ok());
    }

    #[test]
    fn test_roundtrip() {
        let input = r#"{"a":1,"b":"hello","c":[true,false,null]}"#;
        let parsed = parse_fast(input).unwrap();
        let serialized = to_json_fast(&parsed).unwrap();
        let reparsed = parse_fast(&serialized).unwrap();
        assert_eq!(parsed, reparsed);
    }

    #[test]
    fn test_malformed_input() {
        let result = parse_fast("{invalid json}");
        assert!(result.is_err());
    }

    #[test]
    fn test_empty_input() {
        let result = parse_fast("");
        assert!(result.is_err());
    }

    #[test]
    fn test_nested_objects() {
        let json = r#"{"a":{"b":{"c":{"d":"deep"}}}}"#;
        let result = parse_fast(json).unwrap();
        assert_eq!(result["a"]["b"]["c"]["d"], "deep");
    }

    #[test]
    fn test_c_ffi_null_ptr() {
        let result = parse_json_c_ffi(std::ptr::null(), 0);
        assert!(result.is_null());
    }

    #[test]
    fn test_benchmark_runs() {
        let elapsed = benchmark_parse_iterations(100);
        assert!(elapsed > 0.0);
    }
}
