# This file contains all preprocessing functions
from scipy.signal import find_peaks, butter, lfilter, filtfilt, detrend


def butter_highpass(cutoff, fs, order=5):
    """
    Designs a high-pass Butterworth filter.

    Parameters:
    - cutoff: the cutoff frequency of the filter.
    - fs: the sampling rate of the signal.
    - order: the order of the filter.

    Returns:
    - b, a: numerator (b) and denominator (a) polynomials of the IIR filter.
    """
    nyq = 0.5 * fs  # Nyquist frequency
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return b, a


def butter_highpass_filter(data, cutoff, fs, order=5):
    """
    Applies a high-pass Butterworth filter to a signal.

    Parameters:
    - data: the input signal.
    - cutoff: the cutoff frequency of the filter.
    - fs: the sampling rate of the signal.
    - order: the order of the filter.

    Returns:
    - y: the filtered signal.
    """
    b, a = butter_highpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y


def butter_lowpass(cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return b, a


def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = filtfilt(b, a, data)
    return y


def decompose_eda_signal(eda_signal, fs):
    # Define cutoff frequencies for high-pass and low-pass filters
    lowcut_tonic = 0.1  # Low-pass filter cutoff frequency for tonic component - only frequencies below this can pass
    highcut_phasic = 0.1  # High-pass filter cutoff frequency for phasic component -> only frequencies above this range can pass

    # Extract tonic component using low-pass filter
    tonic = butter_lowpass_filter(eda_signal, lowcut_tonic, fs, order=5)

    # Extract phasic component using high-pass filter
    # Note: The phasic component is typically derived by subtracting the tonic from the original signal
    # or directly filtering the original/detrended signal with a high-pass filter.
    phasic = butter_highpass_filter(eda_signal, highcut_phasic, fs, order=5)

    return tonic, phasic


def normalize_signal(signal, baseline_period):
    baseline_value = baseline_period.mean()
    baseline_std = baseline_period.std()
    normalized_signal = (signal - baseline_value) / baseline_std

    return normalized_signal
