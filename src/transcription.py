import os
import torch
import pandas as pd
import time
import whisperx
from whisperx.audio import SAMPLE_RATE, log_mel_spectrogram, N_SAMPLES

from data.const import data_leaks

DEVICE = os.getenv("DEVICE")


def get_prompt(self, tokenizer, previous_tokens, without_timestamps, prefix):
    prompt = []

    if previous_tokens or prefix:
        prompt.append(tokenizer.sot_prev)
        if prefix:
            hotwords_tokens = tokenizer.encode(" " + prefix.strip())
            if len(hotwords_tokens) >= self.max_length // 2:
                hotwords_tokens = hotwords_tokens[: self.max_length // 2 - 1]
            prompt.extend(hotwords_tokens)
        if prefix and previous_tokens:
            prompt.extend(previous_tokens[-(self.max_length // 2 - 1) :])

    prompt.extend(tokenizer.sot_sequence)

    if without_timestamps:
        prompt.append(tokenizer.no_timestamps)

    return prompt


def detect_language(audio, model):
    model_n_mels = model.model.feat_kwargs.get("feature_size")
    segment = log_mel_spectrogram(
        audio[:N_SAMPLES],
        n_mels=model_n_mels if model_n_mels is not None else 80,
        padding=0 if audio.shape[0] >= N_SAMPLES else N_SAMPLES - audio.shape[0],
    )
    encoder_output = model.model.encode(segment)
    results = model.model.model.detect_language(encoder_output)
    language_token, language_probability = results[0][0]
    language = language_token[2:-2]
    return (language, language_probability)


def transcribe(
    complete_name,
    model,
    diarize_model,
    device,
    num_speaker,
    add_language=False,
    hotwords=[],
    batch_size=4,
    num_speakers_detected=None,
    language="de",
):
    torch.cuda.empty_cache()

    # Convert audio given a file path.
    audio = whisperx.load_audio(complete_name)

    start_time = time.time()

    if len(hotwords) > 0:
        model.options = model.options._replace(prefix=" ".join(hotwords))
    print("Transcribing...")
    if DEVICE == "mps":
        import mlx_whisper

        decode_options = {"language": None, "prefix": " ".join(hotwords)}

        result1 = mlx_whisper.transcribe(
            complete_name,
            path_or_hf_repo="mlx-community/whisper-large-v3-mlx",
            **decode_options,
        )
    else:
        result1 = model.transcribe(audio, batch_size=batch_size, language=language)

    print(f"Transcription took {time.time() - start_time:.2f} seconds.")
    if len(hotwords) > 0:
        model.options = model.options._replace(prefix=None)

    # Align whisper output.
    model_a, metadata = whisperx.load_align_model(language_code=result1["language"], device=device)
    start_aligning = time.time()

    print("Aligning...")
    result2 = whisperx.align(
        result1["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )

    print(f"Alignment took {time.time() - start_aligning:.2f} seconds.")

    if add_language:
        start_language = time.time()
        print("Adding language...")
        for segment in result2["segments"]:
            start = (int(segment["start"]) * 16_000) - 8_000
            end = ((int(segment["end"]) + 1) * 16_000) + 8_000
            segment_audio = audio[start:end]
            if DEVICE == "mps":
                ## This is a workaround to use the whisper model in mps, it doesn't have "detect language" method
                decode_options = {"language": None, "prefix": " ".join(hotwords)}
                language = mlx_whisper.transcribe(
                    segment_audio, path_or_hf_repo="mlx-community/whisper-large-v3-mlx", **decode_options
                )
                segment["language"] = language["language"]
            else:
                detected_language, language_probability = detect_language(segment_audio, model)
                segment["language"] = detected_language if language_probability > 0.85 else language
        print(f"Adding language took {time.time() - start_language:.2f} seconds.")

    # Diarize and assign speaker labels.
    start_diarize = time.time()
    print("Diarizing...")
    audio_data = {
        "waveform": torch.from_numpy(audio[None, :]),
        "sample_rate": SAMPLE_RATE,
    }

    
    segments = diarize_model(audio_data, num_speakers=num_speaker)

    diarize_df = pd.DataFrame(segments.itertracks(yield_label=True), columns=["segment", "label", "speaker"])
    diarize_df["start"] = diarize_df["segment"].apply(lambda x: x.start)
    diarize_df["end"] = diarize_df["segment"].apply(lambda x: x.end)
    result3 = whisperx.assign_word_speakers(diarize_df, result2)
    if num_speakers_detected is not None:
        for segment in result3["segments"]:
            segment["speaker"] = "SPEAKER_" + str(num_speakers_detected + int(segment["speaker"].split('_')[1])).zfill(2)

    print(f"Diarization took {time.time() - start_diarize:.2f} seconds.")
    print(f"Total time: {time.time() - start_time:.2f} seconds.")
    torch.cuda.empty_cache()
    if DEVICE == "mps":
        torch.mps.empty_cache()
    # Text cleanup.
    cleaned_segments = []
    for segment in result3["segments"]:
        if result1["language"] in data_leaks:
            for line in data_leaks[result1["language"]]:
                if line in segment["text"]:
                    segment["text"] = segment["text"].replace(line, "")
        segment["text"] = segment["text"].strip()

        if len(segment["text"]) > 0:
            cleaned_segments.append(segment)

    return cleaned_segments
