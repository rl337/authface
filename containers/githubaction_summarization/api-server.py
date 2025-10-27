#!/usr/bin/env python3
"""
Health and status API server for weirdness-githubaction runner.
Provides /health and /api/status endpoints as required by rl337/callableapis platform.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin requests

# Container metadata
CONTAINER_NAME = "weirdness-githubaction"
VERSION = os.getenv("VERSION", "dev")
MODELS_DIR = Path("/app/models")
WORK_DIR = Path("/runner/_work")


def get_health_status() -> str:
    """Check if runner is healthy."""
    # Check if runner process is running
    try:
        result = subprocess.run(
            ["pgrep", "-f", "Runner.Listener"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return "UP"
    except Exception:
        pass
    return "DOWN"


def get_models_info() -> Dict[str, Any]:
    """Get information about cached models."""
    info: Dict[str, Any] = {
        "total_models": 0,
        "total_size_mb": 0,
        "models": [],
    }

    if not MODELS_DIR.exists():
        return info

    try:
        for model_path in MODELS_DIR.rglob("*.bin"):
            size = model_path.stat().st_size / (1024 * 1024)  # MB
            info["total_models"] += 1
            info["total_size_mb"] += size
            info["models"].append(
                {
                    "name": model_path.name,
                    "path": str(model_path.relative_to(MODELS_DIR)),
                    "size_mb": round(size, 2),
                }
            )
    except Exception:
        pass

    info["total_size_mb"] = round(info["total_size_mb"], 2)
    return info


def get_build_info() -> Dict[str, Any]:
    """Get information about recent builds."""
    builds: list[Dict[str, Any]] = []

    if WORK_DIR.exists():
        try:
            for build_dir in sorted(WORK_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
                try:
                    stat = build_dir.stat()
                    builds.append(
                        {
                            "name": build_dir.name,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        }
                    )
                except Exception:
                    pass
        except Exception:
            pass

    return {"recent_builds": builds, "build_count": len(builds)}


def get_memory_info() -> Dict[str, Any]:
    """Get memory usage information."""
    try:
        # Try to read from /proc/meminfo
        with open("/proc/meminfo", "r") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    meminfo[parts[0].rstrip(":")] = int(parts[1])
            
            total_mb = meminfo.get("MemTotal", 0) / 1024
            available_mb = meminfo.get("MemAvailable", 0) / 1024
            used_mb = total_mb - available_mb
            
            return {
                "total_mb": round(total_mb, 2),
                "used_mb": round(used_mb, 2),
                "available_mb": round(available_mb, 2),
                "usage_percent": round((used_mb / total_mb * 100) if total_mb > 0 else 0, 2),
            }
    except Exception:
        pass
    
    return {}


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint - required by platform."""
    health_status = get_health_status()
    
    return jsonify({
        "status": health_status,
        "version": VERSION,
        "container": CONTAINER_NAME,
        "timestamp": datetime.utcnow().isoformat(),
    })


@app.route("/api/status", methods=["GET"])
def status():
    """Status endpoint with detailed information."""
    models_info = get_models_info()
    build_info = get_build_info()
    memory_info = get_memory_info()
    
    return jsonify({
        "status": get_health_status(),
        "version": VERSION,
        "container": CONTAINER_NAME,
        "memory": memory_info,
        "models": models_info,
        "builds": build_info,
        "available_endpoints": ["/health", "/api/status"],
        "timestamp": datetime.utcnow().isoformat(),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
