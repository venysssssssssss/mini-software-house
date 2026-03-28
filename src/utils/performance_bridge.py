"""
Performance Bridge - Python FFI to Rust optimization modules
Connects Python pipeline with high-performance Rust implementations
"""

import ctypes
import json
from pathlib import Path
from typing import Any, Dict

from ..core.logger import get_logger

logger = get_logger("performance_bridge")

# Get library paths (from the Rust workspace target directory)
_RUST_TARGET = Path(__file__).parent.parent / "rust" / "target" / "release"


def _find_lib(name: str) -> Path | None:
    """Find a shared library by name, trying platform-specific extensions."""
    for ext in (".so", ".dylib", ".dll"):
        candidate = _RUST_TARGET / f"lib{name}{ext}"
        if candidate.exists():
            return candidate
    return None


class RustASTParser:
    """FFI wrapper for the Rust ast_parser crate."""

    def __init__(self):
        self._lib = None
        self._available = False
        lib_path = _find_lib("ast_parser")
        if lib_path:
            try:
                self._lib = ctypes.CDLL(str(lib_path))

                # ast_summarize_python(source: *const c_char) -> *mut c_char
                self._lib.ast_summarize_python.argtypes = [ctypes.c_char_p]
                self._lib.ast_summarize_python.restype = ctypes.c_void_p

                # ast_summarize_python_json(source: *const c_char) -> *mut c_char
                self._lib.ast_summarize_python_json.argtypes = [ctypes.c_char_p]
                self._lib.ast_summarize_python_json.restype = ctypes.c_void_p

                # ast_free_string(ptr: *mut c_char)
                self._lib.ast_free_string.argtypes = [ctypes.c_void_p]
                self._lib.ast_free_string.restype = None

                self._available = True
                logger.info("rust_ast_loaded", path=str(lib_path))
            except Exception as e:
                logger.warning("rust_ast_load_failed", error=str(e))
        else:
            logger.info("rust_ast_not_found", search_dir=str(_RUST_TARGET))

    @property
    def available(self) -> bool:
        return self._available

    def summarize(self, source: str) -> str:
        """Summarize Python source into function/class signatures (text format)."""
        if not self._available:
            raise RuntimeError("Rust ast_parser not loaded")

        ptr = self._lib.ast_summarize_python(source.encode("utf-8"))
        if not ptr:
            return ""
        result = ctypes.cast(ptr, ctypes.c_char_p).value.decode("utf-8")
        self._lib.ast_free_string(ptr)
        return result

    def summarize_json(self, source: str) -> dict:
        """Summarize Python source into structured JSON."""
        if not self._available:
            raise RuntimeError("Rust ast_parser not loaded")

        ptr = self._lib.ast_summarize_python_json(source.encode("utf-8"))
        if not ptr:
            return {"functions": [], "classes": []}
        json_str = ctypes.cast(ptr, ctypes.c_char_p).value.decode("utf-8")
        self._lib.ast_free_string(ptr)
        return json.loads(json_str)


# Singleton — loaded once at import time
_rust_ast = RustASTParser()


def get_rust_ast_parser() -> RustASTParser:
    """Return the singleton Rust AST parser (may or may not be available)."""
    return _rust_ast


class RustBridge:
    """Universal bridge to Rust optimization modules"""

    def __init__(self):
        self.lib_cache = {}
        self.ast_parser = _rust_ast
        self._load_libraries()

    def _load_libraries(self):
        """Load all available Rust libraries with fallback"""
        libs = ["libjson_parser", "libperformance_core", "libdocker_log_streamer"]

        for lib_name in libs:
            lib_path = _find_lib(lib_name.removeprefix("lib"))
            if lib_path:
                try:
                    self.lib_cache[lib_name] = ctypes.CDLL(str(lib_path))
                    logger.info("rust_lib_loaded", lib=lib_name)
                except Exception as e:
                    logger.warning("rust_lib_failed", lib=lib_name, error=str(e))

        if self.ast_parser.available:
            self.lib_cache["libast_parser"] = self.ast_parser._lib

    def parse_json_fast(self, json_str: str) -> Dict[str, Any]:
        """Fast JSON parsing (falls back to Python stdlib)."""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parse error: {e}")

    def filter_logs(self, logs: list, patterns: list) -> list:
        """Filter logs by patterns using Python (Rust version available)."""
        import re

        regex = re.compile("|".join(patterns))
        return [log for log in logs if regex.search(log)]

    def summarize_python(self, source: str) -> str:
        """Summarize Python code using Rust tree-sitter if available, else Python AST."""
        if self.ast_parser.available:
            return self.ast_parser.summarize(source)
        # Fallback to Python AST
        from ..agents.context_manager import get_code_summary

        return get_code_summary(source)

    def benchmark_modules(self) -> Dict[str, Any]:
        """Run basic benchmarks on loaded modules"""
        results = {
            "json_parser": self._benchmark_json_parse(),
            "ast_parser": self._benchmark_ast_parse(),
            "libraries_loaded": len(self.lib_cache),
            "library_names": list(self.lib_cache.keys()),
            "rust_ast_available": self.ast_parser.available,
        }
        return results

    def _benchmark_json_parse(self) -> Dict[str, float]:
        """Benchmark JSON parsing"""
        import time

        test_json = '{"status":"completed","output":{"files":["app.py"],"time":3.2}}'
        iterations = 10000

        start = time.time()
        for _ in range(iterations):
            json.loads(test_json)
        python_time = time.time() - start

        return {
            "iterations": iterations,
            "python_time_ms": python_time * 1000,
            "avg_per_ops_us": (python_time / iterations) * 1_000_000,
        }

    def _benchmark_ast_parse(self) -> Dict[str, Any]:
        """Benchmark AST parsing: Rust tree-sitter vs Python ast module."""
        import time

        test_code = """
class Example(Base):
    def __init__(self, name: str, value: int):
        self.name = name
        self.value = value

    def process(self, data: list) -> dict:
        return {"name": self.name, "count": len(data)}

    def validate(self) -> bool:
        return self.value > 0

def standalone_function(x: int, y: int) -> int:
    return x + y
"""
        iterations = 1000

        # Python AST benchmark
        from ..agents.context_manager import get_code_summary

        start = time.time()
        for _ in range(iterations):
            get_code_summary(test_code)
        python_time = time.time() - start

        result = {
            "iterations": iterations,
            "python_time_ms": round(python_time * 1000, 2),
            "python_avg_us": round((python_time / iterations) * 1_000_000, 2),
        }

        # Rust tree-sitter benchmark (if available)
        if self.ast_parser.available:
            start = time.time()
            for _ in range(iterations):
                self.ast_parser.summarize(test_code)
            rust_time = time.time() - start

            result["rust_time_ms"] = round(rust_time * 1000, 2)
            result["rust_avg_us"] = round((rust_time / iterations) * 1_000_000, 2)
            result["speedup"] = round(python_time / rust_time, 2) if rust_time > 0 else 0

        return result


def main():
    """Demo of the Rust bridge"""
    bridge = RustBridge()

    print("Benchmarks:")
    benchmarks = bridge.benchmark_modules()
    print(json.dumps(benchmarks, indent=2))

    print("\nBridge ready for integration!")


if __name__ == "__main__":
    main()
