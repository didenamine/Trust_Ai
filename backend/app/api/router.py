from fastapi import APIRouter

from app.api.routes import adaptations, ats, auth, cv, health, matching, offers, profile

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")  # US01
api_router.include_router(cv.router, prefix="/cv")  # US03 / US05
api_router.include_router(ats.router, prefix="/ats")  # US24
api_router.include_router(profile.router, prefix="/profile")  # T-09 / US06 / US07
api_router.include_router(offers.router, prefix="/offers")  # US08 / US09
api_router.include_router(matching.router, prefix="/matching")  # US12 / US13
api_router.include_router(adaptations.router, prefix="/adaptations")  # US14
