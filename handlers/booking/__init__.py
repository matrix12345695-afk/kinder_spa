
from aiogram import Router
from .start import router as start_router
from .form import router as form_router

router = Router()
router.include_router(start_router)
router.include_router(form_router)
