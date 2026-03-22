"""
Orchestrator Agent - The main coordinator for the Mini Software House
Implements the sequential pipeline for GTX 1050 Ti (4GB VRAM) optimization.
"""

import json
import time
from typing import Dict, Any, List, Optional
from colorama import Fore, Style, init

from .planner import PlannerAgent
from .executor import ExecutorAgent
from .tester import TesterAgent
from .documenter import DocumenterAgent
from .rag import RAGEngine
from ..utils.docker_runner import DockerRunner

init(autoreset=True)

class OrchestratorAgent:
    """Main orchestrator that manages the sequential agent pipeline."""
    
    def __init__(self):
        self.planner = PlannerAgent()
        self.executor = ExecutorAgent()
        self.tester = TesterAgent()
        self.documenter = DocumenterAgent()
        self.rag = RAGEngine()
        
        # Pipeline state
        self.current_task = ""
        self.plan = {}
        self.execution_results = []
        self.test_results = {}
        
    def log_action(self, message: str, color=Fore.WHITE):
        """Centralized logging with color coding."""
        print(f"{color}[Orchestrator] {message}{Style.RESET_ALL}")
    
    def execute_pipeline(self, user_request: str) -> Dict[str, Any]:
        """
        Execute the complete pipeline:
        1. Planning
        2. Sequential Development (Backend)
        3. Testing
        4. Auto-Correction Loop
        5. Documentation
        """
        self.log_action(f"🚀 Starting pipeline for: {user_request}", Fore.CYAN)
        self.current_task = user_request
        
        try:
            # Phase 1: Planning
            self.log_action("📋 Phase 1: Planning", Fore.BLUE)
            plan = self._execute_planning()
            if not plan:
                return {"status": "failed", "error": "Planning phase failed"}
            
            # Phase 2: Sequential Development
            self.log_action("🏗️  Phase 2: Sequential Development", Fore.GREEN)
            dev_success = self._execute_development(plan)
            if not dev_success:
                return {"status": "failed", "error": "Development phase failed"}
            
            # Phase 3: Testing & Auto-Correction
            self.log_action("🧪 Phase 3: Testing & Auto-Correction", Fore.YELLOW)
            test_success = self._execute_testing_with_correction()
            if not test_success:
                return {"status": "failed", "error": "Testing phase failed"}
            
            # Phase 4: Documentation
            self.log_action("📚 Phase 4: Documentation", Fore.MAGENTA)
            docs = self._execute_documentation()
            
            # Final result
            result = {
                "status": "success",
                "user_request": user_request,
                "plan": plan,
                "execution_results": self.execution_results,
                "test_results": self.test_results,
                "documentation": docs,
                "pipeline_summary": {
                    "total_phases": 4,
                    "completed_phases": 4,
                    "execution_time": time.time() - self._start_time
                }
            }
            
            self.log_action("✅ Pipeline completed successfully!", Fore.GREEN)
            return result
            
        except Exception as e:
            self.log_action(f"❌ Pipeline failed with error: {e}", Fore.RED)
            return {"status": "failed", "error": str(e)}
    
    def _execute_planning(self) -> Dict[str, Any]:
        """Execute the planning phase."""
        self._start_time = time.time()
        
        try:
            plan = self.planner.plan_task(self.current_task)
            self.plan = plan
            
            self.log_action(f"Architecture: {plan.get('architecture', 'N/A')}")
            self.log_action(f"Files to create: {', '.join(plan.get('files_to_create', []))}")
            self.log_action(f"Dependencies: {', '.join(plan.get('dependencies', []))}")
            
            return plan
            
        except Exception as e:
            self.log_action(f"Planning failed: {e}", Fore.RED)
            return {}
    
    def _execute_development(self, plan: Dict[str, Any]) -> bool:
        """Execute sequential development with VRAM optimization."""
        files_to_create = plan.get("files_to_create", [])
        
        if not files_to_create:
            self.log_action("No files to create in plan", Fore.YELLOW)
            return True
        
        for i, file_task in enumerate(files_to_create):
            self.log_action(f"💻 Creating file {i+1}/{len(files_to_create)}: {file_task}")
            
            # Create specific task for this file
            file_task_description = f"Create the file '{file_task}' based on the overall plan. "
            file_task_description += f"Plan: {plan.get('architecture', '')}. "
            file_task_description += f"Dependencies: {', '.join(plan.get('dependencies', []))}. "
            file_task_description += "Focus on clean, efficient code. Output the complete file content."
            
            try:
                # Execute the task
                response, saved_files = self.executor.execute_task(file_task_description)
                self.execution_results.append({
                    "file": file_task,
                    "saved_files": saved_files,
                    "response_length": len(response)
                })
                
                self.log_action(f"✓ Successfully created: {', '.join(saved_files)}")
                
                # Index the created code for RAG
                self.rag.index_workspace()
                
            except Exception as e:
                self.log_action(f"✗ Failed to create {file_task}: {e}", Fore.RED)
                return False
        
        return True
    
    def _execute_testing_with_correction(self) -> bool:
        """Execute testing with auto-correction loop."""
        max_correction_attempts = 3
        correction_attempts = 0
        
        while correction_attempts < max_correction_attempts:
            self.log_action(f"🧪 Running tests (attempt {correction_attempts + 1}/{max_correction_attempts})")
            
            try:
                # Generate tests
                test_response = self.tester.generate_tests()
                self.log_action(f"Generated tests: {len(test_response)} characters")
                
                # Run tests in Docker
                test_result = self.tester.run_tests()
                
                self.test_results = {
                    "attempt": correction_attempts + 1,
                    "exit_code": test_result["exit_code"],
                    "output": test_result["output"]
                }
                
                # Check if tests passed
                if test_result["exit_code"] == 0:
                    self.log_action("✅ All tests passed!")
                    return True
                else:
                    self.log_action(f"❌ Tests failed with exit code {test_result['exit_code']}")
                    
                    # Parse error for correction
                    error_details = self.tester.parse_error(test_result["output"])
                    self.log_action(f"Error details: {error_details[:200]}...")
                    
                    # Auto-correction: feed error back to executor
                    correction_task = f"""
                    The following tests failed:
                    {error_details}
                    
                    Please fix the code based on these test failures. 
                    Focus on the specific errors mentioned above.
                    Re-execute the corrected code and ensure tests pass.
                    """
                    
                    self.log_action("🔄 Starting auto-correction loop")
                    correction_response, _ = self.executor.execute_task(correction_task)
                    self.log_action(f"Correction applied: {len(correction_response)} characters")
                    
                    correction_attempts += 1
                    
            except Exception as e:
                self.log_action(f"Testing failed: {e}", Fore.RED)
                return False
        
        self.log_action("❌ Maximum correction attempts reached. Tests still failing.", Fore.RED)
        return False
    
    def _execute_documentation(self) -> str:
        """Execute documentation generation."""
        try:
            docs = self.documenter.generate_documentation()
            self.log_action(f"Generated documentation: {len(docs)} characters")
            return docs
        except Exception as e:
            self.log_action(f"Documentation failed: {e}", Fore.RED)
            return ""
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "current_task": self.current_task,
            "plan_completed": bool(self.plan),
            "execution_completed": len(self.execution_results) > 0,
            "testing_completed": bool(self.test_results),
            "documentation_completed": False,  # Would need to track this
            "execution_results": self.execution_results,
            "test_results": self.test_results
        }

def main():
    """Example usage of the orchestrator."""
    orchestrator = OrchestratorAgent()
    
    # Example user request
    user_request = "Create a simple task management API with FastAPI that allows users to create, read, update, and delete tasks."
    
    result = orchestrator.execute_pipeline(user_request)
    
    print("\n" + "="*60)
    print("PIPELINE RESULTS")
    print("="*60)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()