import time, os, shutil, zipfile, datetime, base64
from os import listdir
from os.path import isfile, join
from functools import partial

from nicegui import ui, events, app

from util import time_estimate
from config import ONLINE, ROOT, WINDOWS, STORAGE_SECRET, SSL_CERTFILE, SSL_KEYFILE
from help import help

ONLINE = False

if WINDOWS:
	os.environ["PATH"] += os.pathsep + "ffmpeg/bin"
	os.environ["PATH"] += os.pathsep + "ffmpeg"
	
user_storage = {}


# read in all files of the user and set the file status if known
def read_files(user_id):
	user_storage[user_id]['file_list'] = []
	if os.path.exists(ROOT + 'data/in/' + user_id): 
		user_path = ROOT + 'data/in/' + user_id
		for f in listdir(user_path): 
			if isfile(join(user_path, f)) and not f == 'hotwords.txt':
				file_status = [f, 'Datei in Warteschlange. Geschätzte Wartezeit: ', 0.0, 0, os.path.getmtime(join(user_path, f))]
				if isfile(join(ROOT + 'data/out/' + user_id, f + '.html')):
					file_status[1] = 'Datei transkribiert'
					file_status[2] = 100.0
					file_status[3] = 0
				else:				
					estimated_time, _ = time_estimate(join(user_path, f), ONLINE)
					if estimated_time == -1:
						estimated_time = 0
					file_status[3] = estimated_time

				user_storage[user_id]['file_list'].append(file_status)

		files_in_queue = []
		for u in user_storage:
			for f in user_storage[u]['file_list']:
				if 'updates' in user_storage[u] and len(user_storage[u]['updates']) > 0:
					if user_storage[u]['updates'][0] == f[0]:
						f = user_storage[u]['updates']
				if f[2] < 100.0:
					files_in_queue.append(f)

		for file_status in user_storage[user_id]['file_list']:
			estimated_wait_time = 0
			for f in files_in_queue:
				if f[4] < file_status[4]:
					estimated_wait_time += f[3]
			if file_status[2] < 100.0:
				file_status[1] += str(datetime.timedelta(seconds=round(estimated_wait_time + file_status[3])))

	if os.path.exists(ROOT + 'data/error/' + user_id): 
		user_path = ROOT + 'data/error/' + user_id
		for f in listdir(user_path): 
			if isfile(join(user_path, f)) and '.txt' not in f:
				text = 'Transkription fehlgeschlagen'
				with open(join(user_path, f) + '.txt', 'r') as txtf:
					content = txtf.read()
					if len(content) > 0:
						text = content
				file_status = [f, text, -1, 0, os.path.getmtime(join(user_path, f))]
				if f not in user_storage[user_id]['known_errors']:
					user_storage[user_id]['known_errors'].update(f)
				user_storage[user_id]['file_list'].append(file_status)

	user_storage[user_id]['file_list'] = sorted(user_storage[user_id]['file_list'])

# save uploaded file to disk
async def handle_upload(e: events.UploadEventArguments, user_id):
	if not os.path.exists(ROOT + 'data/in/' + user_id): 
		os.makedirs(ROOT + 'data/in/' + user_id) 
	if not os.path.exists(ROOT + 'data/out/' + user_id): 
		os.makedirs(ROOT + 'data/out/' + user_id) 
	file_name = e.name

	if os.path.exists(ROOT + 'data/error/' + user_id):
		if file_name in user_storage[user_id]['known_errors']:
			user_storage[user_id]['known_errors'].remove(file_name)
		if os.path.exists(join(ROOT + 'data/error/' + user_id, file_name)):
			os.remove(join(ROOT + 'data/error/' + user_id, file_name))
		if os.path.exists(join(ROOT + 'data/error/' + user_id, file_name + '.txt')):
			os.remove(join(ROOT + 'data/error/' + user_id, file_name + '.txt'))	

	# if the file name already exists, append a number of up to 10000 to the name, if someone uploads 10001 copies of the same file, it will ignore the file
	for i in range(10000):
		if isfile(ROOT + 'data/in/' + user_id + '/' + file_name):
			file_name = '.'.join(e.name.split('.')[:-1]) + f'_{str(i)}.' + ''.join(e.name.split('.')[-1:])

	if user_id + 'vocab' in app.storage.user and len(app.storage.user[user_id + 'vocab'].strip()) > 0:
		with open(ROOT + 'data/in/' + user_id + '/hotwords.txt', 'w') as f:
			f.write(app.storage.user[user_id + 'vocab'])
	elif isfile(ROOT + 'data/in/' + user_id + '/hotwords.txt'):
		os.remove(ROOT + 'data/in/' + user_id + '/hotwords.txt')

	with open(ROOT + 'data/in/' + user_id + '/' + file_name, 'wb') as f:
		f.write(e.content.read())
	
def handle_reject(e: events.GenericEventArguments):
	ui.notify('Ungültige Datei. Es können nur Audio/Video-Dateien unter 12GB transkribiert werden.')
	
def handle_added(e: events.GenericEventArguments, user_id, upload_element, refresh_file_view):
	upload_element.run_method('removeUploadedFiles')
	refresh_file_view(user_id = user_id, refresh_queue = True, refresh_results = False)

def prepare_download(file_name, user_id):
	full_file_name = join(ROOT + 'data/out/' + user_id, file_name + '.html')

	with open(full_file_name, 'r', encoding='utf-8') as f:
		content = f.read()
	if os.path.exists(full_file_name + 'update'): 
		with open(full_file_name + 'update', 'r', encoding='utf-8') as f:
			new_content = f.read()
		start_index = content.find('</nav>') + len('</nav>')
		end_index = content.find('var fileName = ')

		content = content[:start_index] + new_content + content[end_index:]
																					
		with open(full_file_name, 'w', encoding = 'utf-8') as f:
			f.write(content)

		os.remove(full_file_name + 'update')

	content = content.replace('<div>Bitte den Editor herunterladen, um den Viewer zu erstellen.</div>', 
							  '<a href="#" id="viewer-link" onclick="viewerClick()" class="btn btn-primary">Viewer erstellen</a>')
	if not 'var base64str = ' in content:
		with open(join(ROOT + 'data/out/' + user_id, file_name + '.mp4'), "rb") as videoFile:
			video_base64 = base64.b64encode(videoFile.read()).decode('utf-8')
        
		video_content = f'var base64str = "{video_base64}";'
		video_content += '''
var binary = atob(base64str);
var len = binary.length;
var buffer = new ArrayBuffer(len);
var view = new Uint8Array(buffer);
for (var i = 0; i < len; i++) {
    view[i] = binary.charCodeAt(i);
}
              
var blob = new Blob( [view], { type: "video/MP4" });

var url = URL.createObjectURL(blob);

var video = document.getElementById("player")

setTimeout(function() {
  video.pause();
  video.setAttribute('src', url);
}, 100);
</script>
'''
		content = content.replace('</script>', video_content)

	with open(full_file_name + 'final', 'w', encoding = 'utf-8') as f:
		f.write(content)

async def download_editor(file_name, user_id):
	prepare_download(file_name, user_id)
	ui.download(src = join(ROOT + 'data/out/' + user_id, file_name + '.htmlfinal'), filename = file_name.split('.')[0] + '.html')

async def download_srt(file_name, user_id):
	ui.download(src = join(ROOT + 'data/out/' + user_id, file_name + '.srt'), filename = file_name.split('.')[0] + '.srt')

async def open_editor(file_name, user_id):
	full_file_name = join(ROOT + 'data/out/' + user_id, file_name + '.html')
	with open(full_file_name, 'r', encoding='utf-8') as f:
		user_storage[user_id]['content'] = f.read()
		print(user_id)
		user_storage[user_id]['content'] = user_storage[user_id]['content'].replace('<video id="player" width="100%" style="max-height: 320px" src="" type="video/MP4" controls="controls" position="sticky"></video>',
																			  		'<video id="player" width="100%" style="max-height: 320px" src="/data/' + str(user_id) + '/' + file_name + '.mp4' + '" type="video/MP4" controls="controls" position="sticky"></video>')
		user_storage[user_id]['content'] = user_storage[user_id]['content'].replace('<video id="player" width="100%" style="max-height: 250px" src="" type="video/MP4" controls="controls" position="sticky"></video>',
																			  		'<video id="player" width="100%" style="max-height: 250px" src="/data/' + str(user_id) + '/' + file_name + '.mp4' + '" type="video/MP4" controls="controls" position="sticky"></video>')

	user_storage[user_id]['full_file_name'] = full_file_name
	ui.open(editor, new_tab=True)
	
async def download_all(user_id):
	with zipfile.ZipFile(ROOT + 'data/out/' + user_id + '/' + 'transcribed_files.zip', 'w', allowZip64=True) as myzip:
		for file_name in user_storage[user_id]['file_list']:
			if file_name[2] == 100.0:
				prepare_download(file_name[0], user_id)
				myzip.write(ROOT + 'data/out/' + user_id + '/' + file_name[0] + '.htmlfinal', file_name[0] + '.html')

	ui.download(ROOT + 'data/out/' + user_id + '/' + 'transcribed_files.zip')

def delete(file_name, user_id, refresh_file_view):
	if os.path.exists(join(ROOT + 'data/in/' + user_id, file_name)):
		os.remove(join(ROOT + 'data/in/' + user_id, file_name))
	for suffix in ['', '.txt', '.html', '.mp4', '.srt']:
		if os.path.exists(join(ROOT + 'data/out/' + user_id, file_name + suffix)):
			os.remove(join(ROOT + 'data/out/' + user_id, file_name + suffix))
	if os.path.exists(join(ROOT + 'data/error/' + user_id, file_name)):
		os.remove(join(ROOT + 'data/error/' + user_id, file_name))
	if os.path.exists(join(ROOT + 'data/error/' + user_id, file_name + '.txt')):
		os.remove(join(ROOT + 'data/error/' + user_id, file_name + '.txt'))
	if os.path.exists(join(ROOT + 'data/out/' + user_id, file_name + '.htmlupdate')): 
		os.remove(join(ROOT + 'data/out/' + user_id, file_name + '.htmlupdate'))

	refresh_file_view(user_id = user_id, refresh_queue = True, refresh_results = True)

# periodically check if a file is being transcribed and calulate its estimated progress
def listen(user_id, refresh_file_view):
	user_path = ROOT + 'data/worker/' + user_id + '/'

	if os.path.exists(user_path):
		for f in listdir(user_path): 
			if isfile(join(user_path, f)):
				f = f.split('_')
				estimated_time = f[0]
				start = f[1]
				file_name = '_'.join(f[2:])
				progress = min(0.975, (time.time() - float(start)) / float(estimated_time))
				estimated_time_left = round(max(1, float(estimated_time) - (time.time() - float(start))))
				if os.path.exists(join(ROOT + 'data/in/' + user_id + '/', file_name)):
					user_storage[user_id]['updates'] = [file_name, 'Datei wird transkribiert. Geschätzte Bearbeitungszeit: ' + str(datetime.timedelta(seconds=estimated_time_left)), progress, estimated_time_left, os.path.getmtime(join(ROOT + 'data/in/' + user_id + '/'
, file_name))]
				else:
					os.remove(join(user_path, '_'.join(f)))
				refresh_file_view(user_id = user_id, refresh_queue = True, refresh_results = user_storage[user_id]['file_in_progress'] is not None and not user_storage[user_id]['file_in_progress'] == file_name)
				user_storage[user_id]['file_in_progress'] = file_name
				return

		if 'updates' in user_storage[user_id] and len(user_storage[user_id]['updates']) > 0:
			user_storage[user_id]['updates'] = []
			user_storage[user_id]['file_in_progress'] = None
			refresh_file_view(user_id = user_id, refresh_queue = True, refresh_results = True)
		else:
			refresh_file_view(user_id = user_id, refresh_queue = True, refresh_results = False)

def update_hotwords(user_id):
	if 'textarea' in user_storage[user_id]:
		app.storage.user[user_id + 'vocab'] = user_storage[user_id]['textarea'].value

@ui.page('/editor')
async def editor():
	async def handle_save(full_file_name):
		content = ''
		for i in range(100):
			content_tmp = await ui.run_javascript('''
var content = String(document.documentElement.innerHTML);
var start_index = content.indexOf('<!--start-->') + '<!--start-->'.length;
content = content.slice(start_index, content.indexOf('var fileName = ', start_index))
content = content.slice(content.indexOf('</nav>') + '</nav>'.length, content.length)
return content.slice(''' + str(i * 500_000) + ',' + str(((i + 1) * 500_000)) + ')' , timeout = 60.0)
			content += content_tmp
			if len(content_tmp) < 500_000:
				break

		with open(full_file_name + 'update', 'w', encoding = 'utf-8') as f:
			f.write(content.strip())
		
		ui.notify('Änderungen gespeichert.')

	if ONLINE:
		user_id = str(app.storage.browser['id'])
	else:
		user_id = 'local'

	app.add_media_files('/data/' + user_id, join(ROOT + 'data/out/' + user_id))
	if user_id in user_storage and 'full_file_name' in user_storage[user_id]:
		full_file_name = user_storage[user_id]['full_file_name']
		ui.on('editor_save', lambda e: handle_save(full_file_name))
		ui.add_body_html('<!--start-->')
		
		if os.path.exists(full_file_name + 'update'): 
			with open(full_file_name + 'update', 'r', encoding='utf-8') as f:
				new_content = f.read()
			start_index = user_storage[user_id]['content'].find('</nav>') + len('</nav>')
			end_index = user_storage[user_id]['content'].find('var fileName = ')
			user_storage[user_id]['content'] = user_storage[user_id]['content'][:start_index] + new_content + user_storage[user_id]['content'][end_index:]
			
		user_storage[user_id]['content'] = user_storage[user_id]['content'].replace('<a href ="#" id="viewer-link" onClick="viewerClick()" class="btn btn-primary">Viewer erstellen</a>',
																					'<div>Bitte den Editor herunterladen, um den Viewer zu erstellen.</div>')
		user_storage[user_id]['content'] = user_storage[user_id]['content'].replace('<a href="#" id="viewer-link" onclick="viewerClick()" class="btn btn-primary">Viewer erstellen</a>',
																					'<div>Bitte den Editor herunterladen, um den Viewer zu erstellen.</div>')
		ui.add_body_html(user_storage[user_id]['content'])

		ui.add_body_html('''<script language="javascript">
	var origFunction = downloadClick;
	downloadClick = function downloadClick() {
		emitEvent('editor_save');
	}
</script>''')
	else:
		ui.label('Session abgelaufen. Bitte öffne den Editor erneut.')

@ui.page('/')
async def main_page():
	@ui.refreshable
	def display_queue(user_id):
		for file_name in sorted(user_storage[user_id]['file_list'], key = lambda x: (x[2], -x[4], x[0])):
			if 'updates' in user_storage[user_id] and len(user_storage[user_id]['updates']) > 0:
				if user_storage[user_id]['updates'][0] == file_name[0] and file_name[2] < 100.0:
					file_name = user_storage[user_id]['updates']
			if file_name[2] < 100.0 and file_name[2] >= 0:
				ui.markdown('<b>' + file_name[0].replace('_', '\\_') + ':</b> ' + file_name[1])
				ui.linear_progress(value=file_name[2], show_value=False, size='10px').props('instant-feedback')
				ui.separator()	

	@ui.refreshable
	def display_results(user_id):
		any_file_ready = False
		for file_name in sorted(user_storage[user_id]['file_list'], key = lambda x: (x[2], -x[4], x[0])):
			if 'updates' in user_storage[user_id] and len(user_storage[user_id]['updates']) > 0:
				if user_storage[user_id]['updates'][0] == file_name[0] and file_name[2] < 100.0:
					file_name = user_storage[user_id]['updates']
			if file_name[2] >= 100.0:
				ui.markdown('<b>' + file_name[0].replace('_', '\\_') + '</b>')
				with ui.row():
					ui.button('Editor herunterladen (Lokal)', on_click=partial(download_editor, file_name=file_name[0], user_id=user_id)).props('no-caps')
					ui.button('Editor öffnen (Server)', on_click=partial(open_editor, file_name=file_name[0], user_id=user_id)).props('no-caps')
					ui.button('SRT-Datei', on_click=partial(download_srt, file_name=file_name[0], user_id=user_id)).props('no-caps')
					ui.button('Datei entfernen', on_click=partial(delete, file_name=file_name[0], user_id=user_id, refresh_file_view=refresh_file_view), color='red-5').props('no-caps')
					any_file_ready = True
				ui.separator()
			elif file_name[2] == -1:
				ui.markdown('<b>' + file_name[0].replace('_', '\\_') + ':</b> ' + file_name[1])
				ui.button('Datei entfernen', on_click=partial(delete, file_name=file_name[0], user_id=user_id, refresh_file_view=refresh_file_view), color='red-5').props('no-caps')
				ui.separator()	
		if any_file_ready:
			ui.button('Alle Dateien herunterladen', on_click=partial(download_all, user_id=user_id)).props('no-caps')

	def refresh_file_view(user_id, refresh_queue, refresh_results):
		num_errors = len(user_storage[user_id]['known_errors'])
		read_files(user_id)
		if refresh_queue:
			display_queue.refresh(user_id = user_id)
		if refresh_results or num_errors < len(user_storage[user_id]['known_errors']):
			display_results.refresh(user_id = user_id)

	def display_files(user_id):
		read_files(user_id)

		# display progress and buttons for each file
		with ui.card().classes('border p-4').style('width: min(60vw, 700px);'):
			display_queue(user_id = user_id)
			display_results(user_id = user_id)

	global user_storage
	
	if ONLINE:
		user_id = str(app.storage.browser['id'])
	else:
		user_id = 'local'
	user_storage[user_id] = {}
	user_storage[user_id]['uploaded_files'] = set()
	user_storage[user_id]['file_list'] = []
	user_storage[user_id]['transcribe_button'] = None
	user_storage[user_id]['content'] = ''
	user_storage[user_id]['content_filename'] = ''
	user_storage[user_id]['file_in_progress'] = None
	user_storage[user_id]['known_errors'] = set()

	if os.path.exists(ROOT + 'data/in/' + user_id + '/tmp'):
		shutil.rmtree(ROOT + 'data/in/' + user_id + '/tmp')

	read_files(user_id)

	# Create the UI
	with ui.column():
		with ui.header(elevated=True).style('background-color: #0070b4;').props('fit=scale-down').classes('q-pa-xs-xs'):
			ui.image(ROOT + 'banner.png').style('height: 90px; width: 443px;')
		with ui.row():
			# left side of the page. upload element and information
			with ui.column():
				with ui.card().classes('border p-4'):
					with ui.card().style('width: min(40vw, 400px)'):        
						upload_element = ui.upload(multiple=True, on_upload=partial(handle_upload, user_id=user_id), on_rejected=handle_reject, label='Dateien auswählen', auto_upload=True, max_file_size=12_000_000_000, max_files=100).props('accept="video/*, audio/*"').tooltip('Dateien auswählen').classes('w-full').style('width: 100%;')
						upload_element = upload_element.on("uploaded", partial(handle_added, user_id=user_id, upload_element=upload_element, refresh_file_view=refresh_file_view))

				label = ui.label('')
				ui.timer(2, partial(listen, user_id=user_id, refresh_file_view=refresh_file_view))
				with ui.expansion('Vokabular', icon='menu_book').classes('w-full no-wrap').style('width: min(40vw, 400px)') as expansion:
					user_storage[user_id]['textarea'] = ui.textarea(label='Vokabular', placeholder='Zürich\nUster\nUitikon', on_change=partial(update_hotwords, user_id)).classes('w-full h-full')
					if user_id + 'vocab' in app.storage.user and len(app.storage.user[user_id + 'vocab'].strip()) > 0:
						user_storage[user_id]['textarea'].value = app.storage.user[user_id + 'vocab']
						expansion.open()
				with ui.expansion('Informationen', icon='help_outline').classes('w-full no-wrap').style('width: min(40vw, 400px)'):
					ui.label('Diese Prototyp-Applikation wird vom Statistischen Amt Kanton Zürich entwickelt.')
					ui.label('Feedback und Wünsche sind jederzeit willkommen.')
					ui.label('Kontakt: dominik.frefel@statistik.ji.zh.ch')
				ui.button('Anleitung öffnen', on_click=lambda: ui.open(help, new_tab=True)).props('no-caps')

			# file view (on the right side of the page)
			display_files(user_id = user_id)
	
	
if __name__ in {"__main__", "__mp_main__"}:
	if ONLINE:
		ui.run(port=443, reload=False, title="Transcribo", ssl_certfile=SSL_CERTFILE, ssl_keyfile=SSL_KEYFILE, storage_secret=STORAGE_SECRET, favicon=ROOT + 'logo.png')
	else:
		ui.run(title="Transcribo", host='127.0.0.1', port=8080, storage_secret=STORAGE_SECRET, favicon=ROOT + 'logo.png')
