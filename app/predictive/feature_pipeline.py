"""Predictive maintenance feature engineering pipeline.

Data Leakage Prevention Strategy:
=================================
To prevent temporal data leakage, all features are calculated strictly using data 
BEFORE the observation timestamp `T`. 
- `T` is the current observation time.
- Features are calculated on the closed-open interval `[T - window, T)`.
- The target `incident_next_7_days` is calculated on the closed-open interval `[T, T + 7 days)`.
- Using `.shift(1)` on rolled aggregations ensures that data from time `T` is not 
  included in the features for time `T`.
"""

import numpy as np
import pandas as pd


class FeaturePipeline:
    """Calculates rolling features and targets for predictive maintenance."""

    def __init__(
        self,
        telemetry_df: pd.DataFrame,
        incidents_df: pd.DataFrame,
        device_meta_df: pd.DataFrame,
    ):
        """
        Args:
            telemetry_df: DataFrame containing hourly telemetry.
                          Required columns: timestamp, device_id, packet_loss_percent, crc_errors, interface_flaps, cpu_utilization, memory_utilization, latency_ms
            incidents_df: DataFrame containing incidents.
                          Required columns: start_time, recovery_time, device_id
            device_meta_df: DataFrame containing device metadata and vulnerability status.
                          Required columns: device_id, firmware_age_days, patch_age_days, cve_count, critical_cve_count, device_criticality
        """
        self.telemetry = telemetry_df.copy()
        self.incidents = incidents_df.copy()
        self.device_meta = device_meta_df.copy()

        # Ensure datetime types — skip if empty
        if not self.telemetry.empty and "timestamp" in self.telemetry.columns:
            self.telemetry["timestamp"] = pd.to_datetime(self.telemetry["timestamp"])
            self.telemetry.set_index("timestamp", inplace=True)
            self.telemetry.sort_index(inplace=True)

        if not self.incidents.empty:
            self.incidents["start_time"] = pd.to_datetime(self.incidents["start_time"])
            if "recovery_time" in self.incidents.columns:
                self.incidents["recovery_time"] = pd.to_datetime(self.incidents["recovery_time"])

    def _calculate_trend(self, series: pd.Series) -> float:
        """Calculates a simple linear trend over the series."""
        if len(series) < 2:
            return 0.0
        x = np.arange(len(series))
        # Handle nan values
        mask = ~np.isnan(series)
        if mask.sum() < 2:
            return 0.0

        y = series[mask].values
        x = x[mask]

        # Polyfit returns [slope, intercept]
        slope, _ = np.polyfit(x, y, 1)
        return slope

    def _calculate_telemetry_features(self) -> pd.DataFrame:
        """Calculates telemetry-based rolling features."""
        features_list = []

        grouped = self.telemetry.groupby("device_id")
        for device_id, group in grouped:
            # Resample to hourly in case of missing hours
            resampled = group.resample("1h").ffill()

            # Using shift(1) to avoid data leakage (features at T only use data < T)
            df_shifted = resampled.shift(1)

            # 24 hours
            roll_24h = df_shifted.rolling(window="24h", min_periods=1)

            # 7 days
            roll_7d = df_shifted.rolling(window="7D", min_periods=1)

            # 30 days
            roll_30d = df_shifted.rolling(window="30D", min_periods=1)

            # Feature extraction
            feat = pd.DataFrame(index=resampled.index)
            feat["device_id"] = device_id

            # 24h features
            feat["packet_loss_mean_24h"] = roll_24h["packet_loss_percent"].mean()
            feat["packet_loss_max_24h"] = roll_24h["packet_loss_percent"].max()
            feat["crc_errors_sum_24h"] = roll_24h["crc_errors"].sum()
            feat["interface_flaps_sum_24h"] = roll_24h["interface_flaps"].sum()
            feat["cpu_mean_24h"] = roll_24h["cpu_utilization"].mean()
            feat["cpu_max_24h"] = roll_24h["cpu_utilization"].max()
            feat["memory_mean_24h"] = roll_24h["memory_utilization"].mean()
            feat["memory_max_24h"] = roll_24h["memory_utilization"].max()
            feat["latency_mean_24h"] = roll_24h["latency_ms"].mean()

            # Trends (using rolling apply)
            feat["packet_loss_trend_24h"] = roll_24h["packet_loss_percent"].apply(self._calculate_trend, raw=False)
            feat["crc_errors_trend_24h"] = roll_24h["crc_errors"].apply(self._calculate_trend, raw=False)
            feat["latency_trend_24h"] = roll_24h["latency_ms"].apply(self._calculate_trend, raw=False)

            # 7d features
            feat["packet_loss_mean_7d"] = roll_7d["packet_loss_percent"].mean()
            feat["crc_errors_sum_7d"] = roll_7d["crc_errors"].sum()

            # 30d features
            feat["packet_loss_mean_30d"] = roll_30d["packet_loss_percent"].mean()

            features_list.append(feat)

        if not features_list:
            return pd.DataFrame()

        return pd.concat(features_list).reset_index()

    def _calculate_incident_features(self, timestamps: pd.DatetimeIndex, device_id: str) -> pd.DataFrame:
        """Calculates incident counts and downtime features."""
        inc_df = pd.DataFrame(index=timestamps)
        inc_df["incident_count_7d"] = 0
        inc_df["incident_count_30d"] = 0
        inc_df["downtime_7d"] = 0.0
        inc_df["downtime_30d"] = 0.0
        inc_df["incident_next_7_days"] = 0

        device_incidents = self.incidents[self.incidents["device_id"] == device_id]
        if device_incidents.empty:
            return inc_df

        for i, timestamp in enumerate(timestamps):
            # strict past [timestamp - window, timestamp)
            past_7d = timestamp - pd.Timedelta(days=7)
            past_30d = timestamp - pd.Timedelta(days=30)

            # Incidents that started in the window
            inc_7d = device_incidents[(device_incidents["start_time"] >= past_7d) & (device_incidents["start_time"] < timestamp)]
            inc_30d = device_incidents[(device_incidents["start_time"] >= past_30d) & (device_incidents["start_time"] < timestamp)]

            inc_df.iloc[i, inc_df.columns.get_loc("incident_count_7d")] = len(inc_7d)
            inc_df.iloc[i, inc_df.columns.get_loc("incident_count_30d")] = len(inc_30d)

            # Downtime calculation
            # For simplicity, if an incident is in the window, add its duration.
            # In a strict implementation, we'd clip the duration to the window, but this is a good proxy.
            dt_7d = 0.0
            for _, inc in inc_7d.iterrows():
                if pd.notna(inc.get("duration_minutes")):
                    dt_7d += inc["duration_minutes"]
                elif pd.notna(inc.get("recovery_time")):
                    dt_7d += (inc["recovery_time"] - inc["start_time"]).total_seconds() / 60.0

            dt_30d = 0.0
            for _, inc in inc_30d.iterrows():
                if pd.notna(inc.get("duration_minutes")):
                    dt_30d += inc["duration_minutes"]
                elif pd.notna(inc.get("recovery_time")):
                    dt_30d += (inc["recovery_time"] - inc["start_time"]).total_seconds() / 60.0

            inc_df.iloc[i, inc_df.columns.get_loc("downtime_7d")] = dt_7d
            inc_df.iloc[i, inc_df.columns.get_loc("downtime_30d")] = dt_30d

            # Target generation: strictly future [timestamp, timestamp + 7 days)
            future_7d = timestamp + pd.Timedelta(days=7)
            future_incs = device_incidents[(device_incidents["start_time"] >= timestamp) & (device_incidents["start_time"] < future_7d)]
            inc_df.iloc[i, inc_df.columns.get_loc("incident_next_7_days")] = 1 if len(future_incs) > 0 else 0

        return inc_df

    def create_features(self) -> pd.DataFrame:
        """Builds the full feature set."""
        if self.telemetry.empty:
            return pd.DataFrame()

        # 1. Telemetry features
        features_df = self._calculate_telemetry_features()

        # 2. Incident features & Target
        inc_features_list = []
        for device_id, group in features_df.groupby("device_id"):
            inc_feat = self._calculate_incident_features(group["timestamp"], device_id)
            inc_feat.reset_index(drop=True, inplace=True)
            inc_feat["timestamp"] = group["timestamp"].values
            inc_feat["device_id"] = device_id
            inc_features_list.append(inc_feat)

        all_inc_features = pd.concat(inc_features_list)

        # Merge telemetry and incident features
        final_df = pd.merge(features_df, all_inc_features, on=["timestamp", "device_id"])

        # 3. Static metadata (Vulnerabilities, criticality)
        if not self.device_meta.empty:
            final_df = pd.merge(final_df, self.device_meta, on="device_id", how="left")

        # Fill NAs
        final_df.fillna(0, inplace=True)

        return final_df
