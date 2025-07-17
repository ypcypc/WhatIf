"""
FastAPI middleware configuration.

Sets up CORS, logging, error handling, and other middleware.
"""

import logging
import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend_services.app.core.config import settings


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware for the FastAPI application."""
    
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_origins,
        allow_credentials=settings.allow_credentials,
        allow_methods=settings.allow_methods,
        allow_headers=settings.allow_headers,
    )
    
    # Request Timing Middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Logging Middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        # 使用标准的 logger 而不是 uvicorn.access
        logger = logging.getLogger("whatif.requests")
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        # 修复日志记录格式问题 - 使用标准的 logger
        logger.info(
            "%s %s - Status: %s - Time: %.4fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time
        )
        
        return response
    
    # Exception Handlers
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.detail, "status_code": exc.status_code}
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"error": "Validation Error", "details": exc.errors()}
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger = logging.getLogger("uvicorn.error")
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        ) 