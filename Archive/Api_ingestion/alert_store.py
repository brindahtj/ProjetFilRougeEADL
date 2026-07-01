from typing import Dict, List, Optional

from Archive.Api_ingestion.alert_models import Alert, AlertCreate, AlertUpdate


class AlertStore:
    def __init__(self):
        self._alerts: Dict[int, Alert] = {}
        self._next_id: int = 1

    def list(self) -> List[Alert]:
        return list(self._alerts.values())

    def get(self, alert_id: int) -> Optional[Alert]:
        return self._alerts.get(alert_id)

    def create(self, data: AlertCreate) -> Alert:
        alert = Alert(id=self._next_id, **data.model_dump())
        self._alerts[self._next_id] = alert
        self._next_id += 1
        return alert

    def update(self, alert_id: int, data: AlertUpdate) -> Optional[Alert]:
        current = self._alerts.get(alert_id)
        if not current:
            return None

        updated_data = current.model_dump()
        for key, value in data.model_dump(exclude_unset=True).items():
            updated_data[key] = value

        updated = Alert(**updated_data)
        self._alerts[alert_id] = updated
        return updated

    def delete(self, alert_id: int) -> bool:
        if alert_id in self._alerts:
            del self._alerts[alert_id]
            return True
        return False