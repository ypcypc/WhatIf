"""
Anchor Service Module

This module provides functionality for extracting text segments based on anchor points.
It follows a four-layer architecture: Models → Repository → Service → Router.
"""

from .models import Anchor, AssembleRequest, Span, AssembleResponse
from .repositories import AnchorRepository
from .services import AnchorService
from .routers import router

__all__ = [
    "Anchor",
    "AssembleRequest", 
    "Span",
    "AssembleResponse",
    "AnchorRepository",
    "AnchorService", 
    "router"
] 