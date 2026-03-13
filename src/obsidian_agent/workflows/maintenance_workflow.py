"""Maintenance workflow."""

from obsidian_agent.services.maintenance_service import MaintenanceService


class MaintenanceWorkflow:
    """Facade for maintenance tasks."""

    def __init__(self, maintenance_service: MaintenanceService) -> None:
        self.maintenance_service = maintenance_service

    async def weekly_digest(self, week_key: str) -> str:
        return await self.maintenance_service.generate_weekly_digest(week_key)
