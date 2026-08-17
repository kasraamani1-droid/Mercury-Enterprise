"""Program B – Enterprise Logistics (warehouse, stock, tools, purchasing)."""

__all__ = ["LogisticsService"]


def __getattr__(name: str):
    if name == "LogisticsService":
        from .service import LogisticsService

        return LogisticsService
    raise AttributeError(name)
