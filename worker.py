import os
import shutil
import time
import fnmatch
import types
import ffmpeg
import torch
import whisperx
import zipfile
import logging

from os.path import isfile, join, normpath, basename, dirname
from dotenv import load_dotenv
from pyannote.audio import Pipeline

from src.viewer import create_viewer, write_content_summary, read_content_summary
from src.srt import create_srt
from src.transcription import transcribe, get_prompt
from src.util import time_estimate, isolate_voices

# Load environment variables
load_dotenv()

# Configuration
ONLINE = os.getenv("ONLINE") == "True"
DEVICE = os.getenv("DEVICE")
ROOT = os.getenv("ROOT")
WINDOWS = os.getenv("WINDOWS") == "True"
BATCH_SIZE = int(os.getenv("BATCH_SIZE"))
SUMMARIZATION = os.getenv("SUMMARIZATION") == "True"

if SUMMARIZATION:
    from llama_cpp import Llama
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer
    import json


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if WINDOWS:
    os.environ["PATH"] += os.pathsep + "ffmpeg/bin"
    os.environ["PATH"] += os.pathsep + "ffmpeg"
    os.environ["PYANNOTE_CACHE"] = join(ROOT, "models")
    os.environ["HF_HOME"] = join(ROOT, "models")


def report_error(file_name, file_name_error, user_id, text=""):
    logger.error(text)
    error_dir = join(ROOT, "data", "error", user_id)
    os.makedirs(error_dir, exist_ok=True)
    error_file = file_name_error + ".txt"
    with open(error_file, "w") as f:
        f.write(text)
    shutil.move(file_name, file_name_error)


def oldest_files(folder):
    matches = []
    times = []
    for root, _, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, "*.*"):
            file_path = join(root, filename)
            matches.append(file_path)
            times.append(os.path.getmtime(file_path))
    return [m for _, m in sorted(zip(times, matches))]


def transcribe_file(
    file_name, multi_mode=False, num_speakers_detected=None, audio_files=None, language="de"
):
    data = None
    estimated_time = 0
    progress_file_name = ""

    file = basename(file_name)
    user_id = normpath(dirname(file_name)).split(os.sep)[-1]
    file_name_error = join(ROOT, "data", "error", user_id, file)
    file_name_out = join(ROOT, "data", "out", user_id, file + ".mp4")

    # Clean up worker directory
    if not multi_mode:
        worker_user_dir = join(ROOT, "data", "worker", user_id)
        if os.path.exists(worker_user_dir):
            try:
                shutil.rmtree(worker_user_dir)
            except OSError as e:
                logger.error(f"Could not remove folder: {worker_user_dir}. Error: {e}")

    # Create output directory
    if not multi_mode:
        output_user_dir = join(ROOT, "data", "out", user_id)
        os.makedirs(output_user_dir, exist_ok=True)

    # Estimate run time
    try:
        time.sleep(2)
        estimated_time, run_time = time_estimate(file_name, ONLINE)
        if run_time == -1:
            report_error(
                file_name, file_name_error, user_id, "Datei konnte nicht gelesen werden"
            )
            return data, estimated_time, progress_file_name
    except Exception as e:
        logger.exception("Error estimating run time")
        report_error(
            file_name, file_name_error, user_id, "Datei konnte nicht gelesen werden"
        )
        return data, estimated_time, progress_file_name

    if not multi_mode:
        worker_user_dir = join(ROOT, "data", "worker", user_id)
        os.makedirs(worker_user_dir, exist_ok=True)
        progress_file_name = join(
            worker_user_dir, f"{estimated_time}_{int(time.time())}_{file}"
        )
        try:
            with open(progress_file_name, "w") as f:
                f.write("")
        except OSError as e:
            logger.error(
                f"Could not create progress file: {progress_file_name}. Error: {e}"
            )

    # Check if file has a valid audio stream
    try:
        if not ffmpeg.probe(file_name, select_streams="a")["streams"]:
            report_error(
                file_name,
                file_name_error,
                user_id,
                "Die Tonspur der Datei konnte nicht gelesen werden",
            )
            return data, estimated_time, progress_file_name
    except ffmpeg.Error as e:
        logger.exception("ffmpeg error during probing")
        report_error(
            file_name,
            file_name_error,
            user_id,
            "Die Tonspur der Datei konnte nicht gelesen werden",
        )
        return data, estimated_time, progress_file_name

    # Process audio
    if not multi_mode:
        # Convert and filter audio
        exit_status = os.system(
            f'ffmpeg -y -i "{file_name}" -filter:v scale=320:-2 -af "lowpass=3000,highpass=200" "{file_name_out}"'
        )
        if exit_status == 256:
            exit_status = os.system(
                f'ffmpeg -y -i "{file_name}" -c:v copy -af "lowpass=3000,highpass=200" "{file_name_out}"'
            )
        if not exit_status == 0:
            logger.exception("ffmpeg error during audio processing")
            file_name_out = file_name  # Fallback to original file

    else:
        file_name_out = file_name

    # Load hotwords
    hotwords = []
    hotwords_file = join(ROOT, "data", "in", user_id, "hotwords.txt")
    if isfile(hotwords_file):
        with open(hotwords_file, "r") as h:
            hotwords = h.read().splitlines()

    # Transcribe
    try:
        data = transcribe(
            file_name_out,
            model,
            diarize_model,
            DEVICE,
            None,
            add_language=(
                False if DEVICE == "mps" else True
            ),  # on MPS is rather slow and unreliable, but you can try with setting this to true
            hotwords=hotwords,
            num_speakers_detected=num_speakers_detected,
            language=language,
        )
    except Exception as e:
        logger.exception("Transcription failed")
        report_error(
            file_name, file_name_error, user_id, "Transkription fehlgeschlagen"
        )

    return data, estimated_time, progress_file_name


def summarize(text, llm, encoder):
    out = llm.create_chat_completion(
        messages=[
            {
                "role": "system",
                "content": "Du bist Qwen, du verfasst Zusammenfassungen auf Deutsch und antwortest im JSON-Format",
            },
            {
                "role": "user",
                "content": """Fasse das folgende Transkript zusammen. Verwende nur die gegebenen Informationen, erfinde keine Zusätzlichen Fakten. Erwähne die wichtigen Details, wie zum Beispiel Orte, Personen oder Ereignisse. Strukturiere die Zusammenfassung in unterschiedliche Themen. Jedes Thema hat einen Namen und einen Inhalt. Formuliere sachlich und neutral. Schreib prägnant und auf Deutsch.
Transkipt: """
                + encoder.decode(encoder(text)["input_ids"][:30000]),
            },
        ],
        response_format={
            "type": "json_object",
            "schema": {
                "type": "object",
                "properties": {
                    "thema_name": {"type": "array", "items": {"type": "string"}},
                    "thema_inhalt": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["thema_name", "thema_inhalt"],
            },
        },
        temperature=0.5,
    )

    summary = ""
    content = json.loads(out["choices"][0]["message"]["content"].replace("ß", "ss"))
    for i in range(len(content["thema_name"])):
        if len(content["thema_inhalt"]) == i:
            break
        summary += "<b>" + content["thema_name"][i] + "</b><br>"
        summary += content["thema_inhalt"][i] + "<br>"

    return summary


if __name__ == "__main__":
    WHISPER_DEVICE = "cpu" if DEVICE == "mps" else DEVICE
    if WHISPER_DEVICE == "cpu":
        compute_type = "float32"
    else:
        compute_type = "float16"

    # Load models
    whisperx_model = (
        "tiny.en" if DEVICE == "mps" else "large-v3"
    )  # we can load a really small one for mps, because we use mlx_whisper later and only need whisperx for diarization and alignment
    if ONLINE:
        model = whisperx.load_model(
            whisperx_model, WHISPER_DEVICE, compute_type=compute_type
        )
    else:
        model = whisperx.load_model(
            whisperx_model,
            WHISPER_DEVICE,
            compute_type=compute_type,
            download_root=join("models", "whisperx"),
        )

    model.model.get_prompt = types.MethodType(get_prompt, model.model)
    diarize_model = Pipeline.from_pretrained(
        "pyannote/speaker-diarization", use_auth_token=os.getenv("HF_AUTH_TOKEN")
    ).to(torch.device(DEVICE))

    if SUMMARIZATION:
        model_name_or_path = "bartowski/Qwen2.5-7B-Instruct-1M-GGUF"
        model_basename = "Qwen2.5-7B-Instruct-1M-Q6_K.gguf"
        model_path = hf_hub_download(
            repo_id=model_name_or_path, filename=model_basename
        )

        # Initialize the Llama instance
        llm = Llama(
            model_path=model_path,
            n_ctx=32768,
            n_gpu_layers=0,
            n_threads=8,
            use_mmap=True,
            use_mlock=False,
            verbose=False,
        )
        encoder = AutoTokenizer.from_pretrained("Qwen/Qwen-7B", trust_remote_code=True)

    # Create necessary directories
    for directory in ["data/in/", "data/out/", "data/error/", "data/worker/"]:
        os.makedirs(join(ROOT, directory), exist_ok=True)

    disclaimer = (
        "This transcription software (the Software) incorporates the open-source model Whisper Large v3 "
        "(the Model) and has been developed according to and with the intent to be used under Swiss law. "
        "Please be aware that the EU Artificial Intelligence Act (EU AI Act) may, under certain circumstances, "
        "be applicable to your use of the Software. You are solely responsible for ensuring that your use of "
        "the Software as well as of the underlying Model complies with all applicable local, national and "
        "international laws and regulations. By using this Software, you acknowledge and agree (a) that it is "
        "your responsibility to assess which laws and regulations, in particular regarding the use of AI "
        "technologies, are applicable to your intended use and to comply therewith, and (b) that you will hold "
        "us harmless from any action, claims, liability or loss in respect of your use of the Software."
    )
    logger.info(disclaimer)
    logger.info("Worker ready")

    while True:
        try:
            files_sorted_by_date = oldest_files(join(ROOT, "data", "in"))
        except Exception as e:
            logger.exception("Error accessing input directory")
            time.sleep(1)
            continue

        for file_name in files_sorted_by_date:
            file = basename(file_name)
            user_id = normpath(dirname(file_name)).split(os.sep)[-1]

            if file == "hotwords.txt" or file == "language.txt":
                continue

            file_name_viewer = join(ROOT, "data", "out", user_id, file + ".html")

            # Skip files that have already been processed
            if not isfile(file_name) or isfile(file_name_viewer):
                continue

            language_file = join(ROOT, "data", "in", user_id, "language.txt")
            if isfile(language_file):
                with open(language_file, "r") as h:
                    language = h.read()
            else:
                language = "de"

            # Check if it's a zip file
            if file_name.lower().endswith(".zip"):
                try:
                    zip_extract_dir = join(ROOT, "data", "worker", "zip")
                    shutil.rmtree(zip_extract_dir, ignore_errors=True)
                    os.makedirs(zip_extract_dir, exist_ok=True)

                    with zipfile.ZipFile(file_name, "r") as zip_ref:
                        zip_ref.extractall(zip_extract_dir)

                    multi_mode = True
                    data_parts = []
                    estimated_time = 0
                    data = []
                    file_parts = []

                    # Collect files from zip
                    for root, _, filenames in os.walk(zip_extract_dir):
                        audio_files = [
                            fn for fn in filenames if fnmatch.fnmatch(fn, "*.*")
                        ]
                        for filename in audio_files:
                            file_path = join(root, filename)
                            est_time_part, _ = time_estimate(file_path, ONLINE)
                            estimated_time += est_time_part

                    progress_file_name = join(
                        ROOT,
                        "data",
                        "worker",
                        user_id,
                        f"{estimated_time}_{int(time.time())}_{file}",
                    )
                    with open(progress_file_name, "w") as f:
                        f.write("")

                    isolate_voices([join(root, filename) for filename in audio_files])

                    num_speakers_detected = 0
                    # Transcribe each file
                    for filename in audio_files:
                        file_path = join(root, filename)
                        file_parts.append(f'-i "{file_path}"')
                        data_part, _, _ = transcribe_file(
                            file_path,
                            multi_mode=True,
                            num_speakers_detected=num_speakers_detected,
                            language=language,
                        )
                        num_speakers_detected += len(set([segment['speaker'] for segment in data_part]))
                        data_parts.append(data_part)

                    # Merge data
                    while any(data_parts):
                        earliest = min(
                            [(i, dp[0]) for i, dp in enumerate(data_parts) if dp],
                            key=lambda x: x[1]["start"],
                            default=(None, None),
                        )
                        if earliest[0] is None:
                            break

                        data.append(earliest[1])
                        data_parts[earliest[0]].pop(0)

                    # Merge audio files
                    output_audio = join(ROOT, "data", "worker", "zip", "tmp.mp4")
                    ffmpeg_input = " ".join(file_parts)
                    ffmpeg_cmd = f'ffmpeg {ffmpeg_input} -filter_complex amix=inputs={len(file_parts)}:duration=first "{output_audio}"'
                    os.system(ffmpeg_cmd)

                    # Process merged audio
                    file_name_out = join(ROOT, "data", "out", user_id, file + ".mp4")
                    exit_status = os.system(
                        f'ffmpeg -y -i "{output_audio}" -filter:v scale=320:-2 -af "lowpass=3000,highpass=200" "{file_name_out}"'
                    )
                    if exit_status == 256:
                        exit_status = os.system(
                            f'ffmpeg -y -i "{output_audio}" -c:v copy -af "lowpass=3000,highpass=200" "{file_name_out}"'
                        )
                    if not exit_status == 0:
                        logger.exception("ffmpeg error during audio processing")
                        file_name_out = output_audio  # Fallback to original fileue)

                    shutil.rmtree(zip_extract_dir, ignore_errors=True)
                except Exception as e:
                    logger.exception("Transcription failed for zip file")
                    report_error(
                        file_name,
                        join(ROOT, "data", "error", user_id, file),
                        user_id,
                        "Transkription fehlgeschlagen",
                    )
                    continue
            else:
                # Single file transcription
                data, estimated_time, progress_file_name = transcribe_file(
                    file_name, language=language
                )

            if data is None:
                continue

            # Generate outputs
            try:
                file_name_out = join(ROOT, "data", "out", user_id, file + ".mp4")

                srt = create_srt(data)
                viewer = create_viewer(data, file_name_out, True, False, ROOT, language)

                file_name_srt = join(ROOT, "data", "out", user_id, file + ".srt")
                with open(file_name_viewer, "w", encoding="utf-8") as f:
                    f.write(viewer)
                with open(file_name_srt, "w", encoding="utf-8") as f:
                    f.write(srt)

                logger.info(f"Estimated Time: {estimated_time}")
            except Exception as e:
                logger.exception("Error creating editor")
                report_error(
                    file_name,
                    join(ROOT, "data", "error", user_id, file),
                    user_id,
                    "Fehler beim Erstellen des Editors",
                )

            if progress_file_name and os.path.exists(progress_file_name):
                os.remove(progress_file_name)
            if DEVICE == "mps":
                print("Exiting worker to prevent memory leaks with MPS...")
                exit(
                    0
                )  # Due to memory leak problems, we restart the worker after each transcription

            break  # Process one file at a time

        try:
            files_sorted_by_date = oldest_files(join(ROOT, "data", "out"))
        except Exception as e:
            logger.exception("Error accessing input directory")
            time.sleep(1)
            continue

        if SUMMARIZATION:
            for file_name in files_sorted_by_date:
                if file_name.endswith(".todosummary"):
                    logger.info(f"Summarizing file")
                    try:
                        content_out, lines = read_content_summary(file_name)
                        summary = summarize(content_out, llm, encoder)
                    except Exception as e:
                        logger.exception("Summarization failed")
                        summary = (
                            "Zusammenfassung fehlgeschlagen. Bitte versuche es erneut."
                        )
                    write_content_summary(
                        summary, lines, file_name.replace(".todosummary", ".summary")
                    )
                    os.remove(file_name)
                    logger.info(f"Summarizing done")
                    break

        time.sleep(1)
