"""
Smart Project Naming Engine
Analyzes project characteristics and generates intelligent project names.
Not just "workspace" - understands what the project actually does.
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from enum import Enum

class ProjectType(Enum):
    """Project type classifications"""
    BACKEND_API = "backend_api"
    FRONTEND_APP = "frontend_app"
    FULLSTACK = "fullstack"
    DATA_PIPELINE = "data_pipeline"
    ML_MODEL = "ml_model"
    TESTING_SUITE = "testing_suite"
    INFRASTRUCTURE = "infrastructure"
    LIBRARY = "library"
    MICROSERVICE = "microservice"
    UNKNOWN = "unknown"

class ProjectComplexity(Enum):
    """Project complexity levels"""
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"

class NamingEngine:
    """
    Intelligent project naming system that creates memorable, descriptive project names
    based on actual project characteristics rather than generic defaults.
    """
    
    # Naming patterns for different project types
    PATTERNS = {
        ProjectType.BACKEND_API: [
            "API {tech}", "REST {tech}", "{tech}Backend", "{tech}Server",
            "API Gateway", "{tech}Service", "DataHub", "APIHub"
        ],
        ProjectType.FRONTEND_APP: [
            "{tech} Dashboard", "{tech} Suite", "UI {tech}", "WebApp {tech}",
            "DashVue", "UIFlow", "ContentHub", "ViewPro"
        ],
        ProjectType.FULLSTACK: [
            "{tech} Platform", "{tech} Stack", "Full {tech}", "Platform Pro",
            "StackForge", "IntegraHub", "CloudApp", "UnityHub"
        ],
        ProjectType.DATA_PIPELINE: [
            "Pipeline {tech}", "DataFlow {tech}", "ETL Pro", "DataBridge",
            "FlowStream", "PipelineForge", "DataLake", "StreamFlow"
        ],
        ProjectType.ML_MODEL: [
            "ML Engine", "NeuralHub", "ModelSmith", "MLWorkflow",
            "DeepForge", "AILab", "NeuralForge", "IntelliModel"
        ],
        ProjectType.TESTING_SUITE: [
            "QA {tech}", "TestHub", "ValidateX", "TestForge",
            "QAFlow", "TestVault", "AssertHub", "VerifyPro"
        ],
        ProjectType.INFRASTRUCTURE: [
            "Infra {tech}", "DevOps Hub", "CloudForge", "DeployPro",
            "InfraFlow", "CloudPower", "DeployHub", "OpsMaster"
        ],
        ProjectType.LIBRARY: [
            "Lib {tech}", "{tech}Kit", "Utils {tech}", "ToolBox",
            "CodeKit", "LibForge", "UtilHub", "ToolPro"
        ],
        ProjectType.MICROSERVICE: [
            "Service {tech}", "MicroHub", "ServiceForge", "Agent {tech}",
            "MicroFlow", "ServiceHub", "AgentPro", "CloudService"
        ],
        ProjectType.UNKNOWN: [
            "{tech} Project", "Project {tech}", "App {tech}", "{tech}Lab"
        ]
    }
    
    # Technology stack identifiers
    TECH_KEYWORDS = {
        "python": ["py", "python", "django", "flask", "fastapi", "pydantic"],
        "rust": ["rust", "tokio", "actix", "rocket"],
        "javascript": ["js", "javascript", "node", "react", "vue", "angular"],
        "typescript": ["ts", "typescript"],
        "go": ["go", "golang"],
        "java": ["java", "spring", "maven"],
        "cpp": ["cpp", "c++", "boost"],
    }
    
    # Feature keywords that influence naming
    FEATURE_KEYWORDS = {
        "api": ["api", "rest", "graphql", "endpoint", "request", "route"],
        "database": ["db", "database", "mongo", "postgres", "sql", "redis", "cache"],
        "async": ["async", "await", "tokio", "concurrent", "parallel", "thread"],
        "ai_ml": ["ai", "ml", "model", "neural", "torch", "tensorflow", "sklearn"],
        "websocket": ["websocket", "ws", "realtime", "chat", "stream", "socket"],
        "docker": ["docker", "container", "compose", "kubernetes", "k8s"],
        "testing": ["test", "pytest", "jest", "unit", "integration", "e2e"],
        "monitoring": ["monitor", "log", "trace", "metric", "observability"],
        "auth": ["auth", "jwt", "oauth", "security", "password", "token"],
    }
    
    def __init__(self):
        """Initialize the naming engine"""
        self.generated_names: Dict[str, str] = {}
    
    def analyze_project(
        self, 
        files: List[str], 
        dependencies: List[str],
        content_samples: Dict[str, str] = None,
        task_description: str = None
    ) -> Dict:
        """
        Analyze project characteristics to determine type and complexity
        
        Args:
            files: List of project file paths
            dependencies: List of project dependencies
            content_samples: Sample code content by file
            task_description: High-level task description
        
        Returns:
            Dict with analysis results (type, complexity, tech_stack, etc.)
        """
        project_type = self._classify_project_type(files, dependencies, task_description)
        complexity = self._estimate_complexity(files, dependencies, content_samples)
        tech_stack = self._identify_tech_stack(dependencies)
        key_features = self._extract_key_features(files, dependencies, content_samples)
        
        return {
            "type": project_type.value,
            "complexity": complexity.value,
            "tech_stack": tech_stack,
            "key_features": key_features,
            "file_count": len(files),
            "dependency_count": len(dependencies),
        }
    
    def generate_name(
        self,
        analysis: Dict,
        base_context: str = None,
        custom_words: List[str] = None,
        task_description: str = None
    ) -> Tuple[str, str]:
        """
        Generate an intelligent project name based on analysis
        Pattern: action-object-purpose (kebab-case)
        
        Args:
            analysis: Project analysis from analyze_project()
            base_context: Additional context for naming
            custom_words: Custom words to incorporate
            task_description: The problem the project solves
        
        Returns:
            Tuple of (project_name, description) in kebab-case format
        """
        project_type = ProjectType(analysis["type"])
        features = analysis["key_features"]
        
        # NEW: Generate kebab-case name from task description
        if task_description:
            kebab_name = self._generate_kebab_name(task_description, project_type, features)
            description = self._generate_description(project_type, analysis, features)
            return kebab_name, description
        
        # Fallback: Original pattern-based generation
        tech = analysis["tech_stack"][0] if analysis["tech_stack"] else "Pro"
        patterns = self.PATTERNS.get(project_type, self.PATTERNS[ProjectType.UNKNOWN])
        name = self._apply_pattern(patterns[0], tech)
        
        # Enhance with key features if available
        if "api" in features and "database" in features:
            name = f"{name} (DB)"
        elif "async" in features:
            name = f"{name} (Async)"
        elif "monitoring" in features:
            name = f"{name} (Monitor)"
        
        # Generate description
        description = self._generate_description(project_type, analysis, features)
        
        return name, description
    
    def generate_batch(
        self,
        projects: List[Dict],
        context: str = None
    ) -> List[Tuple[str, str, Dict]]:
        """
        Generate names for multiple projects
        
        Args:
            projects: List of project data
            context: Workspace context
        
        Returns:
            List of (name, description, analysis) tuples
        """
        results = []
        for project in projects:
            analysis = self.analyze_project(
                project.get("files", []),
                project.get("dependencies", []),
                project.get("content", {}),
                project.get("description", "")
            )
            name, description = self.generate_name(analysis)
            results.append((name, description, analysis))
        
        return results
    
    # ========== Private Methods ==========
    
    def _classify_project_type(
        self,
        files: List[str],
        dependencies: List[str],
        task_description: str = None
    ) -> ProjectType:
        """Classify project type based on files and dependencies"""
        files_lower = [f.lower() for f in files]
        deps_lower = [d.lower() for d in dependencies]
        desc_lower = (task_description or "").lower()
        
        # Check for specific patterns
        has_tests = any("test" in f for f in files_lower)
        has_routes = any("route" in f or "api" in f for f in files_lower)
        has_models = any("model" in f for f in files_lower)
        has_ui = any(ext in f for f in files_lower for ext in [".html", ".jsx", ".tsx", ".vue"])
        has_ml = any(lib in deps_lower for lib in ["torch", "tensorflow", "sklearn", "ml"])
        has_docker = any(ext in files_lower for ext in ["dockerfile", "docker-compose.yml"])
        
        # Logic to determine type
        if has_ml:
            return ProjectType.ML_MODEL
        elif has_tests and not has_routes and not has_ui:
            return ProjectType.TESTING_SUITE
        elif "pipeline" in desc_lower or "etl" in desc_lower:
            return ProjectType.DATA_PIPELINE
        elif has_routes and has_models and not has_ui:
            return ProjectType.BACKEND_API
        elif has_ui and not has_routes:
            return ProjectType.FRONTEND_APP
        elif has_ui and has_routes:
            return ProjectType.FULLSTACK
        elif has_docker or "infra" in desc_lower:
            return ProjectType.INFRASTRUCTURE
        elif "lib" in desc_lower or "util" in desc_lower:
            return ProjectType.LIBRARY
        elif len(files) < 5:
            return ProjectType.MICROSERVICE
        
        return ProjectType.UNKNOWN
    
    def _estimate_complexity(
        self,
        files: List[str],
        dependencies: List[str],
        content_samples: Dict[str, str] = None
    ) -> ProjectComplexity:
        """Estimate project complexity"""
        # Simple heuristics
        total_elements = len(files) + len(dependencies)
        content_size = sum(len(c) for c in (content_samples or {}).values())
        
        if total_elements < 10 and content_size < 5000:
            return ProjectComplexity.SIMPLE
        elif total_elements < 30 and content_size < 20000:
            return ProjectComplexity.MODERATE
        else:
            return ProjectComplexity.COMPLEX
    
    def _identify_tech_stack(self, dependencies: List[str]) -> List[str]:
        """Identify primary technologies from dependencies"""
        tech_stack = []
        deps_lower = [d.lower() for d in dependencies]
        
        for tech, keywords in self.TECH_KEYWORDS.items():
            if any(kw in deps_str for kw in keywords for deps_str in deps_lower):
                tech_stack.append(tech)
        
        # Ensure at least one tech
        if not tech_stack:
            tech_stack = ["General"]
        
        return tech_stack[:2]  # Return top 2 techs
    
    def _extract_key_features(
        self,
        files: List[str],
        dependencies: List[str],
        content_samples: Dict[str, str] = None
    ) -> List[str]:
        """Extract key features from project"""
        features = []
        files_lower = [f.lower() for f in files]
        deps_lower = [d.lower() for d in dependencies]
        content_lower = " ".join((content_samples or {}).values()).lower()
        
        all_text = " ".join(files_lower + deps_lower + [content_lower])
        
        for feature, keywords in self.FEATURE_KEYWORDS.items():
            if any(kw in all_text for kw in keywords):
                features.append(feature)
        
        return features[:5]  # Top 5 features
    
    def _generate_kebab_name(
        self,
        task_description: str,
        project_type: ProjectType,
        features: List[str]
    ) -> str:
        """
        Generate kebab-case project name from task description.
        Pattern: action-object-purpose
        
        Examples:
        - "Build a REST API for user management" → "api-user-manager"
        - "Create a real-time chat application" → "realtime-chat-app"
        - "Machine learning image recognition" → "ml-image-recognizer"
        
        Args:
            task_description: Description of what the project does
            project_type: Classified project type
            features: List of key features
        
        Returns:
            Kebab-case project name
        """
        desc_lower = task_description.lower()
        
        # Extract action verb
        action_verbs = {
            "build": "build",
            "create": "create",
            "develop": "dev",
            "generate": "gen",
            "analyze": "analyze",
            "process": "processor",
            "manage": "mgr",
            "monitor": "monitor",
            "track": "tracker",
            "stream": "stream",
            "sync": "sync",
            "transform": "transform",
        }
        
        action = "app"
        for verb, short in action_verbs.items():
            if verb in desc_lower:
                action = short
                break
        
        # Extract main object (noun) - what is being created
        object_keywords = {
            "api": "api",
            "rest": "rest",
            "graphql": "graphql",
            "dashboard": "dashboard",
            "interface": "ui",
            "website": "web",
            "application": "app",
            "service": "svc",
            "tool": "tool",
            "engine": "engine",
            "pipeline": "pipeline",
            "model": "model",
            "bot": "bot",
            "chat": "chat",
            "server": "server",
            "client": "client",
            "framework": "framework",
            "library": "lib",
        }
        
        main_object = "app"
        for keyword, short in object_keywords.items():
            if keyword in desc_lower:
                main_object = short
                break
        
        # Extract domain/purpose - what problem it solves
        # Extract first meaningful noun after common prepositions
        purpose_keywords = [
            "user", "admin", "product", "order", "inventory", "task",
            "todo", "note", "event", "message", "payment", "billing",
            "report", "analytics", "metric", "data", "content", "media",
            "image", "video", "document", "file", "storage", "cache",
            "queue", "stream", "log", "monitor", "alert", "notification",
            "recommendation", "search", "recommendation", "translation",
            "sentiment", "classification", "detection", "recognition",
            "optimization", "scheduling", "allocation", "routing",
        ]
        
        purpose_words = []
        words = re.findall(r'\w+', desc_lower)
        for i, word in enumerate(words):
            if word in purpose_keywords and word not in [action, main_object]:
                purpose_words.append(word)
        
        # Extract tech features for naming
        tech_suffixes = {
            "api": "api",
            "async": "async",
            "realtime": "rt",
            "real-time": "rt",
            "websocket": "ws",
            "db": "db",
            "database": "db",
            "sql": "sql",
            "nosql": "nosql",
            "mongodb": "mongo",
            "postgres": "postgres",
            "redis": "redis",
            "cache": "cache",
            "ml": "ml",
            "ai": "ai",
            "neural": "neural",
            "deep": "deep",
            "learning": "learn",
            "docker": "docker",
            "kubernetes": "k8s",
            "microservice": "micro",
        }
        
        tech_name = None
        for keyword, short in tech_suffixes.items():
            if keyword in desc_lower:
                tech_name = short
                break
        
        # Build kebab-case name: action-purpose-object or action-tech-object
        parts = []
        
        # Add action if it's meaningful
        if action != "app":
            parts.append(action)
        
        # Add purpose (max 2 words)
        if purpose_words:
            parts.extend(purpose_words[:2])
        
        # Add tech if present
        if tech_name and tech_name not in parts:
            parts.append(tech_name)
        
        # Add main object if not already included
        if main_object not in parts:
            parts.append(main_object)
        
        # Ensure we have at least 2 parts
        if len(parts) < 2:
            if purpose_words:
                parts = [purpose_words[0], main_object]
            else:
                parts = [action, main_object]
        
        # Create kebab-case name (max 5 parts)
        kebab_name = "-".join(parts[:5])
        
        # Clean up: remove duplicates and normalize
        name_parts = kebab_name.split("-")
        seen = set()
        unique_parts = []
        for part in name_parts:
            if part not in seen and part:
                unique_parts.append(part)
                seen.add(part)
        
        final_name = "-".join(unique_parts[:4])
        
        return final_name if final_name else "project-app"
    
    def _apply_pattern(self, pattern: str, tech: str) -> str:
        """Apply naming pattern with technology"""
        return pattern.replace("{tech}", tech.capitalize())
    
    def _generate_description(
        self,
        project_type: ProjectType,
        analysis: Dict,
        features: List[str]
    ) -> str:
        """Generate human-readable project description"""
        type_descriptions = {
            ProjectType.BACKEND_API: "REST API backend service",
            ProjectType.FRONTEND_APP: "Interactive web interface",
            ProjectType.FULLSTACK: "Complete end-to-end application",
            ProjectType.DATA_PIPELINE: "Data processing and transformation workflow",
            ProjectType.ML_MODEL: "Machine learning model and inference pipeline",
            ProjectType.TESTING_SUITE: "Comprehensive testing and validation framework",
            ProjectType.INFRASTRUCTURE: "Infrastructure and deployment platform",
            ProjectType.LIBRARY: "Reusable utility library",
            ProjectType.MICROSERVICE: "Lightweight microservice component",
            ProjectType.UNKNOWN: "Custom application project",
        }
        
        base_desc = type_descriptions.get(project_type, "Project")
        
        # Add complexity
        complex_text = f"({analysis['complexity'].upper()})"
        
        # Add key capabilities
        capabilities = []
        if "api" in features:
            capabilities.append("API")
        if "database" in features:
            capabilities.append("data persistence")
        if "async" in features:
            capabilities.append("async processing")
        if "websocket" in features:
            capabilities.append("real-time communication")
        if "monitoring" in features:
            capabilities.append("observability")
        
        if capabilities:
            return f"{base_desc} {complex_text} with {', '.join(capabilities)}"
        else:
            return f"{base_desc} {complex_text}"


    def generate_project_name_from_task(
        self,
        task_description: str,
        project_type: str = None,
        dependencies: List[str] = None
    ) -> str:
        """
        Quick method to generate kebab-case project name from just a task description.
        Perfect for use in agents during planning/execution phase.
        
        Args:
            task_description: Description of what the project does (the problem it solves)
            project_type: Optional ProjectType override
            dependencies: Optional list of dependencies
        
        Returns:
            Kebab-case project name (e.g., "api-user-manager")
        
        Example:
            >>> engine = NamingEngine()
            >>> name = engine.generate_project_name_from_task(
            ...     "Build a REST API for managing user accounts with authentication"
            ... )
            >>> print(name)
            # Output: "api-user-manager"
        """
        # Quick analysis
        files = task_description.split()  # Just split to get word count for complexity
        deps = dependencies or []
        
        analysis = self.analyze_project(
            files=files,
            dependencies=deps,
            task_description=task_description
        )
        
        # Generate kebab-case name
        name, _ = self.generate_name(analysis, task_description=task_description)
        return name


def load_project_metadata(workspace_path: str) -> Optional[Dict]:
    """Load project metadata from workspace"""
    try:
        import os
        
        files = []
        dependencies = []
        
        for root, dirs, filenames in os.walk(workspace_path):
            # Skip common non-essential directories
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.pytest_cache'}]
            
            for filename in filenames:
                if not filename.startswith('.'):
                    filepath = os.path.join(root, filename)
                    rel_path = os.path.relpath(filepath, workspace_path)
                    files.append(rel_path)
        
        # Try to load dependencies from various package files
        package_files = {
            "requirements.txt": "pip",
            "Cargo.toml": "cargo",
            "package.json": "npm",
            "Gemfile": "ruby",
        }
        
        for pkg_file, manager in package_files.items():
            pkg_path = os.path.join(workspace_path, pkg_file)
            if os.path.exists(pkg_path):
                try:
                    with open(pkg_path, 'r') as f:
                        content = f.read()
                        # Simple parsing - just extract names
                        for line in content.split('\n'):
                            line = line.strip()
                            if line and not line.startswith('#') and '=' not in line:
                                dependencies.append(line.split()[0])
                except:
                    pass
        
        return {
            "files": files,
            "dependencies": dependencies,
        }
    except Exception as e:
        print(f"Error loading project metadata: {e}")
        return None


if __name__ == "__main__":
    # Example usage
    engine = NamingEngine()
    
    print("=" * 60)
    print("🎯 NAMING ENGINE - KEBAB-CASE PROJECT NAMING")
    print("=" * 60)
    
    # Test 1: FastAPI backend with database
    print("\n📋 Test 1: REST API with Database")
    analysis = engine.analyze_project(
        files=["main.py", "models.py", "routes.py", "requirements.txt"],
        dependencies=["fastapi", "pydantic", "sqlalchemy", "postgresql"],
        task_description="Build a REST API for user management with PostgreSQL database"
    )
    name, description = engine.generate_name(analysis, task_description="Build a REST API for user management with PostgreSQL database")
    print(f"  Project Name: {name}")
    print(f"  Description: {description}")
    
    # Test 2: Real-time chat app
    print("\n📋 Test 2: Real-time Chat Application")
    analysis = engine.analyze_project(
        files=["app.py", "chat.py", "websocket.py", "db.py"],
        dependencies=["fastapi", "websockets", "sqlalchemy"],
        task_description="Create a real-time chat application with WebSocket support"
    )
    name, description = engine.generate_name(analysis, task_description="Create a real-time chat application with WebSocket support")
    print(f"  Project Name: {name}")
    print(f"  Description: {description}")
    
    # Test 3: ML image recognition
    print("\n📋 Test 3: Machine Learning Image Recognition")
    analysis = engine.analyze_project(
        files=["model.py", "train.py", "inference.py"],
        dependencies=["torch", "torchvision", "tensorflow", "opencv"],
        task_description="Build a machine learning model for image recognition and classification"
    )
    name, description = engine.generate_name(analysis, task_description="Build a machine learning model for image recognition and classification")
    print(f"  Project Name: {name}")
    print(f"  Description: {description}")
    
    # Test 4: Data pipeline
    print("\n📋 Test 4: Data Pipeline Processing")
    analysis = engine.analyze_project(
        files=["pipeline.py", "etl.py", "transform.py"],
        dependencies=["pandas", "pyspark", "kafka"],
        task_description="Develop a data processing pipeline for ETL operations with real-time streaming"
    )
    name, description = engine.generate_name(analysis, task_description="Develop a data processing pipeline for ETL operations with real-time streaming")
    print(f"  Project Name: {name}")
    print(f"  Description: {description}")
    
    print("\n" + "=" * 60)
