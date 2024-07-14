import sys
import os
import concurrent.futures
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QProgressBar, QMessageBox, QComboBox)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from anipy_api.provider.providers.yugen_provider import YugenProvider
from anipy_api.provider.providers.gogo_provider import GoGoProvider
from anipy_api.anime import Anime
from anipy_api.provider import LanguageTypeEnum

def titleGen(index, letter='E'):
    if index in range(9): return f'{letter}0{index+1}' if letter == 'E' else f'{letter}0{index}'
    if index == 9: return f'{letter}10' if letter == "E" else f'{letter}09'
    return f'{letter}{index+1}' if letter == 'E' else f'{letter}{index}'

def removeSymbols(string):
    return ''.join(e for e in string if e.isalnum() or e.isspace())

def fetch_episode(selectedAnime, e, selectedLanguage, signals):
    try:
        video = selectedAnime.get_video(
            episode=e,
            lang=selectedLanguage,
            preferred_quality=1080
        )
        signals.update_output.emit(f'Episode {e} succeeded\n')
        return e, video
    except Exception as exc:
        signals.update_output.emit(f'Episode {e} failed: {exc}\n')
        return e, None

class WorkerSignals(QObject):
    update_progress = pyqtSignal(int)
    update_output = pyqtSignal(str)

class AnimeDownloaderGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        # Providers
        self.provider = YugenProvider()
        self.ggp = GoGoProvider()
        self.anime_list = []

        # Worker signals
        self.signals = WorkerSignals()

    def initUI(self):
        # Font style for banners
        banner_font = QFont()
        banner_font.setBold(True)
        banner_font.setPointSize(24)

        # Banner Labels
        banner_label1 = QLabel('ANIME PLAYLIST CREATOR')
        banner_label1.setAlignment(Qt.AlignCenter)
        banner_label1.setFont(banner_font)

        # Layouts
        vbox = QVBoxLayout()
        vbox.addWidget(banner_label1)

        # Anime Name
        hbox1 = QHBoxLayout()
        lbl1 = QLabel('Enter Anime Name:')
        self.nameEdit = QLineEdit()
        hbox1.addWidget(lbl1)
        hbox1.addWidget(self.nameEdit)
        
        # Season
        hbox2 = QHBoxLayout()
        lbl2 = QLabel('Season:')
        self.seasonEdit = QLineEdit()
        self.seasonEdit.setText('1')
        hbox2.addWidget(lbl2)
        hbox2.addWidget(self.seasonEdit)
        
        # Version (Dub/Sub)
        hbox3 = QHBoxLayout()
        lbl3 = QLabel('Dub or Sub:')
        self.verComboBox = QComboBox()
        self.verComboBox.addItems(['Sub', 'Dub'])
        self.verComboBox.setCurrentText('Sub')
        hbox3.addWidget(lbl3)
        hbox3.addWidget(self.verComboBox)
        
        # Search Button
        self.searchBtn = QPushButton('Search', self)
        self.searchBtn.clicked.connect(self.search_anime)
        
        # Anime Selection ComboBox
        self.animeComboBox = QComboBox(self)
        
        # Create Playlist Button
        self.createBtn = QPushButton('Create Playlist', self)
        self.createBtn.clicked.connect(self.create_playlist)
        
        # Progress
        self.progress = QProgressBar(self)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        
        # Output
        self.output = QTextEdit(self)
        self.output.setReadOnly(True)
        
        # Add layouts to the main layout
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addLayout(hbox3)
        vbox.addWidget(self.searchBtn)
        vbox.addWidget(QLabel('Select Anime:'))
        vbox.addWidget(self.animeComboBox)
        vbox.addWidget(self.createBtn)
        vbox.addWidget(self.progress)
        vbox.addWidget(self.output)
        
        self.setLayout(vbox)
        
        self.setWindowTitle('Anime Playlist Creator')
        self.setGeometry(300, 300, 600, 400)
        self.show()

        # Quit Button
        self.quitBtn = QPushButton('Quit', self)
        self.quitBtn.clicked.connect(self.close)
        vbox.addWidget(self.quitBtn)

    def search_anime(self):
        name = self.nameEdit.text()
        self.output.clear()
        self.output.append("Searching for anime...\n")
        
        # Initial Search
        searchResults = self.provider.get_search(name)
        if not searchResults:
            QMessageBox.critical(self, "No Results", f'No anime with name "{name}" found!')
            return
        
        # Populate ComboBox with search results
        self.anime_list = []
        self.animeComboBox.clear()
        for r in searchResults:
            anime = Anime(self.provider, r.name, r.identifier, r.languages)
            self.anime_list.append(anime)
            self.animeComboBox.addItem(anime.name)
        
        self.output.append("Search complete. Select an anime from the dropdown menu.\n")

    def create_playlist(self):
        try:
            selected_index = self.animeComboBox.currentIndex()
            selectedAnime = self.anime_list[selected_index]
        except IndexError:
            QMessageBox.critical(self, "No Selection", "No anime selected!")
            return
        
        try:
            season = int(self.seasonEdit.text())
        except ValueError:
            QMessageBox.critical(self, "Invalid Input", "Season must be an integer.")
            return

        ver = self.verComboBox.currentText().lower()
        if ver not in ['dub', 'sub']:
            QMessageBox.critical(self, "Invalid Input", "Version must be 'Dub' or 'Sub'.")
            return

        ver = True if ver == 'dub' else False

        self.progress.setValue(0)
        self.output.clear()
        self.output.append("Selecting anime...\n")
        
        selectedLanguage = LanguageTypeEnum.DUB if ('DUB' in [x.name for x in selectedAnime.languages]) and ver else LanguageTypeEnum.SUB
        episodes = selectedAnime.get_episodes(lang=selectedLanguage)

        # Gathering URLs
        self.output.append("Gathering URLs...\n")
        eps = {}
        failed = []

        def update_progress(value):
            self.signals.update_progress.emit(value)

        def update_output(text):
            self.signals.update_output.emit(text)

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_episode = {executor.submit(fetch_episode, selectedAnime, e, selectedLanguage, self.signals): e for e in episodes}
            for future in concurrent.futures.as_completed(future_to_episode):
                episode = future_to_episode[future]
                try:
                    ep_num, result = future.result()
                    if result:
                        eps[ep_num] = result
                    else:
                        failed.append(ep_num)
                except Exception as exc:
                    update_output(f'Episode {episode} generated an exception: {exc}\n')
                    failed.append(episode)

                progress_value = len(eps) / len(episodes) * 100
                update_progress(progress_value)

        # Retry for failed episodes
        if failed:
            update_output(f'Failed: {failed}\n')
            update_output("Retrying Failed\n")
            ggsr = self.ggp.get_search(selectedAnime.name)
            gga = []
            g = None
            for r in ggsr:
                gga.append(Anime(self.ggp, r.name, r.identifier, r.languages))
            for i in range(len(gga)):
                if gga[i].name == selectedAnime.name and (selectedLanguage in gga[i].languages):
                    g = i
                    break

            newFail = []
            if failed and g is not None:
                ggsa = gga[g]
                ggsl = LanguageTypeEnum.DUB if ('DUB' in [x.name for x in ggsa.languages]) and ver else LanguageTypeEnum.SUB
                ggeps = ggsa.get_episodes(lang=ggsl)

            if failed and g is not None:
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    future_to_episode = {executor.submit(fetch_episode, ggsa, e, selectedLanguage, self.signals): e for e in failed}
                    for future in concurrent.futures.as_completed(future_to_episode):
                        episode = future_to_episode[future]
                        try:
                            ep_num, result = future.result()
                            if result:
                                eps[ep_num] = result
                            else:
                                newFail.append(ep_num)
                        except Exception as exc:
                            update_output(f'Episode {episode} generated an exception: {exc}\n')
                            newFail.append(episode)

                        progress_value = len(eps) / len(episodes) * 100
                        update_progress(progress_value)

            if newFail:
                update_output(f"New Fails: {newFail}\n")
                return

        # Setting array of URL
        urlArr = [eps[e].url for e in sorted(eps.keys())]
        dubORsub = 'DUB' if ver else 'SUB'
        if len(urlArr) < 3:
            return
        title = removeSymbols(selectedAnime.get_info().name)

        # Creating XSPF File
        file_path = f'{title} {titleGen(season, "S")} {dubORsub}.xspf'
        with open(file_path, 'w') as f:
            f.write(f'''<?xml version="1.0" encoding="UTF-8"?>\n<playlist xmlns="http://xspf.org/ns/0/" xmlns:vlc="http://www.videolan.org/vlc/playlist/ns/0/" version="1">\n    <title>{title} {titleGen(season, "S")}</title>\n    <trackList>''')
            for i, url in enumerate(urlArr):
                f.write(f'''\n        <track>\n            <location>{url}</location>\n            <title>{titleGen(season, "S")} {titleGen(i)}</title>\n            <extension application="http://www.videolan.org/vlc/playlist/0">\n                <vlc:id>{i}</vlc:id>\n                <vlc:option>network-caching=1000</vlc:option>\n            </extension>\n        </track>''')
            f.write('''\n    </trackList>\n</playlist>''')

        update_output(f'Playlist created: {file_path}\n')
        update_output('Open the file with VLC\n')
        update_output(f'File Path: {os.path.abspath(file_path)}\n')

    def update_progress_bar(self, value):
        self.progress.setValue(int(value))

    def update_output_text(self, text):
        self.output.append(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AnimeDownloaderGUI()
    sys.exit(app.exec_())
