/// Parse Python function signatures and extract dependencies
pub fn extract_function_signature(source: &str, fn_name: &str) -> Option<String> {
    let lines: Vec<&str> = source.lines().collect();
    
    for (i, line) in lines.iter().enumerate() {
        if line.contains(&format!("def {}", fn_name)) {
            let mut signature = String::new();
            let mut paren_count = 0;
            let mut in_signature = false;
            
            for j in i..lines.len() {
                let line_text = lines[j];
                
                for ch in line_text.chars() {
                    if ch == '(' {
                        in_signature = true;
                        paren_count += 1;
                    } else if ch == ')' {
                        paren_count -= 1;
                        if paren_count == 0 && in_signature {
                            signature.push(ch);
                            return Some(signature);
                        }
                    }
                    
                    if in_signature {
                        signature.push(ch);
                    }
                }
                
                if !in_signature && line_text.contains(&format!("def {}", fn_name)) {
                    in_signature = true;
                }
            }
        }
    }
    None
}

/// Extract function and its dependencies (smart AST analysis)
pub fn extract_function_context(source: &str, fn_name: &str) -> FunctionContext {
    let signature = extract_function_signature(source, fn_name);
    let dependencies = extract_dependencies(source, fn_name);
    let estimated_complexity = estimate_complexity(&dependencies);
    
    FunctionContext {
        name: fn_name.to_string(),
        signature,
        dependencies,
        estimated_complexity,
        estimated_tokens: calculate_tokens(source, fn_name),
    }
}

/// Extract function dependencies
fn extract_dependencies(source: &str, fn_name: &str) -> Vec<String> {
    let mut deps = Vec::new();
    let lines: Vec<&str> = source.lines().collect();
    let mut in_function = false;
    
    for line in lines {
        if line.contains(&format!("def {}", fn_name)) {
            in_function = true;
        } else if in_function && line.starts_with("def ") {
            break;
        }
        
        if in_function && (line.contains("import ") || line.contains("from ")) {
            deps.push(line.trim().to_string());
        }
    }
    
    deps
}

/// Estimate complexity from dependency count
fn estimate_complexity(deps: &[String]) -> Complexity {
    match deps.len() {
        0..=2 => Complexity::Simple,
        3..=10 => Complexity::Moderate,
        _ => Complexity::Complex,
    }
}

/// Estimate token count for the function
fn calculate_tokens(source: &str, fn_name: &str) -> usize {
    source
        .lines()
        .filter(|line| {
            line.contains(&format!("def {}", fn_name))
                || line.starts_with("    ")
                || line.starts_with("\t")
        })
        .map(|line| (line.len() / 4) + 1) // Rough token estimation
        .sum()
}

#[derive(Debug, Clone, PartialEq)]
pub enum Complexity {
    Simple,
    Moderate,
    Complex,
}

#[derive(Debug, Clone)]
pub struct FunctionContext {
    pub name: String,
    pub signature: Option<String>,
    pub dependencies: Vec<String>,
    pub estimated_complexity: Complexity,
    pub estimated_tokens: usize,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_function_signature() {
        let source = "def hello(name: str) -> str:\n    return f'Hello {name}'";
        let result = extract_function_signature(source, "hello");
        assert!(result.is_some());
        let sig = result.unwrap();
        // Signature contains the parameters
        assert!(sig.contains("name"));
    }

    #[test]
    fn test_extract_context() {
        let source = r#"
import json
def process_data(data: dict):
    return json.dumps(data)
"#;
        let ctx = extract_function_context(source, "process_data");
        assert_eq!(ctx.name, "process_data");
        assert!(ctx.signature.is_some());
    }

    #[test]
    fn test_complexity_estimation() {
        let deps = vec!["import json".to_string()];
        let complexity = estimate_complexity(&deps);
        assert_eq!(complexity, Complexity::Simple);
    }
}
