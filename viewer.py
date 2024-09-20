import os
import datetime
from config import ADDITIONAL_SPEAKERS


# Function to generate the viewer html-file.
# Input data is the segments of the output of whisperx.assign_word_speakers: whisperx.assign_word_speakers(diarize_df, result2)['segments']
# File_path is the path to the audio/video file.
def create_viewer(data, file_path, encode_base64, combine_speaker, root):
    for segment in data:
        if "speaker" not in segment:
            segment["speaker"] = "unknown"
    file_name = str(os.path.basename(file_path))

    html = header(root)
    html += navbar(root)
    html += video(file_name, encode_base64)
    html += buttons()
    html += meta_data(file_name, encode_base64)
    html += speaker_information(data)
    html += transcript(data, combine_speaker)
    html += javascript(data, file_path, encode_base64, file_name)
    return html


def header(root):
    content = ""
    with open(root + "data/bootstrap_content.txt", "r") as f:
        bootstrap_content = f.read()

    content += "<!doctype html>\n<html lang=\"en\">\n<meta http-equiv='Content-Type' content='text/html;charset=UTF-8'>\n<head>\t\n\t<style>\n\t\t@charset \"UTF-8\";/*!\n\t\t * Bootstrap  v5.3.2 (https://getbootstrap.com/)\n\t\t * Copyright 2011-2023 The Bootstrap Authors\n\t\t * Licensed under MIT (https://github.com/twbs/bootstrap/blob/main/LICENSE)\n\t\t"
    content += bootstrap_content + "\n"
    content += '\t\t/*# sourceMappingURL=bootstrap.min.css.map */\n\t\t.sticky-offset {\n\t\t\ttop: 130px;\n\t\t}\n\t\t.segment {\n\t\t\tpadding-right: 8px;\n\t\t}\n\t*[contenteditable]:empty:before{content: "\\feff-";}\n\t</style>\n</head>\n'

    return content


def navbar(root):
    with open(root + "data/logo.txt", "r") as f:
        logo = f.read()
    content = "<body>"
    content += "\n"
    content += f'\t<nav class="navbar sticky-top navbar-light" style="background-color: #0070b4; z-index: 999">\n\t\t<img src="{logo}" width="390" height="105" alt=""></img>\n\t</nav>'
    content += "\n"
    return content


def video(file_name, encode_base64):
    content = '\t<div class="row container justify-content-center align-items-start" style="max-width: 200ch; margin-left: auto; margin-right: auto; margin-bottom: 0px;">\n\t\t<div class="col-md-6 sticky-top sticky-offset" style="width: 40%; z-index: 1; margin-bottom: 0px;"">\n'
    if encode_base64:
        content += f'\t\t\t<div style="padding: 0">\n\t\t\t\t<video id="player" width="100%" style="max-height: 250px" src="" type="video/MP4" controls="controls" position="sticky"></video>\n'
    else:
        content += f'\t\t\t<div>\n\t\t\t\t<video id="player" width="100%" src="{file_name}" type="video/MP4" controls="controls" position="sticky"></video>\n'
    return content


def meta_data(file_name, encode_base64):
    content = '\t\t\t\t<div style="overflow-y: scroll; height: calc(100vh - 450px)">\n'
    content += '\t\t\t\t<div style="margin-top:10px;">\n'
    content += '\t\t\t\t\t<label for="nr">Hashwert</label><span id="hash" class="form-control">0</span>\n'
    content += (
        '\t\t\t\t\t<label for="date">Transkriptionssdatum</label><span contenteditable="true" class="form-control">'
        + str(datetime.date.today().strftime("%d-%m-%Y"))
        + "</span>\n"
    )
    if not encode_base64:
        content += f'\t\t\t\t\t<label for="date">Videodatei</label><span contenteditable="true" class="form-control", id="source">./{file_name}</span>\n'
    content += "\t\t\t\t</div>\n"
    return content


def speaker_information(data):
    content = '\t\t\t\t<div style="margin-top:10px;" class="viewer-hidden">\n'
    speakers = sorted(
        set(
            [
                segment["speaker"]
                for segment in data
                if segment["speaker"] is not "unknown"
            ]
        )
    )

    n_speakers = len(speakers)
    for i in range(ADDITIONAL_SPEAKERS):
        speakers.append(str(n_speakers + i).zfill(2))
    speakers.append("unknown")

    for idx, speaker in enumerate(speakers):
        if speaker is not "unknown":
            content += f'\t\t\t\t\t<span contenteditable="true" class="form-control" id="IN_SPEAKER_{str(idx).zfill(2)}" style="margin-top:4px;">Person {speaker[-2:]}</span>\n'

    content += "\t\t\t\t<br><br><br><br><br></div>\n"
    content += "\t\t\t\t</div>\n"
    content += "\t\t\t</div>\n"
    content += "\t\t</div>\n"
    return content


def buttons():
    content = '\t\t\t\t<div style="margin-top:10px;" class="viewer-hidden">\n'
    content += '\t\t\t\t\t<a href ="#" id="viewer-link" onClick="viewerClick()" class="btn btn-primary">Viewer erstellen</a>\n'
    content += '\t\t\t\t\t<a href ="#" id="text-link" onClick="textClick()" class="btn btn-primary">Textdatei exportieren</a>\n'
    content += '\t\t\t\t\t<a href ="#" id="download-link" onClick="downloadClick()" class="btn btn-primary">Speichern</a>\n'
    content += '\t\t\t\t\t<br><span>Verzögerung: </span><span contenteditable="true" id="delay" class="border rounded"></span>\n'
    content += '\t\t\t\t\t<input type="checkbox" id="ignore_lang" value="ignore_lang" style="margin-left: 5px" onclick="changeCheckbox(this)"/>\n'
    content += '\t\t\t\t\t<label for="ignore_lang">Fremdsprachen beim Exportieren entfernen</label>\n'
    content += "\t\t\t\t</div>\n"
    return content


def segment_buttons():
    return "<button style='float: right;' class='btn btn-danger btn-sm' onclick='removeRow(this)'><svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='currentColor' class='bi bi-trash' viewBox='0 0 16 16'><path d='M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5m3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0z'/><path d='M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1zM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4zM2.5 3h11V2h-11z'/></svg></button><button style='float: right;' class='btn btn-primary btn-sm' onclick='addRow(this)'><svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='currentColor' class='bi bi-plus' viewBox='0 0 16 16'><path d='M8 4a.5.5 0 0 1 .5.5v3h3a.5.5 0 0 1 0 1h-3v3a.5.5 0 0 1-1 0v-3h-3a.5.5 0 0 1 0-1h3v-3A.5.5 0 0 1 8 4'/></svg></button>"


def transcript(data, combine_speaker):
    content = '\t\t<div class="col-md-6" style="width: 60%; max-width: 90ch; z-index: 1; margin-left: auto; margin-right: auto">\n'
    content += '\t\t\t<div class="wrapper" style="margin: 0.5rem auto 0; max-width: 80ch;" id="editor">\n'

    speakers = sorted(
        set(
            [
                segment["speaker"]
                for segment in data
                if segment["speaker"] is not "unknown"
            ]
        )
    )
    n_speakers = len(speakers)
    for i in range(ADDITIONAL_SPEAKERS):
        speakers.append(str(n_speakers + i).zfill(2))
    speakers.append("unknown")
    speaker_order = []
    table_elements = ""
    last_speaker = None
    for segment in data:
        if (
            segment["speaker"] not in speaker_order
            and segment["speaker"] is not "unknown"
        ):
            speaker_order.append(segment["speaker"])

    for i in range(ADDITIONAL_SPEAKERS):
        speaker_order.append(str(n_speakers + i).zfill(2))
    speaker_order.append("unknown")

    for i, segment in enumerate(data):
        if last_speaker is not None and not segment["speaker"][-1] == last_speaker:
            table_elements += "\t\t\t\t\t</p>\n"
            table_elements += "\t\t\t</div>\n"
        table_elements += "\t\t\t<div>\n"
        if last_speaker is None or not segment["speaker"][-1] == last_speaker:
            table_elements += (
                '\t\t\t\t\t<div style="display: block; margin-bottom: 0.5rem;">\n'
            )
            table_elements += "\t\t\t\t\t"
            table_elements += f'<select onchange="selectChange(this)">\n'
            speaker_idx = speaker_order.index(segment["speaker"])
            for idx, speaker in enumerate(speakers):
                if idx == speaker_idx:
                    if speaker == "unknown":
                        table_elements += f'\t\t\t\t\t\t<option value="{str(idx).zfill(2)}" class="OUT_SPEAKER_{str(idx).zfill(2)}" selected="selected">Person unbekannt</option>\n'
                    else:
                        table_elements += f'\t\t\t\t\t\t<option value="{str(idx).zfill(2)}" class="OUT_SPEAKER_{str(idx).zfill(2)}" selected="selected">Person {str(speaker[-2:]).zfill(2)}</option>\n'
                else:
                    if speaker == "unknown":
                        table_elements += f'\t\t\t\t\t\t<option value="{str(idx).zfill(2)}" class="OUT_SPEAKER_{str(idx).zfill(2)}">Person unbekannt</option>\n'
                    else:
                        table_elements += f'\t\t\t\t\t\t<option value="{str(idx).zfill(2)}" class="OUT_SPEAKER_{str(idx).zfill(2)}">Person {str(speaker[-2:]).zfill(2)}</option>\n'
            table_elements += "\t\t\t\t\t</select>\n"
            table_elements += (
                '\t\t\t\t\t<span contenteditable="true">'
                + str(datetime.timedelta(seconds=round(segment["start"], 0)))
                + "</span>\n"
            )
            if "language" in segment:
                if segment["language"] in ["de", "en", "nl"]:
                    table_elements += '\t\t\t\t\t<input type="checkbox" class="language" name="language" value="Fremdsprache" style="margin-left: 5px" onclick="changeCheckbox(this)"/> <label for="language">Fremdsprache</label>\n'
                else:
                    table_elements += '\t\t\t\t\t<input type="checkbox" class="language" name="language" value="Fremdsprache" style="margin-left: 5px" onclick="changeCheckbox(this)" checked="checked" /> <label for="language">Fremdsprache</label>\n'

            table_elements += "\t\t\t\t\t" + segment_buttons() + "\n"
            table_elements += "\t\t\t\t\t</div>\n"
            table_elements += '\t\t\t\t\t<p class="form-control">'
        table_elements += f"<span id=\"{str(i)}\" tabindex=\"{str(i+1)}\" onclick=\"changeVideo({str(i)})\" contenteditable=\"true\" class=\"segment\" title=\"{str(datetime.timedelta(seconds=round(segment['start'], 0)))} - {str(datetime.timedelta(seconds=round(segment['end'],0)))}\">{segment['text'].strip().replace('ß', 'ss')}</span>"
        table_elements += "\n"
        if combine_speaker:
            last_speaker = segment["speaker"][-1]
        else:
            last_speaker = ""

    content += table_elements

    content += "\t\t\t</p></div>\n"
    content += "\t\t</div>\n"
    content += "\t</div>\n"
    content += "</body>\n"
    content += "</html>\n\n"
    return content


def javascript(data, file_path, encode_base64, file_name):
    speakers = sorted(
        set(
            [
                segment["speaker"]
                for segment in data
                if segment["speaker"] is not "unknown"
            ]
        )
    )
    n_speakers = len(speakers)
    for i in range(ADDITIONAL_SPEAKERS):
        speakers.append(str(n_speakers + i).zfill(2))
    speakers.append("unknown")

    speakers_array = "var speakers = Array("
    for idx, speaker in enumerate(speakers):
        if speaker is not "unknown":
            speakers_array += f'"IN_SPEAKER_{str(idx).zfill(2)}", '
    if len(speakers) > 1:
        speakers_array = speakers_array[:-2] + ")"
    else:
        speakers_array += ")"
    number_of_speakers = len(
        set(
            [
                segment["speaker"]
                for segment in data
                if segment["speaker"] is not "unknown"
            ]
        )
    )
    content = """<script language="javascript">\n"""
    content += f'var fileName = "{file_name.split(".")[0]}"\n'
    content += """var source = Array(null, null, null, null, null)
var outputs = Array(null, null, null, null, null)\n"""
    content += speakers_array + "\n"
    content += f"for(var j = 0; j < speakers.length; j++)" + " {\n"
    content += """\tsource[j] = document.getElementById(speakers[j]);
\toutputs[j] = document.getElementsByClassName("OUT_SPEAKER_" + pad(j, 2));

\tinputHandler = function(e) {
\t\tfor(var i = 0; i < outputs[parseInt(e.target.id.slice(-2))].length; i++) {
\t\t\toutputs[parseInt(e.target.id.slice(-2))][i].innerText = e.target.textContent
\t\t\t//if (e.target.textContent == "") {
\t\t\t\t//outputs[parseInt(e.target.id.slice(-2))][i].innerText = "SPEAKER_" + pad(parseInt(e.target.id.slice(-2)), 2);
\t\t\t//}
\t\t}
\t}

\tsource[j].addEventListener('input', inputHandler);
\tsource[j].addEventListener('propertychange', inputHandler);
}
"""
    if not encode_base64:
        content += """
source_video_field = document.getElementById("source");

inputHandler = function(e) {
    document.getElementById("player").src = e.target.textContent;
}

source_video_field.addEventListener('input', inputHandler);
source_video_field.addEventListener('propertychange', inputHandler);
"""

    content += """
function hashCode(s) {
  var hash = 0,
    i, chr;
  if (s.length === 0) return hash;
  for (i = 0; i < s.length; i++) {
    chr = s.charCodeAt(i);
    hash = ((hash << 5) - hash) + chr;
    hash |= 0; // Convert to 32bit integer
  }
  return hash;
}

var hash_field = document.getElementById("hash");  
hash_field.textContent = hashCode(document.getElementById("editor").textContent)

function handleBeforeInput(e) {
    if (e.inputType === "deleteByCut" || e.inputType === "deleteContentBackward" || e.inputType === "deleteContentForward") {
    } else if (e.data === null && e.dataTransfer) {
        e.preventDefault()
        document.execCommand("insertText", false, e.dataTransfer.getData("text/plain"))
    } else if (e.data === null && e.dataTransfer === null) {
        e.preventDefault()
    }
}

document.getElementsByClassName("wrapper")[0].addEventListener('beforeinput', handleBeforeInput);

var vid = document.getElementsByTagName("video")[0];
vid.ontimeupdate = function() {highlightFunction()};"""
    content += "\n"

    content += "var timestamps = "
    timestamps = "Array("
    for segment in data:
        timestamps += f"Array({segment['start']}, {segment['end']}), "
    if len(data) > 0:
        timestamps = timestamps[:-2] + ");"
    else:
        timestamps += ");"
    content += timestamps
    content += "\n"

    content += """vid.currentTime = 0.0;
highlightFunction();

function pad(num, size) {
    num = num.toString();
    while (num.length < size) num = "0" + num;
    return num;
}

function downloadClick() {
    var content = document.documentElement.innerHTML;
    var path = window.location.pathname;
    var page = path.split("/").pop();
    download(content, "html")
}

function viewerClick() {
    var content = document.documentElement.innerHTML;
    var path = window.location.pathname;
    var page = path.split("/").pop();
    downloadViewer(content, "html")
}

function textClick() {
    var content = document.documentElement.innerHTML;
    var path = window.location.pathname;
    var page = path.split("/").pop();
    downloadText(content, "txt")
}

function download(content, fileType) {
    var link = document.getElementById("download-link");
    var file = new Blob([content], {type: fileType});
    var downloadFile = fileName + "." + fileType;
    link.href = URL.createObjectURL(file);
    link.download = downloadFile;
}

function changeCheckbox(checkbox) {
	console.log(checkbox.getAttribute("checked"))
	if (checkbox.getAttribute("checked") != null) {
		checkbox.removeAttribute("checked")
	} else {
		checkbox.setAttribute("checked", "checked")
	}
}

function downloadViewer(content, fileType) {
    var link = document.getElementById("viewer-link");
	var ignore_lang = document.getElementById("ignore_lang").checked;
	var current_pos=0, current_speaker_start=0, current_speaker_end=0, current_speaker=0, current_end_span=0, next_span_start=0, next_speaker_start=0, next_speaker=0;
	var same_speaker = false;
	
    content = content.replaceAll('contenteditable="true"', 'contenteditable="false"');
    content = content.replaceAll('<p class="form-control">', '<p>');
    content = content.replaceAll('class="viewer-hidden"', 'hidden');
    content = content.replaceAll('class="viewer-disabled"', 'class="form-control" disabled');
    content = content.replaceAll('video.pause();', '');
    
	
	index_script = content.indexOf("<script language")
    content_script = content.substr(index_script, content.length)
	content = content.substr(0, index_script)
	content_header = content.substr(0, content.indexOf('id="editor">') + 'id="editor">'.length)
	content = content.substr(content.indexOf('id="editor">'), content.length)

	content_out = ""
                
	next_speaker_start = content.indexOf('selected="selected">') + 'selected="selected">'.length
	next_speaker_end = content.indexOf('</option>', next_speaker_start)

	
    while(next_speaker_start > 'selected="selected">'.length) {
		if (ignore_lang) {
			var d = document.createElement('html');
			d.innerHTML = content;
			first_element = d.querySelector('.language');
		}
		skip = ignore_lang && (!(first_element == null) && first_element.checked)

		if (!(same_speaker)) {
			if (!skip) {
				current_speaker = content.slice(next_speaker_start, next_speaker_end)
			}
				current_timestamp_start = content.indexOf('<span contenteditable="false">') + '<span contenteditable="false">'.length
				current_timestamp_end = content.indexOf('</span>')
				current_timestamp = content.slice(current_timestamp_start, current_timestamp_end)
			if (!skip) {
				content_out = content_out + '<div class="form-control bg-secondary text-white" disabled style="display: block; margin-top: 0.5rem;">\\n'
				content_out = content_out + current_speaker + ' (' + current_timestamp + ')\\n</div>\\n'
			}
		}
		current_text_start = content.indexOf('<p>', current_timestamp_end)
		current_text_end = content.indexOf('</p>', current_text_start) + '</p>'.length
		current_text = content.slice(current_text_start, current_text_end)
		if (!skip){
			content_out = content_out + current_text.replaceAll('<p>', '<span>').replaceAll('</p>', '</span>') + '\\n'
		}
		content = content.substr(current_text_end, content.length)
		
		next_speaker_start = content.indexOf('selected="selected">') + 'selected="selected">'.length

		if (next_speaker_start > 'selected="selected">'.length) {
			next_speaker_end = content.indexOf('</option>', next_speaker_start)
			same_speaker = (current_speaker === content.slice(next_speaker_start, next_speaker_end))
			current_timestamp_end = next_speaker_end
		}
    }
    var file = new Blob([content_header + '\\n' + content_out + '\\n' + content_script], {type: fileType});
    var downloadFile = fileName + "_viewer." + fileType;
    link.href = URL.createObjectURL(file);
    link.download = downloadFile;
}

function downloadText(content, fileType) {
    var content_out = ''
    var link = document.getElementById("text-link");   
	var ignore_lang = document.getElementById("ignore_lang").checked; 
	var current_pos=0, current_speaker_start=0, current_speaker_end=0, current_speaker=0, current_end_span=0, next_span_start=0, next_speaker_start=0, next_speaker=0;
	var same_speaker = false;
	
    content = content.replaceAll('contenteditable="true"', 'contenteditable="false"');
    content = content.replaceAll('<p class="form-control">', '<p>');
    content = content.replaceAll('class="viewer-hidden"', 'hidden');
    content = content.replaceAll('class="viewer-disabled"', 'class="form-control" disabled');
    content = content.replaceAll('video.pause();', '');
    
	index_script = content.indexOf("<script language")
	content = content.substr(0, index_script)
	content = content.substr(content.indexOf('id="editor">'), content.length)

	content_out = ""
                
	next_speaker_start = content.indexOf('selected="selected">') + 'selected="selected">'.length
	next_speaker_end = content.indexOf('</option>', next_speaker_start)

    while(next_speaker_start > 'selected="selected">'.length) {
		if (ignore_lang) {
			var d = document.createElement('html');
			d.innerHTML = content;
			first_element = d.querySelector('.language');
		}
		skip = ignore_lang && (!(first_element == null) && first_element.checked)

		if (!(same_speaker)) {
			if (!skip) {
				current_speaker = content.slice(next_speaker_start, next_speaker_end)
			}
			current_timestamp_start = content.indexOf('<span contenteditable="false">') + '<span contenteditable="false">'.length
			current_timestamp_end = content.indexOf('</span>')
			current_timestamp = content.slice(current_timestamp_start, current_timestamp_end)
			
			if (!skip) {
				if (content_out.length > 0) {
					content_out = content_out + '\\n\\n'
				}
				content_out = content_out + current_speaker + ' (' + current_timestamp + '):\\n'
			}
		}
		current_text_start = content.indexOf('<p>', current_timestamp_end)
		current_text_end = content.indexOf('</p>', current_text_start) + '</p>'.length
		current_text = content.slice(current_text_start, current_text_end)
		current_text = current_text.replaceAll('<p>', '').replaceAll('</p>', '').replace(/\\u00a0/g, " ");
		current_text = current_text.slice(current_text.indexOf('>') + 1, current_text.indexOf('</span>'))
		if (!skip) {
			content_out = content_out + current_text + ' '
		}

		content = content.substr(current_text_end, content.length)
		
		next_speaker_start = content.indexOf('selected="selected">') + 'selected="selected">'.length

		if (next_speaker_start > 'selected="selected">'.length) {
			next_speaker_end = content.indexOf('</option>', next_speaker_start)
			same_speaker = (current_speaker === content.slice(next_speaker_start, next_speaker_end))
			current_timestamp_end = next_speaker_end
		}
    }

    var file = new Blob([content_out], {type: fileType});
    var downloadFile = fileName + "." + fileType;
    link.href = URL.createObjectURL(file);
    link.download = downloadFile;
}

function selectChange(selectObject) {
    var idx = selectObject.selectedIndex
    selectObject.innerHTML = selectObject.innerHTML.replace('selected="selected"', '')
    selectObject.innerHTML = selectObject.innerHTML.replace('class="OUT_SPEAKER_' + pad(idx, 2) + '"', 'class="OUT_SPEAKER_' + pad(idx, 2) + '" selected="selected"')
}

function highlightFunction() {
    var i = 0;
    while (i < timestamps.length) {
      if (vid.currentTime >= timestamps[i][0] && vid.currentTime < timestamps[i][1]){
		var element = document.getElementById(i.toString())
		if (element) {
			element.style.backgroundColor = "#9ddbff";
			var rect = element.getBoundingClientRect();
			var viewHeight = window.innerHeight
			if (rect.bottom < 40 || rect.top - viewHeight >= -40){
				element.scrollIntoView({ block: "center" });
			}
		}
      } else {
        var element = document.getElementById(i.toString())
		if (element) {
			element.style.backgroundColor = "white";
		}
      }
      i++;
    }
}

function insertAfter(referenceNode, newNode) {
  referenceNode.parentNode.insertBefore(newNode, referenceNode.nextSibling);
}

function addRow(button) {
	var previous_row = button.parentElement.parentElement;
	var new_row = document.createElement('div');
	new_row.innerHTML = previous_row.innerHTML
	text_span = new_row.getElementsByClassName("segment")[0]
	text_span.textContent = "Neues Textsegment"
	text_span.removeAttribute('id');
	text_span.removeAttribute('onclick');
    text_span.style.backgroundColor = "white";
	insertAfter(previous_row, new_row);
}

function removeRow(button) {
    if (confirm("Sprachsegment entfernen?\\nDrücke OK um das Sprachsegment zu entfernen.")){
	    button.parentElement.parentElement.remove();
    }
}

document.addEventListener('keydown', (event) => {
    if(event.ctrlKey && event.keyCode == 32) {
		event.preventDefault();
		var v = document.getElementsByTagName("video")[0];
    	if (video.paused) v.play(); 
		else v.pause();
  	}
});

function isNumeric(str) {
  if (typeof str != "string") return false 
  return !isNaN(str) && 
         !isNaN(parseFloat(str))
}

function changeVideo(id) {
    var video = document.getElementsByTagName("video")[0];
	var delayElement = document.getElementById("delay");
    var content = delayElement.innerText;
    content = content.replaceAll('s', '');
	var delay = 0;

	if (isNumeric(content)){
		delay = parseFloat(content)
	}
    video.currentTime = Math.max(timestamps[id][0] - delay, 0);
    video.pause();
}

"""

    content += "</script>"

    return content
