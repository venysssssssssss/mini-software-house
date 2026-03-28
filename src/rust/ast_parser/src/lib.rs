use serde::{Deserialize, Serialize};
use std::ffi::{CStr, CString};
use std::os::raw::c_char;

/// Result of summarizing a Python source file via tree-sitter AST.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PythonSummary {
    pub functions: Vec<FunctionSig>,
    pub classes: Vec<ClassSig>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FunctionSig {
    pub name: String,
    pub params: Vec<String>,
    pub return_type: Option<String>,
    pub indent: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ClassSig {
    pub name: String,
    pub bases: Vec<String>,
    pub methods: Vec<FunctionSig>,
    pub nested_classes: Vec<ClassSig>,
    pub indent: usize,
}

// ---------------------------------------------------------------------------
// Tree-sitter based summarizer
// ---------------------------------------------------------------------------

/// Summarize Python source code into function/class signatures (like Python's ast module).
pub fn summarize_python(source: &str) -> PythonSummary {
    let mut parser = tree_sitter::Parser::new();
    let language = tree_sitter_python::LANGUAGE;
    parser
        .set_language(&language.into())
        .expect("Error loading Python grammar");

    let tree = match parser.parse(source, None) {
        Some(t) => t,
        None => return PythonSummary { functions: vec![], classes: vec![] },
    };

    let root = tree.root_node();
    let src_bytes = source.as_bytes();

    let mut functions = Vec::new();
    let mut classes = Vec::new();

    let mut cursor = root.walk();
    for child in root.children(&mut cursor) {
        match child.kind() {
            "function_definition" => {
                if let Some(f) = extract_function(&child, src_bytes, 0) {
                    functions.push(f);
                }
            }
            "decorated_definition" => {
                // Look for the function/class inside the decorator
                let mut inner_cursor = child.walk();
                for inner in child.children(&mut inner_cursor) {
                    if inner.kind() == "function_definition" {
                        if let Some(f) = extract_function(&inner, src_bytes, 0) {
                            functions.push(f);
                        }
                    } else if inner.kind() == "class_definition" {
                        if let Some(c) = extract_class(&inner, src_bytes, 0) {
                            classes.push(c);
                        }
                    }
                }
            }
            "class_definition" => {
                if let Some(c) = extract_class(&child, src_bytes, 0) {
                    classes.push(c);
                }
            }
            _ => {}
        }
    }

    PythonSummary { functions, classes }
}

fn extract_function(
    node: &tree_sitter::Node,
    src: &[u8],
    indent: usize,
) -> Option<FunctionSig> {
    let name_node = node.child_by_field_name("name")?;
    let name = node_text(name_node, src).to_string();

    let params_node = node.child_by_field_name("parameters")?;
    let params = extract_params(&params_node, src);

    let return_type = node
        .child_by_field_name("return_type")
        .map(|n| node_text(n, src).to_string());

    Some(FunctionSig {
        name,
        params,
        return_type,
        indent,
    })
}

fn extract_params(node: &tree_sitter::Node, src: &[u8]) -> Vec<String> {
    let mut params = Vec::new();
    let mut cursor = node.walk();
    for child in node.children(&mut cursor) {
        match child.kind() {
            "identifier" => {
                let name = node_text(child, src);
                if name != "self" {
                    params.push(name.to_string());
                }
            }
            "typed_parameter" | "default_parameter" | "typed_default_parameter" => {
                // Get the parameter name (first identifier child)
                if let Some(id) = child.child_by_field_name("name") {
                    let name = node_text(id, src);
                    if name != "self" {
                        params.push(name.to_string());
                    }
                } else {
                    let mut inner = child.walk();
                    for c in child.children(&mut inner) {
                        if c.kind() == "identifier" {
                            let name = node_text(c, src);
                            if name != "self" {
                                params.push(name.to_string());
                                break;
                            }
                        }
                    }
                }
            }
            "list_splat_pattern" | "dictionary_splat_pattern" => {
                // *args, **kwargs
                let text = node_text(child, src);
                params.push(text.to_string());
            }
            _ => {}
        }
    }
    params
}

fn extract_class(node: &tree_sitter::Node, src: &[u8], indent: usize) -> Option<ClassSig> {
    let name_node = node.child_by_field_name("name")?;
    let name = node_text(name_node, src).to_string();

    // Extract base classes
    let bases = if let Some(args) = node.child_by_field_name("superclasses") {
        let mut bases = Vec::new();
        let mut cursor = args.walk();
        for child in args.children(&mut cursor) {
            if child.kind() == "identifier" || child.kind() == "attribute" {
                bases.push(node_text(child, src).to_string());
            }
        }
        bases
    } else {
        vec![]
    };

    // Extract methods and nested classes from class body
    let mut methods = Vec::new();
    let mut nested_classes = Vec::new();
    if let Some(body) = node.child_by_field_name("body") {
        let mut cursor = body.walk();
        for child in body.children(&mut cursor) {
            match child.kind() {
                "function_definition" => {
                    if let Some(f) = extract_function(&child, src, indent + 1) {
                        methods.push(f);
                    }
                }
                "decorated_definition" => {
                    let mut inner_cursor = child.walk();
                    for inner in child.children(&mut inner_cursor) {
                        if inner.kind() == "function_definition" {
                            if let Some(f) = extract_function(&inner, src, indent + 1) {
                                methods.push(f);
                            }
                        } else if inner.kind() == "class_definition" {
                            if let Some(c) = extract_class(&inner, src, indent + 1) {
                                nested_classes.push(c);
                            }
                        }
                    }
                }
                "class_definition" => {
                    if let Some(c) = extract_class(&child, src, indent + 1) {
                        nested_classes.push(c);
                    }
                }
                _ => {}
            }
        }
    }

    Some(ClassSig { name, bases, methods, nested_classes, indent })
}

fn node_text<'a>(node: tree_sitter::Node<'a>, src: &'a [u8]) -> &'a str {
    node.utf8_text(src).unwrap_or("")
}

/// Format a PythonSummary into the same string format as Python's CodeSummarizer.
pub fn format_summary(summary: &PythonSummary) -> String {
    let mut lines = Vec::new();

    for f in &summary.functions {
        let ret = f
            .return_type
            .as_ref()
            .map(|r| format!(" -> {r}"))
            .unwrap_or_default();
        lines.push(format!("def {}({}){}: ...", f.name, f.params.join(", "), ret));
    }

    for c in &summary.classes {
        format_class(c, &mut lines);
    }

    lines.join("\n")
}

fn format_class(class: &ClassSig, lines: &mut Vec<String>) {
    let indent = "    ".repeat(class.indent);
    let base_str = if class.bases.is_empty() {
        String::new()
    } else {
        format!("({})", class.bases.join(", "))
    };
    lines.push(format!("{indent}class {}{}:", class.name, base_str));

    for m in &class.methods {
        let method_indent = "    ".repeat(m.indent);
        let ret = m
            .return_type
            .as_ref()
            .map(|r| format!(" -> {r}"))
            .unwrap_or_default();
        lines.push(format!(
            "{method_indent}def {}({}){}: ...",
            m.name,
            m.params.join(", "),
            ret
        ));
    }

    for nested in &class.nested_classes {
        format_class(nested, lines);
    }
}

// ---------------------------------------------------------------------------
// C FFI for Python integration
// ---------------------------------------------------------------------------

/// Summarize Python source and return a formatted string (C FFI).
///
/// # Safety
/// `source_ptr` must be a valid null-terminated C string.
/// Caller must free the returned pointer with `ast_free_string`.
#[no_mangle]
pub unsafe extern "C" fn ast_summarize_python(source_ptr: *const c_char) -> *mut c_char {
    if source_ptr.is_null() {
        return std::ptr::null_mut();
    }

    let c_str = unsafe { CStr::from_ptr(source_ptr) };
    let source = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let summary = summarize_python(source);
    let formatted = format_summary(&summary);

    match CString::new(formatted) {
        Ok(cs) => cs.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Summarize Python source and return JSON (C FFI).
///
/// # Safety
/// `source_ptr` must be a valid null-terminated C string.
/// Caller must free the returned pointer with `ast_free_string`.
#[no_mangle]
pub unsafe extern "C" fn ast_summarize_python_json(source_ptr: *const c_char) -> *mut c_char {
    if source_ptr.is_null() {
        return std::ptr::null_mut();
    }

    let c_str = unsafe { CStr::from_ptr(source_ptr) };
    let source = match c_str.to_str() {
        Ok(s) => s,
        Err(_) => return std::ptr::null_mut(),
    };

    let summary = summarize_python(source);
    let json_str = match serde_json::to_string(&summary) {
        Ok(j) => j,
        Err(_) => return std::ptr::null_mut(),
    };

    match CString::new(json_str) {
        Ok(cs) => cs.into_raw(),
        Err(_) => std::ptr::null_mut(),
    }
}

/// Free a string returned by ast_summarize_python or ast_summarize_python_json.
///
/// # Safety
/// `ptr` must have been allocated by CString::into_raw from this library.
#[no_mangle]
pub unsafe extern "C" fn ast_free_string(ptr: *mut c_char) {
    if !ptr.is_null() {
        drop(unsafe { CString::from_raw(ptr) });
    }
}

// ---------------------------------------------------------------------------
// Legacy API (kept for backward compatibility)
// ---------------------------------------------------------------------------

/// Parse Python function signatures and extract dependencies
pub fn extract_function_signature(source: &str, fn_name: &str) -> Option<String> {
    let summary = summarize_python(source);

    // Search top-level functions
    for f in &summary.functions {
        if f.name == fn_name {
            let ret = f
                .return_type
                .as_ref()
                .map(|r| format!(" -> {r}"))
                .unwrap_or_default();
            return Some(format!("({}){}", f.params.join(", "), ret));
        }
    }

    // Search class methods
    for c in &summary.classes {
        for m in &c.methods {
            if m.name == fn_name {
                let ret = m
                    .return_type
                    .as_ref()
                    .map(|r| format!(" -> {r}"))
                    .unwrap_or_default();
                return Some(format!("({}){}", m.params.join(", "), ret));
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

fn estimate_complexity(deps: &[String]) -> Complexity {
    match deps.len() {
        0..=2 => Complexity::Simple,
        3..=10 => Complexity::Moderate,
        _ => Complexity::Complex,
    }
}

fn calculate_tokens(source: &str, fn_name: &str) -> usize {
    source
        .lines()
        .filter(|line| {
            line.contains(&format!("def {}", fn_name))
                || line.starts_with("    ")
                || line.starts_with("\t")
        })
        .map(|line| (line.len() / 4) + 1)
        .sum()
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Complexity {
    Simple,
    Moderate,
    Complex,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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
    fn test_summarize_simple_function() {
        let src = "def hello(name: str) -> str:\n    return f'Hello {name}'";
        let summary = summarize_python(src);
        assert_eq!(summary.functions.len(), 1);
        assert_eq!(summary.functions[0].name, "hello");
        assert_eq!(summary.functions[0].params, vec!["name"]);
        assert_eq!(summary.functions[0].return_type, Some("str".to_string()));
    }

    #[test]
    fn test_summarize_class_with_methods() {
        let src = r#"
class MyClass(Base):
    def __init__(self, x: int):
        self.x = x

    def get_value(self) -> int:
        return self.x
"#;
        let summary = summarize_python(src);
        assert_eq!(summary.classes.len(), 1);
        assert_eq!(summary.classes[0].name, "MyClass");
        assert_eq!(summary.classes[0].bases, vec!["Base"]);
        assert_eq!(summary.classes[0].methods.len(), 2);
        assert_eq!(summary.classes[0].methods[0].name, "__init__");
        assert_eq!(summary.classes[0].methods[0].params, vec!["x"]);
        assert_eq!(summary.classes[0].methods[1].name, "get_value");
    }

    #[test]
    fn test_format_summary_output() {
        let src = "def add(a, b) -> int:\n    return a + b\n\ndef sub(a, b):\n    return a - b";
        let summary = summarize_python(src);
        let formatted = format_summary(&summary);
        assert!(formatted.contains("def add(a, b) -> int: ..."));
        assert!(formatted.contains("def sub(a, b): ..."));
    }

    #[test]
    fn test_empty_source() {
        let summary = summarize_python("");
        assert!(summary.functions.is_empty());
        assert!(summary.classes.is_empty());
    }

    #[test]
    fn test_syntax_error_doesnt_crash() {
        let src = "def broken(:\n    pass";
        // Should not panic — tree-sitter is error-tolerant
        let _summary = summarize_python(src);
    }

    #[test]
    fn test_extract_function_signature_legacy() {
        let src = "def hello(name: str) -> str:\n    return f'Hello {name}'";
        let result = extract_function_signature(src, "hello");
        assert!(result.is_some());
        let sig = result.unwrap();
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

    #[test]
    fn test_class_no_bases() {
        let src = "class Foo:\n    def bar(self):\n        pass";
        let summary = summarize_python(src);
        assert_eq!(summary.classes.len(), 1);
        assert!(summary.classes[0].bases.is_empty());
    }
}
