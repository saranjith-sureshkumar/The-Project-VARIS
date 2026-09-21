"""VARIS Alert Queue — thread-safe Guardian → main thread communication."""
import queue

class AlertQueue:
    def __init__(self):
        self._q = queue.Queue(maxsize=50)  # Cap at 50 pending alerts

    def put_alert(self, msg: str):
        try:
            self._q.put_nowait(msg)
        except queue.Full:
            pass  # Drop oldest if queue full — don't block Guardian

    def get_alert(self) -> str | None:
        try:
            return self._q.get_nowait()
        except queue.Empty:
            return None

    def has_alerts(self) -> bool:
        return not self._q.empty()

    def flush(self) -> list:
        """Return all pending alerts at once."""
        alerts = []
        while True:
            a = self.get_alert()
            if a is None:
                break
            alerts.append(a)
        return alerts
