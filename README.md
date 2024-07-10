# Audio Transcription Tool "Transcribo"
**Transcribe any audio or video file. Edit and view your transcripts in a standalone HTML editor.**

[![PyPI - Python](https://img.shields.io/badge/python-v3.10+-blue.svg)](https://github.com/machinelearningZH/audio-transcription)

<img src="_imgs/ui1.PNG" alt="editor" width="1000"/>

<details>

<summary>Contents</summary>

- [Usage](#usage)
- [Project information](#project-information)
    - [What does the app do?](#what-does-the-app-do)
    - [Hardware requirements](#hardware-requirements)
- [Project team](#project-team)
- [Contributing](#feedback-and-contributing)

</details>

## Usage

- Make sure you have a compatible NVIDIA driver and CUDA Version installed: https://pytorch.org/
- Install ffmpeg
    - Windows: https://phoenixnap.com/kb/ffmpeg-windows
    - Linux: `sudo apt install ffmpeg`
- Create a new Python environment, e.g.: `conda create --name transcribo python=3.10`
- Activate your new environment: `conda activate transcribo`
- Clone this repo.
- Install packages: `pip install -r requirements.txt`
- Make sure, that the onnxruntime-gpu package is installed. Otherwise uninstall onnxruntime and install onnxruntime-gpu
    - pip uninstall onnxruntime
    - pip install --force-reinstall onnxruntime-gpu
- Create a Huggingface access token
    - Accept [pyannote/segmentation-3.0](https://hf.co/pyannote/segmentation-3.0) user conditions
    - Accept [pyannote/speaker-diarization-3.0](https://hf.co/pyannote-speaker-diarization-3.0) user conditions
    - Create access token at [hf.co/settings/tokens](https://hf.co/settings/tokens).
- Create a `.env` file and input your access token:
```
    HF_AUTH_TOKEN = ...
```
- Start the worker and frontend scripts
- Linux
    - tmux new -s transcribe_worker
    - source venv/transcribo/bin/activate
    - python worker.py
    - tmux new -s transcribe_frontend
    - source venv/transcribo/bin/activate
    - python main.py
- Windows
    - See `run_gui.bat`, `run_transcribo.bat` and `run_worker.bat`

### Config
...

## Project information

### What does the application do?

### Hardware requirements

## Project team

## Feedback and contributing
We are interested to hear from you. Please share your feedback and let us know how you use the app in your institution. You can [write an email](mailto:datashop@statistik.zh.ch) or share your ideas by opening an issue or a pull requests.
