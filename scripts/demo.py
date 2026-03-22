#!/usr/bin/env python3
"""
End-to-end demo of the Smart Naming Engine and Dynamic HTML Generator
Shows how the system generates intelligent project names and beautiful HTML pages
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.naming_engine import NamingEngine
from src.html_generator import HTMLGenerator, save_html

def demo_naming_engine():
    """Demonstrate the naming engine with various project types"""
    print("=" * 70)
    print("🎯 SMART NAMING ENGINE DEMO")
    print("=" * 70)
    
    engine = NamingEngine()
    
    # Define test projects with different characteristics
    test_projects = [
        {
            "name": "REST API Project",
            "files": ["main.py", "models.py", "routes.py", "database.py", "requirements.txt"],
            "dependencies": ["fastapi", "sqlalchemy", "pydantic", "postgresql", "uvicorn"],
            "description": "Create a REST API with database and async support"
        },
        {
            "name": "Vue.js Dashboard",
            "files": ["App.vue", "index.html", "main.js", "components/Chart.vue", "package.json"],
            "dependencies": ["vue", "axios", "chart.js", "tailwindcss"],
            "description": "Interactive dashboard with real-time data visualization"
        },
        {
            "name": "ML Classification Model",
            "files": ["train.py", "model.py", "preprocess.py", "evaluate.py"],
            "dependencies": ["torch", "tensorflow", "sklearn", "numpy", "pandas"],
            "description": "Deep learning model for image classification"
        },
        {
            "name": "Data Pipeline",
            "files": ["etl.py", "transform.py", "load.py", "config.yaml"],
            "dependencies": ["airflow", "dbt", "pyspark", "delta"],
            "description": "ETL pipeline for data warehouse"
        },
        {
            "name": "Microservice",
            "files": ["main.rs", "Cargo.toml", "lib.rs"],
            "dependencies": ["tokio", "actix", "serde_json"],
            "description": "High-performance microservice in Rust"
        },
    ]
    
    results = []
    for project in test_projects:
        print(f"\n📦 Analyzing: {project['name']}")
        print(f"   Files: {len(project['files'])}, Dependencies: {len(project['dependencies'])}")
        
        # Analyze project
        analysis = engine.analyze_project(
            files=project['files'],
            dependencies=project['dependencies'],
            task_description=project['description']
        )
        
        # Generate name and description
        name, description = engine.generate_name(analysis)
        
        print(f"   ✨ Generated Name: {name}")
        print(f"   📝 Type: {analysis['type']}")
        print(f"   🎯 Complexity: {analysis['complexity']}")
        print(f"   🛠️  Tech: {', '.join(analysis['tech_stack'])}")
        print(f"   ⚡ Features: {', '.join(analysis['key_features'][:3])}")
        print(f"   📄 Description: {description}")
        
        results.append((name, description, analysis, project))
    
    return results

def demo_html_generator(results):
    """Demonstrate the HTML generator"""
    print("\n" + "=" * 70)
    print("🎨 DYNAMIC HTML GENERATOR DEMO")
    print("=" * 70)
    
    generator = HTMLGenerator()
    
    # Generate individual project pages
    output_dir = "/home/kali/BIG/mini-software-house/workspace"
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n📄 Generating individual project pages:")
    for name, description, analysis, project in results:
        clean_name = name.replace(" ", "_").replace("(", "").replace(")", "").lower()
        filepath = os.path.join(output_dir, f"{clean_name}.html")
        
        html = generator.generate_project_page(
            project_name=name,
            description=description,
            analysis=analysis,
            file_count=len(project['files']),
            dependency_count=len(project['dependencies'])
        )
        
        if save_html(html, filepath):
            print(f"   ✓ {name} → {os.path.basename(filepath)}")
    
    # Generate landing page with all projects
    print("\n🌐 Generating portfolio landing page:")
    portfolio_data = [(name, desc, analysis) for name, desc, analysis, _ in results]
    landing_html = generator.generate_landing_page(portfolio_data)
    
    landing_path = os.path.join(output_dir, "portfolio.html")
    if save_html(landing_html, landing_path):
        print(f"   ✓ Portfolio page → {os.path.basename(landing_path)}")

def print_summary(results):
    """Print summary statistics"""
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    
    print(f"\n✅ Successfully generated {len(results)} projects:")
    for name, _, analysis, project in results:
        print(f"   • {name}")
        print(f"     Type: {analysis['type']}, Complexity: {analysis['complexity']}")
        print(f"     Files: {len(project['files'])}, Dependencies: {len(project['dependencies'])}")
    
    # Type distribution
    types = {}
    for _, _, analysis, _ in results:
        proj_type = analysis['type']
        types[proj_type] = types.get(proj_type, 0) + 1
    
    print(f"\n📈 Project Type Distribution:")
    for proj_type, count in sorted(types.items()):
        print(f"   • {proj_type}: {count}")
    
    print(f"\n✨ Features identified across all projects:")
    all_features = set()
    for _, _, analysis, _ in results:
        all_features.update(analysis['key_features'])
    
    for feature in sorted(all_features):
        print(f"   • {feature}")

def main():
    """Run the complete demo"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "MINI SOFTWARE HOUSE - PROJECT GENERATION DEMO" + " " * 14 + "║")
    print("║" + " " * 22 + "Smart Naming + Dynamic HTML/CSS" + " " * 16 + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Run naming engine demo
    naming_results = demo_naming_engine()
    
    # Run HTML generator demo
    demo_html_generator(naming_results)
    
    # Print summary
    print_summary(naming_results)
    
    print("\n" + "=" * 70)
    print("🎉 Demo complete! Check workspace/ for generated HTML files")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    main()
