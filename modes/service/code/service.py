"""Custom service mode for ME2 with formatted strings."""
from functools import partial

from typing import List
from mpf.modes.service.code.service import Service as BaseService, ServiceMenuEntry


class Service(BaseService):

    """Class override for MPF Service class to modify button handlers with toggle state."""

    # Adjustments
    def _load_adjustments_menu_entries(self) -> List[ServiceMenuEntry]:
        """Return the adjustments menu items with label and callback."""
        return [
            ServiceMenuEntry("Standard\nAdjustments", partial(self._settings_menu, "standard")),
            ServiceMenuEntry("Feature\nAdjustments", partial(self._settings_menu, "feature")),
            ServiceMenuEntry("Game\nAdjustments", partial(self._settings_menu, "game")),
            ServiceMenuEntry("Coin\nAdjustments", partial(self._settings_menu, "coin")),
        ]
