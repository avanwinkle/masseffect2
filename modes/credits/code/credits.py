"""Contains the custom Credit (coin play) mode code."""

from mpf.modes.credits.code.credits import Credits as CreditsBase


class Credits(CreditsBase):

    """Custom credits mode with lifetime values."""

    def _audit(self, value, audit_class, key_name=None):
        seven = '7 Lifetime Earnings ' + audit_class
        if seven not in self.earnings:
            self.earnings[seven] = value
        else:
            self.earnings[seven] += value
        super()._audit(value, audit_class, key_name)

    def _player_added(self, **kwargs):
        super()._player_added(**kwargs)
        if not self.machine.settings.get_setting_value('free_play'):
            self._audit_increment_non_coin(1, audit_class='8 Lifetime Paid Games')

    def _reset_earnings(self, **kwargs):
        """Override Reset earnings to preserve lifetime values."""
        del kwargs
        # Guarantee a log regardless of configured log level
        self.log.log(10000, "Resetting all earnings.", **self.earnings)
        # Persist lifetime earnings even after a reset
        self.earnings = {k: self.earnings[k] for k in self.earnings.keys() if "Lifetime" in k}
        self.data_manager.save_all(data=self.earnings)