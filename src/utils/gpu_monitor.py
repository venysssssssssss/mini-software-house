#!/usr/bin/env python3
"""GPU monitoring and real-time metrics"""

import subprocess
import json
import re
from typing import Dict, Optional
from dataclasses import dataclass
import threading
import time


@dataclass
class GPUStats:
    """GPU statistics"""
    gpu_id: int
    name: str
    memory_used_mb: int
    memory_total_mb: int
    memory_percent: float
    temperature: float
    power_draw: float
    power_limit: float
    utilization: float

    def to_dict(self) -> Dict:
        return {
            "gpu_id": self.gpu_id,
            "name": self.name,
            "memory_used_mb": self.memory_used_mb,
            "memory_total_mb": self.memory_total_mb,
            "memory_percent": self.memory_percent,
            "temperature": self.temperature,
            "power_draw": self.power_draw,
            "power_limit": self.power_limit,
            "utilization": self.utilization,
        }


class GPUMonitor:
    """Monitor GPU metrics in real-time"""

    def __init__(self):
        self.has_nvidia = self._check_nvidia()
        self.monitoring = False
        self.monitor_thread = None
        self.latest_stats = []

    def _check_nvidia(self) -> bool:
        """Check if NVIDIA GPU is available"""
        try:
            subprocess.run(
                ["nvidia-smi", "-L"],
                capture_output=True,
                check=True,
                timeout=5,
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_gpu_stats(self) -> list[GPUStats]:
        """Get current GPU statistics"""
        if not self.has_nvidia:
            return []

        try:
            # Query GPU metrics using nvidia-smi
            cmd = [
                "nvidia-smi",
                "--query-gpu=index,name,memory.used,memory.total,temperature.gpu,power.draw,power.limit,utilization.gpu",
                "--format=csv,nounits,noheader",
            ]

            output = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            ).stdout.strip()

            stats = []
            for line in output.split("\n"):
                if not line.strip():
                    continue

                parts = [p.strip() for p in line.split(",")]
                
                gpu_id = int(parts[0])
                name = parts[1]
                memory_used = int(float(parts[2]))
                memory_total = int(float(parts[3]))
                memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0
                temperature = float(parts[4])
                power_draw = float(parts[5])
                power_limit = float(parts[6])
                utilization = float(parts[7])

                stat = GPUStats(
                    gpu_id=gpu_id,
                    name=name,
                    memory_used_mb=memory_used,
                    memory_total_mb=memory_total,
                    memory_percent=memory_percent,
                    temperature=temperature,
                    power_draw=power_draw,
                    power_limit=power_limit,
                    utilization=utilization,
                )
                stats.append(stat)

            self.latest_stats = stats
            return stats

        except Exception as e:
            print(f"Error querying GPU stats: {e}")
            return []

    def format_stats(self) -> str:
        """Format GPU stats for console display"""
        stats = self.get_gpu_stats()

        if not stats:
            return "No NVIDIA GPU detected or nvidia-smi unavailable"

        output = []
        output.append("=" * 80)
        output.append("GPU METRICS (Real-time)")
        output.append("=" * 80)

        for stat in stats:
            mem_bar = self._create_bar(stat.memory_percent)
            util_bar = self._create_bar(stat.utilization)

            output.append(f"\n🖥️  GPU {stat.gpu_id}: {stat.name}")
            output.append(f"   Memory: {mem_bar} {stat.memory_used_mb}/{stat.memory_total_mb} MB ({stat.memory_percent:.1f}%)")
            output.append(f"   Utilization: {util_bar} {stat.utilization:.1f}%")
            output.append(f"   Temperature: {stat.temperature:.1f}°C")
            output.append(f"   Power: {stat.power_draw:.1f}W / {stat.power_limit:.1f}W")

        output.append("\n" + "=" * 80)
        return "\n".join(output)

    @staticmethod
    def _create_bar(value: float, width: int = 20) -> str:
        """Create a simple progress bar"""
        filled = int(width * value / 100)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"

    def start_monitoring(self, callback=None, interval: float = 2.0):
        """Start monitoring GPU in background thread"""
        if self.monitoring:
            return

        self.monitoring = True

        def monitor_loop():
            while self.monitoring:
                try:
                    stats = self.get_gpu_stats()
                    if callback and stats:
                        callback(stats)
                    time.sleep(interval)
                except Exception as e:
                    print(f"Monitoring error: {e}")
                    time.sleep(interval)

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring thread"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)


# Global instance
_monitor = None


def get_monitor() -> GPUMonitor:
    """Get or create global GPU monitor"""
    global _monitor
    if _monitor is None:
        _monitor = GPUMonitor()
    return _monitor
