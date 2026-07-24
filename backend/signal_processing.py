import numpy as np
from scipy.signal import butter, filtfilt, detrend, find_peaks, welch
from typing import Tuple

class SignalProcessor:
    """
    The Alchemy of Signals: Transforms raw green channel intensity into vital signs.
    Implements a precise DSP pipeline for rPPG.
    """
    def __init__(self, fps: float = 120.0, buffer_size: int = 7200):
        self.fps = fps
        self.buffer_size = buffer_size
        self.signal_buffer = []
        self.sample_times = []
        self.sample_reliability = []
        self.last_bpm = 0.0
        self.last_rr = 0.0
        self.last_quality = 0

    def add_sample(self, sample: float, timestamp: float | None = None, reliability: float = 1.0):
        """Adds a new green channel sample to the rolling buffer."""
        if not np.isfinite(sample):
            return
        timestamp = float(timestamp) if timestamp is not None else None
        self.signal_buffer.append(sample)
        self.sample_times.append(timestamp)
        self.sample_reliability.append(float(min(1.0, max(0.0, reliability))))
        if len(self.signal_buffer) > self.buffer_size:
            self.signal_buffer.pop(0)
            self.sample_times.pop(0)
            self.sample_reliability.pop(0)

    def _effective_fps(self) -> float:
        times = np.array([t for t in self.sample_times if t is not None], dtype=float)
        if len(times) < 8:
            return self.fps

        intervals = np.diff(times)
        intervals = intervals[(intervals > 0.005) & (intervals < 0.5)]
        if len(intervals) < 4:
            return self.fps

        median_interval = float(np.median(intervals))
        if median_interval <= 0:
            return self.fps

        return float(min(120.0, max(15.0, 1.0 / median_interval)))

    def _uniform_signal(self, fps: float) -> Tuple[np.ndarray, float]:
        sig = np.array(self.signal_buffer, dtype=float)
        times = np.array(self.sample_times, dtype=object)
        valid_time_count = sum(t is not None for t in self.sample_times)

        if valid_time_count < max(8, int(len(sig) * 0.7)):
            return sig, len(sig) / max(fps, 1.0)

        numeric_times = np.array([float(t) for t in times], dtype=float)
        numeric_times -= numeric_times[0]
        duration = float(numeric_times[-1] - numeric_times[0])
        if duration < 5.0:
            return sig, duration

        target_count = max(2, int(duration * fps))
        uniform_times = np.linspace(0.0, duration, target_count)
        return np.interp(uniform_times, numeric_times, sig), duration

    def _reject_outliers(self, sig: np.ndarray) -> np.ndarray:
        median = np.median(sig)
        mad = np.median(np.abs(sig - median)) + 1e-8
        robust_z = 0.6745 * (sig - median) / mad
        cleaned = sig.copy()
        outliers = np.abs(robust_z) > 5.0
        cleaned[outliers] = median
        return cleaned

    def _bandpass_filter(self, sig: np.ndarray, low_hz: float, high_hz: float, fps: float, order: int = 4) -> np.ndarray:
        nyquist = 0.5 * fps
        if nyquist <= low_hz:
            return sig
        high_hz = min(high_hz, nyquist * 0.95)
        low = low_hz / nyquist
        high = high_hz / nyquist
        b, a = butter(order, [low, high], btype='band')
        padlen = 3 * (max(len(a), len(b)) - 1)
        if len(sig) <= padlen:
            return sig
        return filtfilt(b, a, sig)

    def _autocorrelation_bpm(self, sig: np.ndarray, fps: float) -> float:
        corr = np.correlate(sig, sig, mode='full')[len(sig) - 1:]
        corr /= np.max(np.abs(corr)) + 1e-8
        min_lag = int(fps / 3.7)
        max_lag = int(fps / 0.75)
        peaks, properties = find_peaks(corr, height=0.12, distance=int(fps * 0.3))
        peaks = [p for p in peaks if min_lag <= p <= max_lag]
        if not peaks:
            return 0.0
        best_peak = max(peaks, key=lambda p: corr[p])
        period = best_peak / fps
        bpm = 60.0 / period if period > 0 else 0.0
        return bpm if 45.0 <= bpm <= 220.0 else 0.0

    def _spectral_peak(self, sig: np.ndarray, fps: float, low_hz: float, high_hz: float) -> Tuple[float, float, float]:
        nperseg = min(len(sig), max(256, int(fps * 16)))
        freqs, power = welch(sig, fs=fps, nperseg=nperseg, noverlap=nperseg // 2)
        mask = (freqs >= low_hz) & (freqs <= high_hz)
        if not np.any(mask):
            return 0.0, 0.0, 0.0

        band_freqs = freqs[mask]
        band_power = power[mask]
        peak_idx = int(np.argmax(band_power))
        peak_power = float(band_power[peak_idx])
        median_power = float(np.median(band_power) + 1e-10)
        return float(band_freqs[peak_idx]), peak_power, peak_power / median_power

    def process(self) -> Tuple[float, float, np.ndarray, int]:
        """
        Executes the complete DSP pipeline.
        Returns: (bpm, respiration_rate, filtered_signal, quality)
        """
        effective_fps = self._effective_fps()
        min_duration = 30.0
        min_samples = max(360, int(effective_fps * min_duration))
        if len(self.signal_buffer) < min(360, min_samples):
            return 0.0, 0.0, np.array(self.signal_buffer), 0

        sig, duration = self._uniform_signal(effective_fps)
        if duration < min_duration or len(sig) < min_samples:
            return 0.0, 0.0, sig, 0

        sig = self._reject_outliers(sig)
        sig = detrend(sig)
        sig -= np.mean(sig)
        sig /= np.std(sig) + 1e-8

        filtered = self._bandpass_filter(sig, 0.8, 3.5, effective_fps)
        spectrum_signal = filtered * np.hamming(len(filtered))
        fft_vals = np.abs(np.fft.rfft(spectrum_signal))
        freqs = np.fft.rfftfreq(len(spectrum_signal), 1.0 / effective_fps)

        hr_mask = (freqs >= 0.8) & (freqs <= 3.5)
        if not np.any(hr_mask):
            return 0.0, 0.0, filtered, 0

        target_freqs = freqs[hr_mask]
        target_vals = fft_vals[hr_mask]
        peak_idx = int(np.argmax(target_vals))
        bpm_fft = target_freqs[peak_idx] * 60.0

        bpm_ac = self._autocorrelation_bpm(filtered, effective_fps)
        bpm_welch_freq, hr_peak_power, hr_prominence = self._spectral_peak(filtered, effective_fps, 0.8, 3.5)
        bpm_welch = bpm_welch_freq * 60.0

        estimates = [value for value in [bpm_fft, bpm_ac, bpm_welch] if 45.0 <= value <= 220.0]
        if len(estimates) >= 2 and (max(estimates) - min(estimates)) <= 8.0:
            bpm = float(np.median(estimates))
        elif len(estimates) >= 2 and (max(estimates) - min(estimates)) <= 14.0:
            bpm = float(np.mean(estimates))
        else:
            bpm = bpm_welch if bpm_welch > 0 else (bpm_ac if bpm_ac > 0 else bpm_fft)

        if bpm < 45.0 or bpm > 220.0:
            bpm = 0.0

        respiration_signal = self._bandpass_filter(sig, 0.12, 0.45, effective_fps, order=2)
        rr_freq, rr_peak_power, rr_prominence = self._spectral_peak(respiration_signal, effective_fps, 0.12, 0.45)
        rr = 0.0
        rr_candidate = rr_freq * 60.0
        if 6.0 <= rr_candidate <= 40.0:
            rr = rr_candidate

        noise_idxs = (freqs >= 0.2) & (freqs <= 5.0) & ~hr_mask
        noise_power = np.mean(fft_vals[noise_idxs]) if np.any(noise_idxs) else 0.0
        snr = hr_peak_power / (noise_power + 1e-8)
        reliability = float(np.mean(self.sample_reliability[-len(self.signal_buffer):])) if self.sample_reliability else 1.0
        agreement_penalty = 0
        if len(estimates) < 2:
            agreement_penalty = 25
        elif max(estimates) - min(estimates) > 12:
            agreement_penalty = 15

        quality = int(min(100, max(0, (snr - 1.2) * 18 + hr_prominence * 5 + reliability * 25)))
        quality -= agreement_penalty
        quality = int(min(100, max(0, quality)))
        if duration < 45.0:
            quality = max(0, quality - 12)
        if bpm == 0.0:
            quality = min(quality, 35)
        if rr == 0.0:
            quality = min(quality, 55)
        if rr_prominence < 2.5:
            quality = min(quality, 70)

        bpm = self.get_smoothed_value(bpm, self.last_bpm, alpha=0.15)
        rr = self.get_smoothed_value(rr, self.last_rr, alpha=0.10)
        self.last_bpm = bpm
        self.last_rr = rr
        self.last_quality = quality

        return float(round(bpm, 2)), float(round(rr, 2)), filtered, quality

    def get_smoothed_value(self, new_value: float, prev_value: float, alpha: float = 0.2) -> float:
        """Simple EMA filter to prevent measurement jumps."""
        if prev_value == 0 or new_value == 0:
            return new_value
        return alpha * new_value + (1 - alpha) * prev_value
