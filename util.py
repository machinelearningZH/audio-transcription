import subprocess


def get_length(filename):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            filename,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return float(result.stdout)


def time_estimate(filename, online=True):
    try:
        run_time = get_length(filename)
        if online:
            return run_time / 10, run_time
        else:
            return run_time / 6, run_time
    except Exception as e:
        print(e)
        return -1, -1
