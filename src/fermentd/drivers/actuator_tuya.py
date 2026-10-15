"""Local Teckin / Tuya Smart Life plug via tinytuya. The device object is injectable."""

from __future__ import annotations

from typing import Any

from fermentd.drivers.base import ActuatorUnreachable


class TuyaPlug:
    def __init__(
        self,
        plug_id: str,
        device: Any,
        switch_dp: int = 1,
        countdown_dp: int | None = None,
    ) -> None:
        self.id = plug_id
        self._device = device
        self._switch_dp = switch_dp
        self._countdown_dp = countdown_dp
        # Seconds left on the plug's own countdown if its last status reported it. The Teckin SP10
        # firmware here does not include DP 11 in status, so this usually stays None.
        self.last_countdown: int | None = None

    def set(self, on: bool) -> None:
        try:
            result = (
                self._device.turn_on(switch=self._switch_dp)
                if on
                else self._device.turn_off(switch=self._switch_dp)
            )
        except Exception as exc:
            raise ActuatorUnreachable(str(exc)) from exc
        if isinstance(result, dict) and result.get("Error"):
            raise ActuatorUnreachable(str(result["Error"]))

    def read_state(self) -> bool | None:
        try:
            status = self._device.status()
        except Exception:
            return None
        if not isinstance(status, dict) or status.get("Error") or "dps" not in status:
            return None
        dps = status["dps"]
        if self._countdown_dp is not None:
            left = dps.get(str(self._countdown_dp), dps.get(self._countdown_dp))
            self.last_countdown = left if isinstance(left, int) and not isinstance(left, bool) else None
        value = dps.get(str(self._switch_dp), dps.get(self._switch_dp))
        if isinstance(value, bool):
            return value
        return None

    def supports_countdown(self) -> bool:
        return self._countdown_dp is not None

    def arm_countdown(self, seconds: int) -> bool:
        """Set the plug's hardware off-timer. Returns True when the plug echoed the new value back
        (its acknowledgement), False when it answered without echoing it. Raises on an error."""
        if self._countdown_dp is None:
            return False
        try:
            result = self._device.set_value(self._countdown_dp, seconds)
        except Exception as exc:
            raise ActuatorUnreachable(str(exc)) from exc
        if not isinstance(result, dict):
            return False
        if result.get("Error"):
            raise ActuatorUnreachable(str(result["Error"]))
        dps = result.get("dps") or {}
        echoed = dps.get(str(self._countdown_dp), dps.get(self._countdown_dp))
        return echoed == seconds

    def close(self) -> None:
        close = getattr(self._device, "close", None)
        if close is not None:
            close()


def outlet_device(device_id: str, ip: str, local_key: str, version: str) -> Any:
    import tinytuya

    device = tinytuya.OutletDevice(device_id, ip, local_key, version=float(version))
    device.set_socketTimeout(3)
    return device
