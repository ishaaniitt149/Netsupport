"""Service for managing incident resolutions and computing KPIs."""

from pathlib import Path

import pandas as pd

from app.models.resolution import KPIReport, Resolution


class ResolutionService:
    def __init__(self, parquet_path: Path):
        self.parquet_path = parquet_path
        self._resolutions: dict[str, Resolution] = {}
        self._load()

    def _load(self):
        if self.parquet_path.exists():
            try:
                df = pd.read_parquet(self.parquet_path)
                for _, row in df.iterrows():
                    res = Resolution(**row.to_dict())
                    self._resolutions[res.incident_id] = res
            except Exception:
                self._resolutions = {}
        else:
            self._resolutions = {}

    def _save(self):
        self.parquet_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._resolutions:
            return

        df = pd.DataFrame([res.model_dump() for res in self._resolutions.values()])
        df.to_parquet(self.parquet_path, engine="pyarrow")

    def create_resolution(self, resolution: Resolution) -> Resolution:
        if resolution.incident_id in self._resolutions:
            raise ValueError(f"Resolution for incident {resolution.incident_id} already exists.")
        self._resolutions[resolution.incident_id] = resolution
        self._save()
        return resolution

    def get_resolution(self, incident_id: str) -> Resolution | None:
        return self._resolutions.get(incident_id)

    def update_resolution(self, incident_id: str, updates: dict) -> Resolution | None:
        res = self.get_resolution(incident_id)
        if not res:
            return None

        updated_data = res.model_dump()
        updated_data.update(updates)
        new_res = Resolution(**updated_data)

        self._resolutions[incident_id] = new_res
        self._save()
        return new_res

    def calculate_kpis(self, incidents_df: pd.DataFrame) -> KPIReport:
        """Calculate MTTA, MTTD, MTTR, and FTR Rate based on incidents and resolutions."""
        total_incidents = len(incidents_df)
        if total_incidents == 0:
            return KPIReport(total_incidents=0, mtta_minutes=0.0, mttd_minutes=0.0, mttr_minutes=0.0, ftr_rate=0.0)

        mtta_list = []
        mttd_list = []
        mttr_list = []
        ftr_count = 0
        resolved_count = 0

        for _, inc in incidents_df.iterrows():
            inc_id = inc["incident_id"]
            start_time = inc["start_time"]

            res = self.get_resolution(inc_id)
            if res:
                resolved_count += 1

                # Acknowledge time (MTTA)
                ack_diff = (res.acknowledged_at - start_time).total_seconds() / 60.0
                mtta_list.append(max(0.0, ack_diff))

                # Diagnose time (MTTD) from acknowledge to diagnosed
                diag_diff = (res.diagnosed_at - res.acknowledged_at).total_seconds() / 60.0
                mttd_list.append(max(0.0, diag_diff))

                # Resolve time (MTTR) from start to resolution
                res_diff = (res.resolution_timestamp - start_time).total_seconds() / 60.0
                mttr_list.append(max(0.0, res_diff))

                if res.first_time_resolution:
                    ftr_count += 1

        avg_mtta = sum(mtta_list) / len(mtta_list) if mtta_list else 0.0
        avg_mttd = sum(mttd_list) / len(mttd_list) if mttd_list else 0.0
        avg_mttr = sum(mttr_list) / len(mttr_list) if mttr_list else 0.0
        ftr_rate = (ftr_count / resolved_count * 100.0) if resolved_count > 0 else 0.0

        return KPIReport(
            total_incidents=total_incidents,
            mtta_minutes=round(avg_mtta, 2),
            mttd_minutes=round(avg_mttd, 2),
            mttr_minutes=round(avg_mttr, 2),
            ftr_rate=round(ftr_rate, 2)
        )
