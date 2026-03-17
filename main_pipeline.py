#!/usr/bin/env python3
"""
Main entry point for the Mini Software House Pipeline
Optimized for GTX 1050 Ti (4GB VRAM) with sequential model execution.
"""

import sys
import argparse
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agents.orchestrator import OrchestratorAgent
from agents.rag import RAGEngine

def main():
    """Main pipeline execution."""
    parser = argparse.ArgumentParser(
        description="Mini Software House Pipeline for GTX 1050 Ti (4GB VRAM)"
    )
    parser.add_argument(
        "--task", 
        type=str, 
        required=True,
        help="The software development task to execute"
    )
    parser.add_argument(
        "--interactive", 
        action="store_true",
        help="Run in interactive mode with detailed output"
    )
    parser.add_argument(
        "--output", 
        type=str,
        help="Output file for results (JSON format)"
    )
    
    args = parser.parse_args()
    
    print("🚀 Mini Software House Pipeline")
    print("=" * 50)
    print(f"Task: {args.task}")
    print(f"VRAM Optimization: GTX 1050 Ti (4GB) Mode")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = OrchestratorAgent()
    
    # Execute pipeline
    result = orchestrator.execute_pipeline(args.task)
    
    # Display results
    if args.interactive:
        print("\n" + "=" * 50)
        print("DETAILED RESULTS")
        print("=" * 50)
        print(json.dumps(result, indent=2))
    
    # Save results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n📄 Results saved to: {args.output}")
    
    # Summary
    print("\n" + "=" * 50)
    print("PIPELINE SUMMARY")
    print("=" * 50)
    
    if result["status"] == "success":
        print("✅ Pipeline completed successfully!")
        print(f"   User Request: {result['user_request']}")
        print(f"   Architecture: {result['plan'].get('architecture', 'N/A')}")
        print(f"   Files Created: {len(result['execution_results'])}")
        print(f"   Test Status: {'PASSED' if result['test_results']['exit_code'] == 0 else 'FAILED'}")
        print(f"   Execution Time: {result['pipeline_summary']['execution_time']:.2f} seconds")
    else:
        print("❌ Pipeline failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    
    # Return appropriate exit code
    sys.exit(0 if result["status"] == "success" else 1)

if __name__ == "__main__":
    main()