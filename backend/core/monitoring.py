import logging
from fastapi import Request

# Setup logging for the application

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

# Request logging middleware
async def log_request_middleware(request: Request, call_next):
    logger = logging.getLogger("request")
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response 