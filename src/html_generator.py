"""
Dynamic HTML/CSS Generator
Generates customized HTML/CSS pages for projects based on their type, complexity, 
and tech stack. Creates visually distinct project showcase pages.
"""

import json
from typing import Dict, List, Tuple
from enum import Enum

class ColorScheme(Enum):
    """Color schemes for different project types"""
    # Backend projects - Purple/Blue tones
    BACKEND = {
        "primary": "#6366f1",
        "secondary": "#4f46e5",
        "accent": "#ec4899",
        "background": "#1e293b",
        "surface": "#0f172a"
    }
    # Frontend projects - Blue/Cyan tones
    FRONTEND = {
        "primary": "#06b6d4",
        "secondary": "#0891b2",
        "accent": "#fbbf24",
        "background": "#0c2340",
        "surface": "#051e2d"
    }
    # Data/Pipeline projects - Green tones
    DATA = {
        "primary": "#10b981",
        "secondary": "#059669",
        "accent": "#f59e0b",
        "background": "#064e3b",
        "surface": "#022c1d"
    }
    # ML/AI projects - Orange/Amber tones
    AI = {
        "primary": "#f59e0b",
        "secondary": "#d97706",
        "accent": "#ec4899",
        "background": "#451a03",
        "surface": "#2d1810"
    }
    # Infrastructure - Red/Rose tones
    INFRA = {
        "primary": "#ef4444",
        "secondary": "#dc2626",
        "accent": "#10b981",
        "background": "#4c0519",
        "surface": "#2d0a1a"
    }
    # Default - Indigo tones
    DEFAULT = {
        "primary": "#8b5cf6",
        "secondary": "#7c3aed",
        "accent": "#ec4899",
        "background": "#1e1b4b",
        "surface": "#15803d"
    }

class HTMLGenerator:
    """
    Generates custom HTML/CSS for project showcase pages
    """
    
    def __init__(self):
        """Initialize the generator"""
        self.templates = {}
    
    def get_color_scheme(self, project_type: str, complexity: str) -> Dict[str, str]:
        """
        Get appropriate color scheme based on project type and complexity
        
        Args:
            project_type: Type of project (backend_api, frontend_app, etc.)
            complexity: Complexity level (simple, moderate, complex)
        
        Returns:
            Color scheme dictionary
        """
        scheme_map = {
            "backend_api": ColorScheme.BACKEND,
            "frontend_app": ColorScheme.FRONTEND,
            "data_pipeline": ColorScheme.DATA,
            "ml_model": ColorScheme.AI,
            "infrastructure": ColorScheme.INFRA,
            "testing_suite": ColorScheme.BACKEND,
            "microservice": ColorScheme.BACKEND,
            "library": ColorScheme.DEFAULT,
            "fullstack": ColorScheme.DEFAULT,
        }
        
        scheme = scheme_map.get(project_type, ColorScheme.DEFAULT)
        return dict(scheme.value.items())
    
    def generate_project_page(
        self,
        project_name: str,
        description: str,
        analysis: Dict,
        file_count: int = 0,
        dependency_count: int = 0
    ) -> str:
        """
        Generate a complete project showcase HTML page
        
        Args:
            project_name: Generated project name
            description: Project description
            analysis: Project analysis data
            file_count: Number of files in project
            dependency_count: Number of dependencies
        
        Returns:
            Complete HTML page as string
        """
        colors = self.get_color_scheme(analysis["type"], analysis["complexity"])
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} - Project Showcase</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        :root {{
            --primary: {colors['primary']};
            --secondary: {colors['secondary']};
            --accent: {colors['accent']};
            --background: {colors['background']};
            --surface: {colors['surface']};
            --text-light: #f1f5f9;
            --text-muted: #cbd5e1;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, var(--background) 0%, var(--surface) 100%);
            color: var(--text-light);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 3rem;
            margin-bottom: 3rem;
            text-align: center;
        }}
        
        .badge {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin: 0.5rem;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--accent);
            color: var(--accent);
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin: 1.5rem 0;
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .project-description {{
            font-size: 1.2rem;
            color: var(--text-muted);
            margin: 1.5rem 0;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: var(--primary);
            transform: translateY(-4px);
        }}
        
        .stat-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary);
            margin-bottom: 0.5rem;
        }}
        
        .stat-label {{
            font-size: 0.9rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .tech-stack {{
            margin: 2rem 0;
        }}
        
        .tech-stack h3 {{
            color: var(--primary);
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.9rem;
        }}
        
        .tech-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 1rem;
        }}
        
        .tech-item {{
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.1));
            border: 1px solid var(--primary);
            border-radius: 6px;
            padding: 0.75rem 1.5rem;
            color: var(--text-light);
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        .features {{
            margin: 2rem 0;
        }}
        
        .features h3 {{
            color: var(--primary);
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 0.9rem;
        }}
        
        .feature-list {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
        }}
        
        .feature-item {{
            background: rgba(255, 255, 255, 0.05);
            border-left: 3px solid var(--accent);
            padding: 1.5rem;
            border-radius: 6px;
        }}
        
        .feature-item::before {{
            content: "▸ ";
            color: var(--accent);
            font-weight: bold;
        }}
        
        .feature-item strong {{
            color: var(--text-light);
        }}
        
        .complexity-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .complexity-bar {{
            display: flex;
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
            width: 100px;
        }}
        
        .complexity-fill {{
            background: linear-gradient(90deg, var(--primary), var(--accent));
            height: 100%;
            border-radius: 3px;
        }}
        
        .metrics {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 2rem;
            margin-top: 3rem;
            padding: 2rem;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        footer {{
            text-align: center;
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: var(--text-muted);
            font-size: 0.9rem;
        }}
        
        @media (max-width: 768px) {{
            h1 {{
                font-size: 1.8rem;
            }}
            
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .metrics {{
                grid-template-columns: 1fr;
            }}
            
            header {{
                padding: 2rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="badge">{analysis['type'].replace('_', ' ').title()}</div>
            <div class="badge">{analysis['complexity'].title()}</div>
            
            <h1>{project_name}</h1>
            <p class="project-description">{description}</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{file_count}</div>
                <div class="stat-label">Project Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{dependency_count}</div>
                <div class="stat-label">Dependencies</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(analysis['tech_stack'])}</div>
                <div class="stat-label">Tech Stacks</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(analysis['key_features'])}</div>
                <div class="stat-label">Key Features</div>
            </div>
        </div>
        
        <div class="metrics">
            <div class="tech-stack">
                <h3>🛠️ Technology Stack</h3>
                <div class="tech-list">
{self._generate_tech_items(analysis['tech_stack'])}
                </div>
            </div>
            
            <div class="features">
                <h3>⚡ Key Capabilities</h3>
                <div class="feature-list">
{self._generate_feature_items(analysis['key_features'])}
                </div>
            </div>
        </div>
        
        <footer>
            <p>Generated for <strong>{project_name}</strong> | Project Type: {analysis['type'].replace('_', ' ').title()} | Complexity: {analysis['complexity'].title()}</p>
        </footer>
    </div>
</body>
</html>
"""
        return html
    
    def generate_landing_page(self, projects: List[Tuple[str, str, Dict]]) -> str:
        """
        Generate a landing page showcasing multiple projects
        
        Args:
            projects: List of (name, description, analysis) tuples
        
        Returns:
            Complete HTML landing page
        """
        project_cards = ""
        for name, description, analysis in projects:
            colors = self.get_color_scheme(analysis["type"], analysis["complexity"])
            project_cards += f"""
            <div class="project-card" style="border-color: {colors['primary']};">
                <div class="project-badge">{analysis['complexity'].title()}</div>
                <h3>{name}</h3>
                <p>{description}</p>
                <div class="project-meta">
                    <span class="meta-badge">{analysis['type'].replace('_', ' ').title()}</span>
                    <span class="meta-badge">{', '.join(analysis['tech_stack'][:2])}</span>
                </div>
            </div>
"""
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mini Software House - Project Portfolio</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
            color: #f1f5f9;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            text-align: center;
            margin: 4rem 0;
        }}
        
        h1 {{
            font-size: 3rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, #6366f1 0%, #ec4899 50%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .subtitle {{
            font-size: 1.2rem;
            color: #cbd5e1;
            margin-bottom: 2rem;
        }}
        
        .projects-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 3rem 0;
        }}
        
        .project-card {{
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-left: 4px solid;
            border-radius: 12px;
            padding: 2rem;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .project-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent, currentColor, transparent);
        }}
        
        .project-card:hover {{
            background: rgba(255, 255, 255, 0.08);
            border-color: inherit;
            transform: translateY(-8px);
        }}
        
        .project-badge {{
            display: inline-block;
            padding: 0.35rem 0.75rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 1rem;
            color: #ec4899;
        }}
        
        .project-card h3 {{
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            color: #f1f5f9;
        }}
        
        .project-card p {{
            color: #cbd5e1;
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
        }}
        
        .project-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        
        .meta-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 6px;
            font-size: 0.8rem;
            color: #cbd5e1;
        }}
        
        footer {{
            text-align: center;
            margin-top: 4rem;
            padding-top: 2rem;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #64748b;
        }}
        
        @media (max-width: 768px) {{
            h1 {{
                font-size: 2rem;
            }}
            
            .projects-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Project Portfolio</h1>
            <p class="subtitle">Intelligently named projects with smart analysis</p>
        </header>
        
        <div class="projects-grid">
{project_cards}
        </div>
        
        <footer>
            <p>Mini Software House | Intelligent Project Generation & Naming System</p>
        </footer>
    </div>
</body>
</html>
"""
        return html
    
    def _generate_tech_items(self, tech_stack: List[str]) -> str:
        """Generate tech stack items"""
        items = ""
        for tech in tech_stack:
            items += f'                    <div class="tech-item">{tech.title()}</div>\n'
        return items
    
    def _generate_feature_items(self, features: List[str]) -> str:
        """Generate feature items"""
        items = ""
        feature_names = {
            "api": "RESTful API",
            "database": "Data Persistence",
            "async": "Asynchronous Processing",
            "ai_ml": "Machine Learning",
            "websocket": "Real-time Updates",
            "docker": "Containerization",
            "testing": "Automated Testing",
            "monitoring": "Monitoring & Logging",
            "auth": "Authentication & Security",
        }
        
        for feature in features:
            name = feature_names.get(feature, feature.replace('_', ' ').title())
            items += f'                <div class="feature-item"><strong>{name}</strong></div>\n'
        return items


def save_html(content: str, filepath: str) -> bool:
    """Save HTML content to file"""
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"✓ Generated: {filepath}")
        return True
    except Exception as e:
        print(f"✗ Error saving HTML: {e}")
        return False


if __name__ == "__main__":
    # Example usage
    generator = HTMLGenerator()
    
    # Generate a single project page
    analysis = {
        "type": "backend_api",
        "complexity": "moderate",
        "tech_stack": ["Python", "FastAPI"],
        "key_features": ["api", "database", "async"],
    }
    
    html = generator.generate_project_page(
        "FastAPI Server",
        "High-performance REST API with async support and database integration",
        analysis,
        file_count=12,
        dependency_count=8
    )
    
    save_html(html, "/tmp/project_showcase.html")
