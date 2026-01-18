from io import BytesIO
from pydub import AudioSegment


def load_audio_from_bytes(audio_bytes: bytes) -> AudioSegment:
    return AudioSegment.from_mp3(BytesIO(audio_bytes))


def stitch_audio_clips(clips: list[AudioSegment], pauses_ms: list[int]) -> AudioSegment:
    if not clips:
        raise ValueError("No audio clips provided")
    
    result = clips[0]
    for i in range(1, len(clips)):
        pause_duration = pauses_ms[i - 1] if i - 1 < len(pauses_ms) else 0
        silence = AudioSegment.silent(duration=pause_duration)
        result = result + silence + clips[i]
    
    return result


def export_mp3(audio: AudioSegment, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio.export(str(output_path), format="mp3", bitrate="128k")
