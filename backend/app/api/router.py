from fastapi import APIRouter

from app.api.routes import auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")  # US01

# Register other feature routers here, e.g.:
# api_router.include_router(cv.router, prefix="/cv")       # US03 / US05
# api_router.include_router(offers.router, prefix="/offers")  # US08 / US09
