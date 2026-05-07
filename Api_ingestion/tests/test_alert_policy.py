from contracts import AirQualityAlertEvent


class AlertPolicy:

    def __init__(
        self,
        threshold: float = 80,
        consecutive_count: int = 2
    ):
        self.threshold = threshold
        self.consecutive_count = consecutive_count

    def should_alert(self, values: list[float]) -> bool:

        if len(values) < self.consecutive_count:
            return False

        last_values = values[-self.consecutive_count:]

        return all(v > self.threshold for v in last_values)

    def create_alert_if_needed(
        self,
        city: str,
        pollutant: str,
        values: list[float],
    ):

        if not self.should_alert(values):
            return None

        return AirQualityAlertEvent.create(
            city=city,
            pollutant=pollutant,
            value=values[-1],
            threshold=self.threshold,
        )