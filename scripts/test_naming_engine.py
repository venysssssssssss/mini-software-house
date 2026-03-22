"""
Interactive demo of the kebab-case project naming engine.

The NamingEngine now generates intelligent project names following the pattern:
    action-object-purpose (kebab-case)

Examples:
    - "Build a REST API for user management" → "build-user-api"
    - "Create a real-time chat application" → "create-rt-app"
    - "Develop a machine learning model for image recognition" → "dev-image-recognition-learn"

Usage in agents:
    - PlannerAgent automatically generates project_name in the JSON response
    - Fallback to NamingEngine if model doesn't provide one
    - ExecutorAgent uses the project_name to organize created files
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.naming_engine import NamingEngine

def demo_naming_engine():
    """Demonstrate various project naming scenarios"""
    engine = NamingEngine()
    
    print("=" * 70)
    print("🎯 KEBAB-CASE PROJECT NAMING ENGINE DEMO")
    print("=" * 70)
    
    test_cases = [
        {
            "description": "REST API Backend",
            "task": "Build a REST API for user authentication and management",
            "deps": ["fastapi", "sqlalchemy", "jwt"],
        },
        {
            "description": "Real-time Chat App",
            "task": "Create a real-time chat application with WebSocket and message history",
            "deps": ["fastapi", "websockets", "redis"],
        },
        {
            "description": "ML Image Recognition",
            "task": "Develop a machine learning model for image classification and object detection",
            "deps": ["torch", "torchvision", "opencv"],
        },
        {
            "description": "Data ETL Pipeline",
            "task": "Build an ETL pipeline for processing and streaming data with real-time analytics",
            "deps": ["pyspark", "kafka", "pandas"],
        },
        {
            "description": "Monitoring Dashboard",
            "task": "Create a monitoring dashboard to track system metrics and alerts",
            "deps": ["streamlit", "prometheus", "grafana"],
        },
        {
            "description": "Notification Service",
            "task": "Develop a notification microservice with email and SMS support",
            "deps": ["fastapi", "celery", "redis"],
        },
        {
            "description": "Document Search Engine",
            "task": "Build a search engine with full-text search and relevance ranking",
            "deps": ["elasticsearch", "fastapi", "numpy"],
        },
        {
            "description": "Video Processing Tool",
            "task": "Create a tool to process and convert video files with streaming output",
            "deps": ["opencv", "ffmpeg", "asyncio"],
        },
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📌 Test Case {i}: {test['description']}")
        print(f"   Task: {test['task']}")
        
        name = engine.generate_project_name_from_task(
            task_description=test['task'],
            dependencies=test['deps']
        )
        
        print(f"   ✓ Generated Name: {name}")
        print(f"     Dependencies: {', '.join(test['deps'][:3])}")
    
    print("\n" + "=" * 70)
    print("✅ Demo complete!")
    print("\nUse in your code:")
    print("  from src.naming_engine import NamingEngine")
    print("  engine = NamingEngine()")
    print("  project_name = engine.generate_project_name_from_task(")
    print('      task_description="Build a REST API..."')
    print("  )")
    print("=" * 70)

if __name__ == "__main__":
    demo_naming_engine()
