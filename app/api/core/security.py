from typing import Optional
import re
from fastapi import Request, HTTPException
from app.config import get_settings
from app.core.logger import logger
from jose import JWEError, JWT
import time

settings = get_settings()

class SecurityManager:
    def __init__(self):
        self._request_counts = {}
        self._last_cleanup = time.time()
        
    async def validate_input(self, text: str) -> bool:
        """
        Validate user input for potential security issues.
        Returns True if input is safe, False otherwise.
        """
        if not text or len(text) > 1000:  # Adjust max length as needed
            return False
            
        # Check for common injection patterns
        dangerous_patterns = [
            r"{{.*}}",              # Template injection
            r"<script.*?>",         # XSS attempts
            r"(?i)system\(",        # System command attempts
            r"(?i)exec\(",          # Code execution attempts
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text):
                logger.warning(f"Potentially dangerous input detected: {text}")
                return False
                
        return True
        
    def encrypt_conversation(self, conversation: str) -> str:
        """Encrypt conversation data."""
        try:
            encrypted = JWT().encrypt(
                conversation,
                settings.ENCRYPTION_KEY,
                algorithm='dir',
                encryption_algorithm='A256GCM'
            )
            return encrypted
        except JWEError as e:
            logger.error(f"Encryption error: {e}")
            raise HTTPException(status_code=500, detail="Error encrypting conversation")
            
    def decrypt_conversation(self, encrypted_data: str) -> str:
        """Decrypt conversation data."""
        try:
            decrypted = JWT().decrypt(
                encrypted_data,
                settings.ENCRYPTION_KEY
            )
            return decrypted
        except JWEError as e:
            logger.error(f"Decryption error: {e}")
            raise HTTPException(status_code=500, detail="Error decrypting conversation")
            
    async def check_rate_limit(self, request: Request) -> bool:
        """
        Implement rate limiting.
        Returns True if request is allowed, False if rate limit exceeded.
        """
        client_ip = request.client.host
        current_time = time.time()
        
        # Cleanup old entries every minute
        if current_time - self._last_cleanup > 60:
            self._cleanup_old_requests()
            self._last_cleanup = current_time
            
        # Initialize or update request count
        if client_ip not in self._request_counts:
            self._request_counts[client_ip] = []
            
        self._request_counts[client_ip].append(current_time)
        
        # Check if rate limit exceeded
        recent_requests = [t for t in self._request_counts[client_ip] 
                         if current_time - t < 60]
        self._request_counts[client_ip] = recent_requests
        
        return len(recent_requests) <= settings.MAX_REQUESTS_PER_MINUTE
        
    def _cleanup_old_requests(self):
        """Remove old request counts."""
        current_time = time.time()
        for ip in list(self._request_counts.keys()):
            self._request_counts[ip] = [t for t in self._request_counts[ip] 
                                      if current_time - t < 60]
            if not self._request_counts[ip]:
                del self._request_counts[ip]

security_manager = SecurityManager()