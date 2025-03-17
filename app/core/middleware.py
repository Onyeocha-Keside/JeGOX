from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.error_handler import (
    APIError,
    ErrorLogging,
    error_handler,
    cleanup_handler
)
from app.core.logger import logger
import time
from typing import Callable
import sys
import traceback

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        try:
            # Add request ID
            request_id = str(time.time())
            request.state.request_id = request_id
            
            # Process request
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Get full traceback
            exc_info = sys.exc_info()
            traceback_str = ''.join(traceback.format_exception(*exc_info))
            
            # Log error with full context
            await ErrorLogging.log_error(
                error=e,
                request=request,
                context={
                    "traceback": traceback_str,
                    "request_id": request.state.request_id
                }
            )
            
            # Cleanup
            await cleanup_handler(e)
            
            # Handle error
            return await error_handler(request, e)

class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        # Add timing information
        request.state.start_time = time.time()
        
        # Add request context
        context = {
            "request_id": str(time.time()),
            "client_ip": request.client.host,
            "path": request.url.path,
            "method": request.method
        }
        request.state.context = context
        
        try:
            response = await call_next(request)
            
            # Log successful request
            process_time = time.time() - request.state.start_time
            logger.info(
                f"Request completed",
                extra={
                    **context,
                    "process_time": process_time,
                    "status_code": response.status_code
                }
            )
            
            return response
            
        except Exception as e:
            # Log failed request
            process_time = time.time() - request.state.start_time
            logger.error(
                f"Request failed",
                extra={
                    **context,
                    "process_time": process_time,
                    "error": str(e)
                }
            )
            raise