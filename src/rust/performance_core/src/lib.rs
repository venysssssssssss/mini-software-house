use serde_json::{json, Value};
use std::time::Instant;

/// Async pipeline executor with parallelization
pub async fn execute_pipeline_async(task: String) -> Result<Value, Box<dyn std::error::Error>> {
    let start = Instant::now();
    
    // Execute planner and executor in parallel
    let planner = plan_task_async(&task);
    let executor = execute_task_async(&task);
    
    let (plan_result, exec_result) = tokio::join!(planner, executor);
    
    let plan = plan_result?;
    let exec = exec_result?;
    
    let elapsed = start.elapsed().as_secs_f64();
    
    Ok(json!({
        "status": "success",
        "plan": plan,
        "execution": exec,
        "parallelized": true,
        "elapsed_seconds": elapsed,
        "throughput": format!("2x parallel tasks")
    }))
}

async fn plan_task_async(_task: &str) -> Result<Value, Box<dyn std::error::Error>> {
    // Simulate async planning (would call Ollama)
    tokio::time::sleep(tokio::time::Duration::from_millis(50)).await;
    Ok(json!({
        "architecture": "microservices",
        "files": ["main.py", "config.py", "utils.py"],
        "dependencies": ["fastapi", "pydantic"]
    }))
}

async fn execute_task_async(_task: &str) -> Result<Value, Box<dyn std::error::Error>> {
    // Simulate async execution (would run code generation)
    tokio::time::sleep(tokio::time::Duration::from_millis(30)).await;
    Ok(json!({
        "generated_files": 3,
        "lines_of_code": 450,
        "status": "generated"
    }))
}

/// Fast task parsing with minimal allocation
pub fn parse_task_efficient(task: &str) -> Value {
    json!({
        "task": task,
        "type": classify_task(task),
        "complexity": estimate_complexity(task)
    })
}

fn classify_task(task: &str) -> &'static str {
    if task.contains("API") || task.contains("api") { "backend" }
    else if task.contains("HTML") || task.contains("CSS") { "frontend" }
    else if task.contains("test") { "testing" }
    else { "general" }
}

fn estimate_complexity(task: &str) -> &'static str {
    let len = task.len();
    match len {
        0..=50 => "simple",
        51..=200 => "medium",
        _ => "complex"
    }
}

#[tokio::test]
async fn test_pipeline_async() {
    let result = execute_pipeline_async("test task".to_string()).await;
    assert!(result.is_ok());
    let val = result.unwrap();
    assert_eq!(val["status"], "success");
    assert_eq!(val["parallelized"], true);
}

#[test]
fn test_task_parsing() {
    let result = parse_task_efficient("Create a REST API");
    assert_eq!(result["type"], "backend");
}
