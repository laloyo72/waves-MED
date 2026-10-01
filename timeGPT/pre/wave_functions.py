import numpy as np

def welch_periodogram(signal, dt, n_fft, segment_length=None, overlap=0.5):
    """Estimate a one-sided Welch periodogram with Hann-windowed segments.

    The returned values are energy per frequency bin, not density. Therefore
    their sum estimates signal variance and they remain compatible with the
    existing ``wave_parameters`` calculation.
    """
    signal = np.asarray(signal, dtype=float)
    if signal.ndim != 1 or signal.size < 2:
        raise ValueError("signal must be one-dimensional with at least two samples")
    if not 0 <= overlap < 1:
        raise ValueError("overlap must be in the interval [0, 1)")

    if segment_length is None:
        segment_length = min(4096, signal.size)
    segment_length = int(segment_length)
    if not 2 <= segment_length <= signal.size:
        raise ValueError("segment_length must be between 2 and signal length")
    if n_fft < segment_length:
        raise ValueError("n_fft must be at least segment_length")

    step = max(1, int(round(segment_length * (1.0 - overlap))))
    window = np.hanning(segment_length)
    sample_frequency = 1.0 / dt
    window_power = np.sum(window ** 2)
    spectra = []
    for start in range(0, signal.size - segment_length + 1, step):
        segment = signal[start:start + segment_length]
        transform = np.fft.rfft((segment - segment.mean()) * window, n=n_fft)
        spectra.append(np.abs(transform) ** 2 / (sample_frequency * window_power))

    psd = np.mean(spectra, axis=0)
    if psd.size > 2:
        # One-sided PSD: do not double DC or the Nyquist bin.
        psd[1:-1] *= 2.0
    frequency = np.fft.rfftfreq(n_fft, d=dt)
    return frequency, psd * (sample_frequency / n_fft)
