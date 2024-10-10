import datetime, copy


def create_srt(data):
    data_srt = []
    max_length = 60
    hard_max_length = 80

    # Try to split segments into sub-segments of max. max_length characters.
    # Segments shorter than max_length characters are not changed.
    for segment in data:
        segment["text"] = segment["text"]
        text = segment["text"].strip()
        length = len(text.replace(" ", ""))
        if length < max_length:
            data_srt.append(copy.deepcopy(segment))
        else:
            target_number_of_splits = int(length / (max_length)) + 1
            target_length = length / target_number_of_splits
            word_index = 0

            while word_index < len(segment["words"]):
                new_segment = {"start": -1, "end": -1, "words": [], "text": ""}
                while word_index < len(segment["words"]):
                    # Add a word to the current new_segment.
                    if (
                        new_segment["start"] == -1
                        and "start" in segment["words"][word_index]
                    ):
                        new_segment["start"] = segment["words"][word_index]["start"]
                    if "end" in segment["words"][word_index]:
                        new_segment["end"] = segment["words"][word_index]["end"]

                    new_segment["words"].append(
                        copy.deepcopy(segment["words"][word_index])
                    )
                    new_segment["text"] += segment["words"][word_index]["word"] + " "

                    # Check if word_index is a good position to start a new segment.
                    word_index += 1
                    current_length = len(new_segment["text"].replace(" ", ""))
                    # If hard_max_length will be reached after the next word, start a new segment.
                    if word_index >= len(segment["words"]) or hard_max_length < (
                        current_length + len(segment["words"][word_index]["word"])
                    ):
                        break
                    # Do not start a new segment towards the end.
                    if word_index + 2 > len(segment["words"]):
                        continue
                    # Allow early starting of a new segment if the current word contains ','/'»' or the next word contains 'und'/'oder'/'«'.
                    if current_length > target_length * 0.5 and (
                        "," in segment["words"][word_index - 1]["word"]
                        or "«" in segment["words"][word_index]["word"]
                        or "»" in segment["words"][word_index - 1]["word"]
                        or "und" in segment["words"][word_index]["word"]
                        or "oder" in segment["words"][word_index]["word"]
                    ):
                        break
                    if abs(target_length - current_length) < abs(
                        target_length
                        - (current_length + len(segment["words"][word_index]["word"]))
                    ):
                        break
                data_srt.append(copy.deepcopy(new_segment))

    # Try to increase display times of segments to 13 characters per second if possible.
    for i, segment in enumerate(data_srt):
        length = len(segment["text"].replace(" ", ""))
        display_time = segment["end"] - segment["start"]

        if (
            i + 1 < len(data_srt)
            and (length / 13) < display_time
            and data_srt[i + 1]["start"] > segment["end"]
        ):
            optimal_time_increase = display_time - (length / 13)
            segment["end"] = min(
                data_srt[i + 1]["start"], segment["end"] + optimal_time_increase
            )

    text = ""
    for i, segment in enumerate(data_srt):
        text += str(i + 1) + "\n"
        text += (
            "{:0>8}".format(str(datetime.timedelta(seconds=int(segment["start"]))))
            + ","
            + str(int(segment["start"] % 1 * 1000)).ljust(3, "0")
            + " --> "
            + "{:0>8}".format(str(datetime.timedelta(seconds=int(segment["end"]))))
            + ","
            + str(int(segment["end"] % 1 * 1000)).ljust(3, "0")
            + "\n"
        )

        segment_text = segment["text"].strip()
        length = len(segment_text.replace(" ", ""))
        if length > 40:
            segment_tokens = segment_text.split(" ")
            segment_tokens_lengths = [len(token) for token in segment_tokens]
            new_line_position = 0
            best_difference = 10000
            for index in range(len(segment_tokens_lengths)):
                difference = abs(
                    sum(segment_tokens_lengths[index:])
                    - sum(segment_tokens_lengths[:index])
                )
                if best_difference > difference:
                    best_difference = difference
                    new_line_position = index
            segment_text = (
                " ".join(segment_tokens[:new_line_position])
                + "\n"
                + " ".join(segment_tokens[new_line_position:])
            )

        text += f"{segment_text}\n\n"

    text = text.replace("ß", "ss")
    return text
