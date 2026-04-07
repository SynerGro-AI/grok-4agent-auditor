"""
grok_auditor — Grok XAI 4-Agent Code Project Auditor.

Transforms basic code into enterprise-level software by coordinating four
specialised AI agents powered by the xAI Grok API (with optional CUDA/GPU
acceleration for local pre-processing steps).
"""

from grok_auditor.core.config import AuditorConfig
from grok_auditor.core.orchestrator import AuditOrchestrator, AuditReport

__all__ = ["AuditorConfig", "AuditOrchestrator", "AuditReport"]
__version__ = "1.0.0"
