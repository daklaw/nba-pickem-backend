from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, team_selections, leagues, games, seasons, weeks, teams
import logging
import json
import time
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="API for NBA Pick'em Fantasy Game",
    version="1.0.0"
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Request/Response logging middleware
@app.middleware("http")
async def log_requests_responses(request: Request, call_next):
    start_time = time.time()

    # Log request
    request_body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body_bytes = await request.body()
            if body_bytes:
                request_body = body_bytes.decode()
                # Recreate request body for downstream handlers
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
        except Exception as e:
            logger.error(f"Error reading request body: {e}")

    logger.info(f"→ {request.method} {request.url.path}")
    if request_body:
        try:
            # Try to parse as JSON for pretty printing
            parsed = json.loads(request_body)
            logger.info(f"  Request body: {json.dumps(parsed, indent=2)}")
        except:
            logger.info(f"  Request body: {request_body}")

    # Process request
    response = await call_next(request)

    # Log response
    process_time = time.time() - start_time

    # Capture response body
    response_body = b""
    async for chunk in response.body_iterator:
        response_body += chunk

    # Log response details
    logger.info(f"← {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")

    if response_body:
        try:
            # Try to parse as JSON for pretty printing
            parsed = json.loads(response_body.decode())
            logger.info(f"  Response body: {json.dumps(parsed, indent=2)}")
        except:
            logger.info(f"  Response body: {response_body.decode()[:500]}")  # Limit to 500 chars

    # Return response with body
    return Response(
        content=response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type
    )


# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(team_selections.router)
app.include_router(seasons.router)
app.include_router(weeks.router)
app.include_router(leagues.router)
app.include_router(games.router)
app.include_router(teams.router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to NBA Pick'em API",
        "docs": "/docs",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
