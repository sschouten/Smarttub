"""Platform for lock integration (spa control locks)."""

from typing import Any, override

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from smarttub import Spa

from .controller import SmartTubConfigEntry
from .entity import SmartTubEntity

PARALLEL_UPDATES = 0

# lock kinds reported by the spa; temperature and spa lock are the common ones
# (as in the SmartTub app), the others are disabled by default
DEFAULT_ENABLED_LOCKS = {"temperature", "spa"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: SmartTubConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up lock entities for the locks the spa reports."""
    controller = entry.runtime_data
    entities = []
    for spa in controller.spas:
        locks = controller.coordinator.data[spa.id]["status"].locks or {}
        entities.extend(
            SmartTubLock(controller.coordinator, spa, kind)
            for kind, lock in locks.items()
            if lock.state is not None
        )
    async_add_entities(entities)


class SmartTubLock(SmartTubEntity, LockEntity):
    """A control lock of the spa (temperature, spa, access, maintenance)."""

    def __init__(
        self, coordinator: DataUpdateCoordinator[dict[str, Any]], spa: Spa, kind: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, spa, f"lock_{kind}")
        self.kind = kind
        self._attr_translation_key = f"lock_{kind}"
        self._attr_entity_registry_enabled_default = kind in DEFAULT_ENABLED_LOCKS

    @property
    def _lock(self):
        locks = self.spa_status.locks or {}
        return locks.get(self.kind)

    @property
    @override
    def available(self) -> bool:
        """Return False when the spa no longer reports this lock."""
        return super().available and self._lock is not None

    @property
    @override
    def is_locked(self) -> bool | None:
        """Return True if the lock is engaged."""
        if "is_locked" in self._optimistic:
            return self._optimistic["is_locked"]
        lock = self._lock
        if lock is None or lock.state is None:
            return None
        return lock.state == "LOCKED"

    @override
    async def async_lock(self, **kwargs: Any) -> None:
        """Engage the lock."""
        await self.controller.async_command(self._lock.lock(), f"lock {self.kind}")
        # the API does not confirm lock changes: keep the target state until a
        # later poll shows it (or the optimistic hold expires)
        self._set_optimistic(False, is_locked=True)

    @override
    async def async_unlock(self, **kwargs: Any) -> None:
        """Release the lock."""
        await self.controller.async_command(self._lock.unlock(), f"unlock {self.kind}")
        self._set_optimistic(False, is_locked=False)
