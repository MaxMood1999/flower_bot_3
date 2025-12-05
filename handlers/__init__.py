from handlers.user import router as user_router
from handlers.admin import router as admin_router
from handlers.auction import router as auction_router

__all__ = ["user_router", "admin_router", "auction_router"]
