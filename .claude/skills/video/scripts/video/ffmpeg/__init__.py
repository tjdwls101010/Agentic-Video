"""ffmpeg and ffprobe as measuring instruments (stream facts, loudness, speech spans, still frames, speech audio to send elsewhere), and the encoder that turns rendered graphics into the alpha intermediate FilmCraft composites. Nothing here edits the user's media."""

from .encode import AlphaWriter
from .envelope import envelope, measured_speech, speech_spans
from .extract import extract_audio, extract_frame
from .loudness import Loudness, loudness
from .probe import AudioStream, Media, VideoStream, probe, tool

__all__ = ["probe", "Media", "VideoStream", "AudioStream", "loudness", "Loudness", "extract_frame", "extract_audio", "envelope", "speech_spans", "measured_speech", "tool", "AlphaWriter"]
