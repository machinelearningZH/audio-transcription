from nicegui import ui
from config import ROOT, ONLINE


@ui.page('/help')
def help():
	#todo, upload mehrere dateien, unterstützte formate
	with ui.column():
		with ui.header(elevated=True).style('background-color: #0070b4;').props('fit=scale-down').classes('q-pa-xs-xs'):
			ui.image(ROOT + 'banner.png').style('height: 90px; width: 443px;')
		with ui.expansion('Dateien hochladen', icon='upload_file').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('Du kannst eine oder mehrere Dateien zum Transkribieren hochladen. Drücke dazu auf den "+"-Knopf oder ziehe die Dateien in den Upload-Bereich. Das Transkriptionsmodell (Whisper) von Transcribo kann die meisten gängigen Video- und Audio-Dateiformate verarbeiten. Eine Liste aller unterstützten Formate findest du hier: [ffmpeg.org](https://www.ffmpeg.org/general.html#Supported-File-Formats_002c-Codecs-or-Features)')
			ui.image(ROOT + 'help/upload.png').style('width: min(40vw, 400px)')
		with ui.expansion('Editor öffnen und speichern', icon='open_in_new').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('''Der Editor kann entweder lokal oder auf dem Server geöffnet werden. Wenn du den Editor auf dem Server öffnest, werden deine Änderungen dort gespeichert und das initiale Transkript wird überschrieben. Wenn du den Editor lokal öffnest, wird eine Editor-Datei in deinem Download-Ordner abgelegt. Jedes Mal, wenn du auf "speichern" klickst, wird eine neue Editor-Datei in deinem Download-Ordner erzeugt. Dadurch hast du alle deine Änderungen auf deinem Gerät und behältst alte Versionen.''')
			ui.image(ROOT + 'help/open.png').style('width: min(40vw, 400px)')
			ui.markdown('Achtung: Transcribo speichert nicht automatisch, bitte oft zwischenspeichern!')
			ui.image(ROOT + 'help/editor_buttons_save.png').style('width: min(40vw, 400px)')
		with ui.expansion('Editor Grundfunktionen', icon='edit').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('''#####Sprachsegmente
Im Editor ist das Transkript in einzelne Sprachsegmente aufgetrennt. Ein Sprachsegment umfasst in etwa das, was ein Sprecher zwischen zwei Pausen gesagt hat. Wir trennen sie so auf, damit man den Sprecher für jedes Segment einzeln anpassen kann. Beim Export des Textes oder beim Erstellen eines Viewers werden die Sprachsegmente desselben Sprechers wieder zusammengefügt.

Mit den gekennzeichneten Knöpfen kann ein Sprachsegment hinzugefügt oder entfernt werden.''')
			ui.image(ROOT + 'help/segment_add_delete.png').style('width: min(40vw, 400px)')
			ui.markdown('''#####Sprecher
Sprecher können im Editor auf der linken Seite unbenannt werden.''')
			ui.image(ROOT + 'help/editor_buttons_speaker.png').style('width: min(40vw, 400px)')
			ui.markdown('Bei jedem Sprachsegment kann der Sprecher geändert werden.')
			ui.image(ROOT + 'help/segment_speaker.png').style('width: min(40vw, 400px)')
			ui.markdown('''#####Wiedergabe
Die Wiedergabegeschwindigkeit einer Aufnahme kann im Player angepasst werden.''')
			ui.image(ROOT + 'help/player_speed.png').style('width: min(40vw, 400px)')
			ui.markdown('''#####Zeitverzögerung
Wenn du auf ein Sprachsegment klickst, springt das Video an die entsprechende Stelle. Falls du nicht direkt beim Segment beginnen möchtest, kannst du auf der linken Seite eine Verzögerungszeit angeben.''')
		with ui.expansion('Editor Tastenkombinationen', icon='keyboard').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('''Du kannst die folgenden Tastenkombinationen im Editor verwenden.\n
**Tabulator:** Zum nächsten Sprachsegment springen\n
**Shift + Tabulator:** Zum vorhergehenden Sprachsegment springen\n
**Ctrl + Pfeiltasten:** Von Wort zu Wort springen\n
**Shift + Ctrl + Pfeiltasten:** Wörter markieren\n
**Ctrl + Space:** Video Start/Stop (funktioniert zur Zeit nur im offline Editor)''')
		with ui.expansion('Fremdsprachen', icon='translate').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('Transcribo markiert alle Sprachsegmente, die weder auf Deutsch, Schweizerdeutsch oder Englisch sind, als "Fremdsprache". Du kannst falsch erkannte Sprachsegmente korrigieren.')
			ui.image(ROOT + 'help/segment_language.png').style('width: min(40vw, 400px)')
			ui.markdown('Beim Export als Textdatei oder Viewer kannst du auswählen, ob Fremdsprachen entfernt werden sollen.')
			ui.image(ROOT + 'help/editor_buttons_language.png').style('width: min(40vw, 400px)')
		with ui.expansion('Viewer', icon='visibility').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('Im Editor kannst du einen Viewer erstellen.')
			ui.image(ROOT + 'help/editor_buttons_viewer.png').style('width: min(40vw, 400px)')
			ui.markdown('Der Viewer zeigt aufeinanderfolgende Sprachsegmente des gleichen Sprechers kompakt an. In Klammern hinter dem Namen des Sprechenden wird der Zeitstempel des ersten Sprachsegments angezeigt. Der Viewer ermöglicht es, das Transkript übersichtlich zu lesen und mit der Aufnahme zu vergleichen. Der Text kann nicht mehr bearbeitet werden.')
			ui.image(ROOT + 'help/viewer.png').style('width: min(40vw, 400px)')
		with ui.expansion('Textexport', icon='description').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('Als Alternative zum Viewer kann das Transkript auch als Rohtext exportiert werden. Aufeinanderfolgende Sprachsegmente des gleichen Sprechers werden dabei ebenfalls kombiniert.')
			ui.image(ROOT + 'help/editor_buttons_text.png').style('width: min(40vw, 400px)')
		with ui.expansion('Datenspeicherung', icon='save').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			if ONLINE:
				ui.markdown('Wenn du eine Datei hochlädst, kannst du später wieder auf das fertige Transkript zugreifen. Dafür musst du mit demselben Windows-Useraccount, am selben Rechner und mit demselben Browser auf Transcribo zugreifen. Alle deine Transkripte bleiben erhalten, sofern du sie nicht selbst löschst. Wenn du jedoch 30 Tage lang nicht auf Transcribo zugreifst, werden deine Transkripte entfernt. Bitte lade den Editor herunter, um deine Transkripte langfristig zu speichern.')
			else:
				ui.markdown('Wenn du eine Datei hochlädst, kannst du später wieder auf das fertige Transkript zugreifen. Dafür musst du mit demselben Windows-Useraccount, am selben Rechner und mit demselben Browser auf Transcribo zugreifen. Alle deine Transkripte bleiben erhalten, sofern du sie nicht selbst löschst.')
		with ui.expansion('Vokabular', icon='menu_book').classes('w-full no-wrap').style('width: min(80vw, 800px)'):
			ui.markdown('Im Menü "Vokabular" kannst du Wörter zum bestehenden Vokabular hinzufügen. Das hilft zum Beispiel, selten verwendete Namen oder Bezeichnungen besser zu transkribieren. Du kannst die Wörter durch Leerzeichen getrennt oder zeilenweise angeben.')
