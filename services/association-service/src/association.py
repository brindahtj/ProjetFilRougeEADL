from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .models import PollutionMeasurement, TrafficMeasurement, AssociatedData
from statistics import mean
import logging

log = logging.getLogger("association")

class AssociationEngine:
    """Associe pollution et trafic par zone et fenêtre temporelle."""

    def __init__(self, time_window_minutes: int = 5):
        self.time_window = timedelta(minutes=time_window_minutes)

    def associate_by_zone_and_time(
        self,
        pollution: List[dict],
        traffic: List[dict]
    ) -> List[AssociatedData]:
        """
        Associe mesures pollution et trafic par zone et fenêtre temporelle.

        Stratégie :
        - Grouper par city + zone + time_window (ex: 14:00-14:05)
        - Pour chaque groupe, calculer moyennes pollution/trafic
        - Retourner associations complètes
        """
        associations = []

        # Convertir en objets typisés
        pollution_readings = [
            PollutionMeasurement(**p) for p in pollution
            if isinstance(p, dict)
        ]
        traffic_readings = [
            TrafficMeasurement(**t) for t in traffic
            if isinstance(t, dict)
        ]

        # Grouper par (city, zone, time_bucket)
        pollution_by_bucket = self._group_by_zone_time(pollution_readings)
        traffic_by_bucket = self._group_by_zone_time(traffic_readings)

        # Associer
        for bucket_key, poll_data in pollution_by_bucket.items():
            if bucket_key in traffic_by_bucket:
                traf_data = traffic_by_bucket[bucket_key]
                city, zone, time_window = bucket_key

                poll_values = [p.value for p in poll_data]
                traf_values = [t.q for t in traf_data]

                association = AssociatedData(
                    city=city,
                    zone=zone,
                    pollution_count=len(poll_data),
                    traffic_count=len(traf_data),
                    pollution_avg=mean(poll_values),
                    traffic_avg=mean(traf_values),
                    time_window=time_window,
                    timestamp=datetime.utcnow()
                )
                associations.append(association)
                log.info(
                    "Associated: %s/%s - poll_avg=%.2f, traf_avg=%.2f",
                    city, zone, association.pollution_avg, association.traffic_avg
                )

        return associations

    def _group_by_zone_time(self, readings: List) -> Dict:
        """Groupe les lectures par (city, zone, time_bucket)."""
        grouped = {}

        for reading in readings:
            city = reading.city
            zone = reading.zone or "unknown"
            # Arrondir au time_window
            ts = reading.timestamp
            bucket_minute = (ts.hour * 60 + ts.minute) // self.time_window.total_seconds() // 60 * self.time_window.total_seconds() // 60
            time_bucket = f"{ts.hour:02d}:{bucket_minute:02d}"

            key = (city, zone, time_bucket)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(reading)

        return grouped