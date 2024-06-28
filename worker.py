import os, os.path, shutil
import time
import fnmatch
import types
import ffmpeg
import torch
import whisperx

from os.path import isfile
from dotenv import load_dotenv
from pyannote.audio import Pipeline

from viewer import create_viewer
from srt import create_srt
from transcription import transcribe, get_prompt
from util import time_estimate
from config import ONLINE, DEVICE, ROOT, WINDOWS


if WINDOWS:
    os.environ["PATH"] += os.pathsep + "ffmpeg/bin"
    os.environ["PATH"] += os.pathsep + "ffmpeg"
    os.environ["PYANNOTE_CACHE"] = ROOT + '/models'
    os.environ["HF_HOME"] = ROOT + '/models'

load_dotenv()


def report_error(text = ''):
    print(text)
    if not os.path.exists(ROOT + 'data/error/' + user_id):
        os.makedirs(ROOT + 'data/error/' + user_id)
    with open(file_name_error + '.txt', 'w') as f:
        f.write(text)
    shutil.move(file_name, file_name_error)


def oldest_file(folder):
    matches = []
    times = []
    for root, _, filenames in os.walk(folder):
        for filename in fnmatch.filter(filenames, '*.*'):
            file_path = os.path.join(root, filename)
            matches.append(file_path)
            times.append(os.path.getmtime(file_path))

    return [m for _, m in sorted(zip(times, matches))]


if __name__ == "__main__":
    if DEVICE == 'cpu':
        compute_type = 'float32'
    else:
        compute_type = 'float16'

    if ONLINE:
        model = whisperx.load_model("large-v3", DEVICE, compute_type = compute_type)
    else:
        model = whisperx.load_model("large-v3", DEVICE, compute_type = compute_type, download_root='models/whisperx')

    model.model.get_prompt = types.MethodType(get_prompt, model.model)
    diarize_model = Pipeline.from_pretrained("pyannote/speaker-diarization", use_auth_token=os.getenv('HF_AUTH_TOKEN')).to(torch.device(DEVICE))    

    for directory in ['data/in/', 'data/out/', 'data/error/', 'data/worker/']:
        if not os.path.exists(ROOT + directory): 
            os.makedirs(ROOT + directory)

    print('worker ready')
    while True:
        try:
            files_sorted_by_date = oldest_file(ROOT + 'data/in/')
        except:
            pass
        
        for file_name in files_sorted_by_date:
            file = os.path.basename(file_name)
            user_id = os.path.normpath(file_name).split(os.path.sep)[-2]

            file_name_error = ROOT + 'data/error/' + user_id + '/' + file
            file_name_out = ROOT + 'data/out/' + user_id + '/' + file + '.mp4'
            file_name_viewer = ROOT + 'data/out/' + user_id + '/' + file + '.html'
            file_name_viewer_experimental = ROOT + 'data/out/' + user_id + '/' + file + '_e.html'
            file_name_viewer_srt = ROOT + 'data/out/' + user_id + '/' + file + '_srt.html'
            file_name_txt = ROOT + 'data/out/' + user_id + '/' + file + '.txt'
            file_name_srt = ROOT + 'data/out/' + user_id + '/' + file + '.srt'

            # skip all files that have already been transcribed.
            if (not isfile(file_name) or isfile(file_name_viewer)) or file == 'hotwords.txt':
                continue
        
            try:
                if os.path.exists(ROOT + 'data/worker/' + user_id) and os.path.isdir(ROOT + 'data/worker/' + user_id):
                    shutil.rmtree(ROOT + 'data/worker/' + user_id)
            except:
                # we probably don't have enough permission in ROOT/data/
                print('Could not remove folder: ' + ROOT + 'data/worker/' + user_id)

            try:
                if not os.path.exists(ROOT + 'data/out/' + user_id): 
                    os.makedirs(ROOT + 'data/out/' + user_id)
            except:
                # we probably don't have enough permission in ROOT/data/
                print('Could not create output folder for user_id: ' + user_id)
                continue

            # estimate run time: length of audio divided by 13
            try:
                time.sleep(2)
                estimated_time, run_time = time_estimate(file_name, ONLINE)
                if run_time == -1:
                    report_error('Datei konnte nicht gelesen werden')
                    continue
                start = time.time()
            except Exception as e: 
                print(e)
                report_error('Datei konnte nicht gelesen werden')
                continue

            try:
                if not os.path.exists(ROOT + 'data/worker/' + user_id):
                    os.makedirs(ROOT + 'data/worker/' + user_id)
                progress_file_name = ROOT + 'data/worker/' + user_id + '/' + str(estimated_time) + '_' + str(time.time()) + '_' + file
                with open(progress_file_name, 'w') as f:
                    f.write('')
            except:
                # we probably don't have enough permission in ROOT/data/
                print('Could not create progress_file')

            # the file most likely does not have a (valid) audio stream
            if not ffmpeg.probe(file_name, select_streams='a')['streams']:
                report_error('Die Tonspur der Datei konnte nicht gelesen werden')
                continue

            exit_status = os.system(f'ffmpeg -y -i "{file_name}" -filter:v scale=320:-2 -af "lowpass=3000,highpass=200" "{file_name_out}"')
            if not exit_status == 0:
                file_name_out = file_name
                print('Exit status: ' + str(exit_status))


            try:
                hotwords = []
                if isfile(ROOT + 'data/in/' + user_id + '/hotwords.txt'):
                    with open(ROOT + 'data/in/' + user_id + '/hotwords.txt', 'r') as h:
                        hotwords = h.read().split('\n')
                data = transcribe(file_name_out, model, diarize_model, DEVICE, None, add_language = True, online = ONLINE, hotwords = hotwords)
            except Exception as e:
                report_error('Transkription fehlgeschlagen')
                print(e)
            try:
                srt = create_srt(data)
                viewer = create_viewer(data, file_name_out, True, False, ROOT)

                with open(file_name_viewer, 'w', encoding = 'utf-8') as f:
                    f.write(viewer)
                with open(file_name_srt, 'w', encoding = 'utf-8') as f:
                    f.write(srt)

                print('Run Time ' + str(run_time))
                print('Estimated Time ' + str(estimated_time))
                print('Actual Time ' + str(time.time()-start))
            except Exception as e:
                report_error('Fehler beim Erstellen des Editors')
                print(e)


            if os.path.exists(progress_file_name):
                os.remove(progress_file_name)

            break

        time.sleep(1)