import torch
import pandas as pd
import time
import whisperx
from whisperx.audio import SAMPLE_RATE, log_mel_spectrogram, N_SAMPLES
from config import BATCH_SIZE

from data.const import data_leaks


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
    online=True,
    hotwords=[],
):
    torch.cuda.empty_cache()

    # convert audio given a file path. this function needs to change if we switch to a in-memory file.
    audio = whisperx.load_audio(complete_name)

    start = time.time()
    if len(hotwords) > 0:
        model.options = model.options._replace(prefix=" ".join(hotwords))
    result1 = model.transcribe(audio, batch_size=BATCH_SIZE, language="de")
    if len(hotwords) > 0:
        model.options = model.options._replace(prefix=None)
    print(str(time.time() - start))

    # align whisper output
    model_a, metadata = whisperx.load_align_model(
        language_code=result1["language"], device=device
    )
    result2 = whisperx.align(
        result1["segments"],
        model_a,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )

    if add_language:
        for segment in result2["segments"]:
            start = (int(segment["start"]) * 16_000) - 8_000
            end = ((int(segment["end"]) + 1) * 16_000) + 8_000
            segment_audio = audio[start:end]
            language, language_probability = detect_language(segment_audio, model)
            segment["language"] = language if language_probability > 0.85 else "de"

    # diarize and assign speaker labels
    # currently we make use of my hugginface authentication token.
    # in the future we want to find a better solution (perhaps it is possible to use the diarization and segmentation models locally).
    audio_data = {
        "waveform": torch.from_numpy(audio[None, :]),
        "sample_rate": SAMPLE_RATE,
    }

    segments = diarize_model(audio_data, num_speakers=num_speaker)
    diarize_df = pd.DataFrame(
        segments.itertracks(yield_label=True), columns=["segment", "label", "speaker"]
    )
    diarize_df["start"] = diarize_df["segment"].apply(lambda x: x.start)
    diarize_df["end"] = diarize_df["segment"].apply(lambda x: x.end)

    result3 = whisperx.assign_word_speakers(diarize_df, result2)

    torch.cuda.empty_cache()

    # text cleanup
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
