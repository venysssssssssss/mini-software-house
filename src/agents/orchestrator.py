"""
Orchestrator Agent - The main coordinator for the Mini Software House
Implements the sequential pipeline for GTX 1050 Ti (4GB VRAM) optimization.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict

from ..core.database import get_session_direct, init_db
from ..core.events import EventBus
from ..core.logger import get_logger
from ..core.models import AgentLog, DPOTuple, PipelineRun, Project, Task, TaskStatus
from .base import Agent
from .documenter import DocumenterAgent
from .executor import ExecutorAgent
from .planner import PlannerAgent
from .rag import RAGEngine
from .tester import TesterAgent

logger = get_logger("orchestrator")


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

        # DB IDs for the current run
        self._project_id = None
        self._task_id = None
        self._pipeline_run_id = None

        # Ensure tables exist
        init_db()

    def _log_to_db(
        self,
        agent_name: str,
        level: str,
        message: str,
        data: dict | None = None,
        *,
        model: str | None = None,
        prompt_tokens: int = 0,
        response_tokens: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
    ):
        """Persist a log entry to the AgentLog table with metrics."""
        session = get_session_direct()
        try:
            entry = AgentLog(
                task_id=self._task_id,
                pipeline_run_id=self._pipeline_run_id,
                agent_name=agent_name,
                model=model,
                level=level,
                message=message,
                prompt_tokens=prompt_tokens,
                response_tokens=response_tokens,
                latency_ms=latency_ms,
                success=success,
                structured_data=json.dumps(data) if data else None,
            )
            session.add(entry)
            session.commit()
        finally:
            session.close()

    def _flush_agent_metrics(self):
        """Persist all collected agent call metrics to DB and update PipelineRun totals."""
        metrics = Agent.get_collected_metrics()
        Agent.reset_metrics()

        if not metrics:
            return

        session = get_session_direct()
        try:
            total_prompt = 0
            total_response = 0
            total_latency = 0.0

            for m in metrics:
                entry = AgentLog(
                    task_id=self._task_id,
                    pipeline_run_id=self._pipeline_run_id,
                    agent_name=m.agent_name,
                    model=m.model,
                    level="INFO" if m.success else "ERROR",
                    message="llm_call",
                    prompt_tokens=m.prompt_tokens,
                    response_tokens=m.response_tokens,
                    latency_ms=m.latency_ms,
                    success=m.success,
                    structured_data=json.dumps({"error": m.error}) if m.error else None,
                )
                session.add(entry)
                total_prompt += m.prompt_tokens
                total_response += m.response_tokens
                total_latency += m.latency_ms

            # Update PipelineRun totals
            if self._pipeline_run_id:
                run = session.get(PipelineRun, self._pipeline_run_id)
                if run:
                    run.total_prompt_tokens += total_prompt
                    run.total_response_tokens += total_response
                    run.total_latency_ms += total_latency
                    run.total_agent_calls += len(metrics)
                    session.add(run)

            session.commit()
        finally:
            session.close()

    def _save_dpo_tuple(
        self,
        agent_name: str,
        prompt: str,
        generated_code: str,
        test_result: str,
        corrected_code: str | None = None,
        error_type: str | None = None,
        correction_successful: bool | None = None,
    ):
        """Save a DPO training tuple for the data flywheel."""
        session = get_session_direct()
        try:
            dpo = DPOTuple(
                pipeline_run_id=self._pipeline_run_id,
                agent_name=agent_name,
                prompt=prompt,
                generated_code=generated_code,
                test_result=test_result,
                corrected_code=corrected_code,
                error_type=error_type,
                correction_successful=correction_successful,
            )
            session.add(dpo)
            session.commit()
        finally:
            session.close()

    def execute_pipeline(self, user_request: str) -> Dict[str, Any]:
        """
        Execute the complete pipeline:
        1. Planning
        2. Sequential Development (Backend)
        3. Testing & Auto-Correction
        4. Documentation
        """
        logger.info("pipeline.starting", request=user_request)
        EventBus.publish("pipeline.started", {"request": user_request})
        self.current_task = user_request

        # Reset metrics collector for this run
        Agent.reset_metrics()

        # Create DB records for this run
        session = get_session_direct()
        try:
            project = Project(name=user_request[:120], path="workspace")
            session.add(project)
            session.commit()
            session.refresh(project)
            self._project_id = project.id

            task = Task(
                project_id=project.id,
                description=user_request,
                status=TaskStatus.IN_PROGRESS,
            )
            session.add(task)
            session.commit()
            session.refresh(task)
            self._task_id = task.id

            pipeline_run = PipelineRun(
                project_id=project.id,
                task_id=task.id,
                user_request=user_request,
                status=TaskStatus.IN_PROGRESS,
            )
            session.add(pipeline_run)
            session.commit()
            session.refresh(pipeline_run)
            self._pipeline_run_id = pipeline_run.id
        finally:
            session.close()

        try:
            # Phase 1: Planning
            logger.info("phase.starting", phase="planning")
            EventBus.publish("phase.started", {"phase": "planning"})
            plan = self._execute_planning()
            if not plan:
                self._mark_run_failed("Planning phase failed")
                return {"status": "failed", "error": "Planning phase failed"}
            self._flush_agent_metrics()
            self._update_run_phase(1)
            EventBus.publish("phase.completed", {"phase": "planning"})

            # Phase 2: Sequential Development
            logger.info("phase.starting", phase="development")
            EventBus.publish("phase.started", {"phase": "development"})
            dev_success = self._execute_development(plan)
            if not dev_success:
                self._mark_run_failed("Development phase failed")
                return {"status": "failed", "error": "Development phase failed"}
            self._flush_agent_metrics()
            self._update_run_phase(2)
            EventBus.publish("phase.completed", {"phase": "development"})

            # Phase 3: Testing & Auto-Correction
            logger.info("phase.starting", phase="testing")
            EventBus.publish("phase.started", {"phase": "testing"})
            test_success = self._execute_testing_with_correction()
            if not test_success:
                EventBus.publish("test.failed", {"results": self.test_results})
                self._mark_run_failed("Testing phase failed")
                return {"status": "failed", "error": "Testing phase failed"}
            self._flush_agent_metrics()
            self._update_run_phase(3)
            EventBus.publish("phase.completed", {"phase": "testing"})

            # Phase 4: Documentation
            logger.info("phase.starting", phase="documentation")
            EventBus.publish("phase.started", {"phase": "documentation"})
            docs = self._execute_documentation()
            self._flush_agent_metrics()
            self._update_run_phase(4)
            EventBus.publish("phase.completed", {"phase": "documentation"})

            # Mark success
            self._mark_task_completed()
            execution_time = time.time() - self._start_time
            self._mark_run_completed(execution_time)

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
                    "execution_time": execution_time,
                    "pipeline_run_id": self._pipeline_run_id,
                },
            }

            logger.info("pipeline.completed", execution_time=execution_time)
            EventBus.publish(
                "pipeline.finished",
                {"status": "success", "execution_time": execution_time},
            )
            return result

        except Exception as e:
            logger.error("pipeline.failed", error=str(e))
            EventBus.publish("pipeline.finished", {"status": "failed", "error": str(e)})
            self._flush_agent_metrics()
            self._mark_run_failed(str(e))
            return {"status": "failed", "error": str(e)}

    def _execute_planning(self) -> Dict[str, Any]:
        """Execute the planning phase."""
        self._start_time = time.time()

        try:
            plan = self.planner.plan_task(self.current_task)
            self.plan = plan

            logger.info(
                "planning.completed",
                architecture=plan.get("architecture", "N/A"),
                files=plan.get("files_to_create", []),
                dependencies=plan.get("dependencies", []),
            )
            self._log_to_db("planner", "INFO", "Plan generated", plan)
            return plan

        except Exception as e:
            logger.error("planning.failed", error=str(e))
            self._log_to_db("planner", "ERROR", f"Planning failed: {e}")
            return {}

    def _execute_development(self, plan: Dict[str, Any]) -> bool:
        """Execute sequential development with VRAM optimization and multi-file context."""
        files_to_create = plan.get("files_to_create", [])

        if not files_to_create:
            logger.warning("development.no_files", plan=plan)
            return True

        # Use plan's project_name for workspace subdirectory
        project_name = plan.get("project_name", "")
        if project_name:
            import os

            project_dir = os.path.join(self.executor.file_manager.workspace_dir, project_name)
            os.makedirs(project_dir, exist_ok=True)
            self.executor.file_manager.workspace_dir = os.path.abspath(project_dir)

        for i, file_task in enumerate(files_to_create):
            logger.info(
                "development.file",
                file=file_task,
                progress=f"{i + 1}/{len(files_to_create)}",
            )

            file_task_description = (
                f"Create the file '{file_task}'. "
                "Focus on clean, efficient code. Output the complete file content."
            )

            try:
                # Pass plan context so executor has full project awareness
                response, saved_files = self.executor.execute_task(
                    file_task_description, plan=plan
                )
                self.execution_results.append(
                    {
                        "file": file_task,
                        "saved_files": saved_files,
                        "response_length": len(response),
                    }
                )

                logger.info("development.file_saved", files=saved_files)
                self._log_to_db(
                    "executor",
                    "INFO",
                    f"Created {file_task}",
                    {"saved_files": saved_files},
                )

                # Index the created code for RAG
                self.rag.index_workspace()

            except Exception as e:
                logger.error("development.file_failed", file=file_task, error=str(e))
                self._log_to_db("executor", "ERROR", f"Failed: {file_task}: {e}")
                return False

        return True

    def _execute_testing_with_correction(self) -> bool:
        """Execute testing with auto-correction loop, error classification, and DPO logging."""
        max_correction_attempts = 3
        correction_attempts = 0

        # Snapshot original code for hallucination detection
        original_files = self.executor.file_manager.read_existing_files()

        while correction_attempts < max_correction_attempts:
            logger.info(
                "testing.attempt",
                attempt=correction_attempts + 1,
                max_attempts=max_correction_attempts,
            )

            try:
                test_response = self.tester.generate_tests()
                logger.info("testing.tests_generated", length=len(test_response))

                test_result = self.tester.run_tests()
                self.test_results = {
                    "attempt": correction_attempts + 1,
                    "exit_code": test_result["exit_code"],
                    "output": test_result["output"],
                }

                if test_result["exit_code"] == 0:
                    logger.info("testing.passed")
                    self._log_to_db("tester", "INFO", "All tests passed")

                    # Save DPO tuple for successful first-pass code
                    if correction_attempts == 0:
                        for file_result in self.execution_results:
                            for fpath in file_result.get("saved_files", []):
                                self._save_dpo_tuple(
                                    agent_name="executor",
                                    prompt=self.current_task,
                                    generated_code=fpath,
                                    test_result="pass",
                                )
                    return True
                else:
                    # Classify the error type
                    error_type = self.tester.classify_error(test_result["output"])
                    error_details = self.tester.parse_error(test_result["output"])

                    logger.warning(
                        "testing.failed",
                        exit_code=test_result["exit_code"],
                        attempt=correction_attempts + 1,
                        error_type=error_type or "unknown",
                    )
                    EventBus.publish(
                        "test.failed",
                        {
                            "exit_code": test_result["exit_code"],
                            "attempt": correction_attempts + 1,
                            "error_type": error_type,
                        },
                    )

                    self._log_to_db(
                        "tester",
                        "WARNING",
                        "Tests failed",
                        {
                            "error": error_details[:500],
                            "error_type": error_type,
                            "attempt": correction_attempts + 1,
                        },
                    )

                    # Build targeted correction prompt
                    correction_task = self.tester.build_correction_prompt(
                        error_details, error_type
                    )

                    logger.info(
                        "testing.correction_started",
                        attempt=correction_attempts + 1,
                        error_type=error_type or "unknown",
                    )
                    correction_response, corrected_files = self.executor.execute_task(
                        correction_task
                    )

                    # Hallucination guard: reject if >80% changed
                    new_files = self.executor.file_manager.read_existing_files()
                    hallucination_detected = False
                    for fpath, old_content in original_files.items():
                        new_content = new_files.get(fpath, "")
                        if self.tester.check_hallucination(old_content, new_content):
                            logger.warning(
                                "testing.hallucination_detected",
                                file=fpath,
                                attempt=correction_attempts + 1,
                            )
                            hallucination_detected = True
                            # Restore original file
                            self.executor.file_manager.save_file(fpath, old_content)

                    if hallucination_detected:
                        self._log_to_db(
                            "tester",
                            "WARNING",
                            "Hallucination guard triggered — correction rejected",
                            {"attempt": correction_attempts + 1},
                        )

                    # Save DPO tuple for correction
                    self._save_dpo_tuple(
                        agent_name="executor",
                        prompt=correction_task,
                        generated_code=str(corrected_files),
                        test_result=error_details[:1000],
                        error_type=error_type,
                        correction_successful=None,  # will be determined next iteration
                    )

                    logger.info(
                        "testing.correction_applied",
                        length=len(correction_response),
                    )

                    correction_attempts += 1

            except Exception as e:
                logger.error("testing.error", error=str(e))
                self._log_to_db("tester", "ERROR", f"Testing error: {e}")
                return False

        logger.error("testing.max_retries_exhausted")
        self._log_to_db("tester", "ERROR", "Max correction attempts reached")
        return False

    def _execute_documentation(self) -> str:
        """Execute documentation generation."""
        try:
            docs = self.documenter.generate_documentation()
            logger.info("documentation.completed", length=len(docs))
            self._log_to_db("documenter", "INFO", "Documentation generated", {"length": len(docs)})
            return docs
        except Exception as e:
            logger.error("documentation.failed", error=str(e))
            self._log_to_db("documenter", "ERROR", f"Documentation failed: {e}")
            return ""

    def _update_run_phase(self, completed_phases: int):
        """Update the PipelineRun completed phase count."""
        if not self._pipeline_run_id:
            return
        session = get_session_direct()
        try:
            run = session.get(PipelineRun, self._pipeline_run_id)
            if run:
                run.completed_phases = completed_phases
                session.add(run)
                session.commit()
        finally:
            session.close()

    def _mark_run_completed(self, execution_time: float):
        """Mark PipelineRun as completed and update task."""
        session = get_session_direct()
        try:
            if self._pipeline_run_id:
                run = session.get(PipelineRun, self._pipeline_run_id)
                if run:
                    run.status = TaskStatus.COMPLETED
                    run.execution_time_s = execution_time
                    run.finished_at = datetime.now(timezone.utc)
                    session.add(run)
            session.commit()
        finally:
            session.close()

    def _mark_run_failed(self, reason: str):
        """Mark both PipelineRun and Task as failed."""
        session = get_session_direct()
        try:
            if self._task_id:
                task = session.get(Task, self._task_id)
                if task:
                    task.status = TaskStatus.FAILED
                    session.add(task)
            if self._pipeline_run_id:
                run = session.get(PipelineRun, self._pipeline_run_id)
                if run:
                    run.status = TaskStatus.FAILED
                    run.finished_at = datetime.now(timezone.utc)
                    session.add(run)
            session.commit()
        finally:
            session.close()

    def _mark_task_failed(self, reason: str):
        """Update the DB task record to FAILED."""
        self._mark_run_failed(reason)

    def _mark_task_completed(self):
        """Update the DB task record to COMPLETED."""
        if not self._task_id:
            return
        session = get_session_direct()
        try:
            task = session.get(Task, self._task_id)
            if task:
                task.status = TaskStatus.COMPLETED
                session.add(task)
                session.commit()
        finally:
            session.close()

    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            "current_task": self.current_task,
            "plan_completed": bool(self.plan),
            "execution_completed": len(self.execution_results) > 0,
            "testing_completed": bool(self.test_results),
            "documentation_completed": False,
            "execution_results": self.execution_results,
            "test_results": self.test_results,
        }


def main():
    """Example usage of the orchestrator."""
    orchestrator = OrchestratorAgent()

    user_request = (
        "Create a simple task management API with FastAPI "
        "that allows users to create, read, update, and delete tasks."
    )

    result = orchestrator.execute_pipeline(user_request)

    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
