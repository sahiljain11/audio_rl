import numpy as np
from numpy.typing import NDArray
import librosa



class ProsodyHandler():
    def loudness_raw(audio: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Computes audio array in absolute values.
        :param audio: audio array
        :return: absolute values of audio array
        """
        return np.abs(audio)

    def max_loudness(audio: NDArray[np.float64]) -> float:
        """
        Computes maximum loudness of absolute audio array.
        :param audio: audio array
        :return: maximum loudness of audio array
        """
        return np.max(np.abs(audio))
       

    def mean_loudness(audio: NDArray[np.float64]) -> float:
        """
        Computes mean loudness of absolute audio array.
        :param audio: audio array
        :return: mean loudness of audio array
        """
        return np.mean(np.abs(audio))
        
    def max_pitch(audio: NDArray[np.float64]) -> float:
        """
        Computes maximum pitch of audio array.
        :param audio: audio array
        :return: maximum pitch of audio array
        """
        f0 = librosa.yin(audio, fmin=80, fmax=300)
        return np.max(f0) 

    def max_pitch2(audio: NDArray[np.float64]) -> float:
        """
        Computes maximum pitch of audio array. Second version.
        :param audio: audio array
        :return: maximum pitch of audio array
        """
        pitch = librosa.piptrack(y=audio, fmin=80, fmax=300)
        return np.max(pitch) 

    def mean_pitch(audio: NDArray[np.float64]) -> float:
        """
        Computes mean pitch of audio array.
        :param audio: audio array
        :return: mean pitch of audio array
        """
        f0 = librosa.yin(audio, fmin=80, fmax=300)
        return np.mean(f0)

    def pitch_raw(audio: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Computes raw pitch array of audio array
        :param audio: audio array
        :return: raw pitch array of audio array
        """
        f0 = librosa.yin(audio, fmin=80, fmax=300) # or 50 and 500?
        return f0
        
    def max_energy(audio: NDArray[np.float64]) -> float:
        """
        Computes maximum energy of audio array.
        :param audio: audio array
        :return: maximum energy of audio array
        """
        return np.max(audio ** 2)

    def energy_raw(audio: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Computes raw energy array of audio array.
        :param audio: audio array
        :return: raw energy array 
        """
        return audio ** 2

    def mean_energy(audio: NDArray[np.float64]) -> float:
        """
        Computes mean energy of audio array.
        :param audio: audio array
        :return: mean energy of audio array
        """
        return np.mean(audio ** 2)

    def var_energy(audio: NDArray[np.float64]) -> float:
        """
        Computes variance of energy of audio array.
        :param audio: audio array
        :return: variance of energy of audio array
        """
        return np.var(audio ** 2)

    def sum_energy(audio: NDArray[np.float64]) -> float:
        """
        Computes sum of energy of audio array.
        :param audio: audio array
        :return: sum of energy of audio array
        """
        return np.sum(audio ** 2)
    
    def z_standardize(audio: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Standardizes audio array.
        :param audio: audio array
        :return: standardized audio array
        """
        return (audio - np.mean(audio)) / np.std(audio)

    def intensity(audio: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Computes intensity of audio array.
        :param audio: audio array
        :return: intensity of audio array
        """
        return librosa.feature.rms(audio)

    def db_loudness(audio: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Computes loudness of audio array.
        :param audio: audio array
        :return: loudness of audio array
        """
        intensity = librosa.feature.rms(audio)
        return librosa.amplitude_to_db(intensity)
    
    def duration(audio: NDArray[np.float64], sr: int) -> float:
        """
        Computes duration of audio array.
        :param audio: audio array
        :param sr: sampling rate
        :return: duration of audio array
        """
        return len(audio) / sr
    