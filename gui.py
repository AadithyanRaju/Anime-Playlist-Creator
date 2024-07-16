import sys
import os
import concurrent.futures
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout, QTextEdit, QProgressBar, QMessageBox, QComboBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QThreadPool, QRunnable
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

class WorkerSignals(QObject):
    update_progress = pyqtSignal(int)
    update_output = pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self, anime_downloader_gui, anime, season, ver, selected_language):
        super().__init__()
        self.anime_downloader_gui = anime_downloader_gui
        self.anime = anime
        self.season = season
        self.ver = ver
        self.selected_language = selected_language

    @pyqtSlot()
    def run(self):
        self.anime_downloader_gui.create_playlist_worker(self.anime, self.season, self.ver, self.selected_language)

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
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(5)  # Default max threads
        self.signals.update_progress.connect(self.update_progress_bar)
        self.signals.update_output.connect(self.update_output_text)

    def initUI(self):
        # Font style for banners
        banner_font = QFont()
        banner_font.setBold(True)
        banner_font.setPointSize(24)

        # Banner Label
        banner_label = QLabel('ANIME PLAYLIST CREATOR')
        banner_label.setAlignment(Qt.AlignCenter)
        banner_label.setFont(banner_font)

        # Layouts
        vbox = QVBoxLayout()

        # Banner layout
        vbox.addWidget(banner_label)

        # Anime Name
        self.nameEdit = QLineEdit()
        vbox.addLayout(self.create_label_edit_pair('Enter Anime Name:', self.nameEdit))

        # Season
        self.seasonEdit = QLineEdit('1')
        vbox.addLayout(self.create_label_edit_pair('Season:', self.seasonEdit))

        # Version (Dub/Sub)
        self.verComboBox = QComboBox()
        self.verComboBox.addItems(['Sub', 'Dub'])
        self.verComboBox.setCurrentText('Sub')  # Set default value to Sub
        vbox.addLayout(self.create_label_combobox_pair('Dub or Sub:', self.verComboBox))

        # Quality Selection (1080, 720, 480, 360)
        self.qualityComboBox = QComboBox()
        self.qualityComboBox.addItems(['1080', '720', '480', '360'])
        self.qualityComboBox.setCurrentText('1080')  # Set default value to 1080
        vbox.addLayout(self.create_label_combobox_pair('Quality:', self.qualityComboBox))

        # Max Workers Selection
        self.maxWorkersComboBox = QComboBox()
        self.maxWorkersComboBox.addItems([str(i) for i in range(1,9)])  # Options for max threads
        self.maxWorkersComboBox.setCurrentText('5')  # Default max workers
        vbox.addLayout(self.create_label_combobox_pair('Max Workers:', self.maxWorkersComboBox))

        # Search Button
        self.searchBtn = QPushButton('Search')
        self.searchBtn.clicked.connect(self.search_anime)
        vbox.addWidget(self.searchBtn)

        # Anime Selection ComboBox
        vbox.addWidget(QLabel('Select Anime:'))
        self.animeComboBox = QComboBox()
        vbox.addWidget(self.animeComboBox)

        # Create Playlist Button
        self.createBtn = QPushButton('Create Playlist')
        self.createBtn.clicked.connect(self.create_playlist)
        vbox.addWidget(self.createBtn)

        # Progress
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        vbox.addWidget(self.progress)

        # Output
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        vbox.addWidget(self.output)

        # Quit Button
        self.quitBtn = QPushButton('Quit')
        self.quitBtn.clicked.connect(QApplication.quit)
        vbox.addWidget(self.quitBtn)

        self.setLayout(vbox)
        self.setWindowTitle('Anime Playlist Creator')
        self.setGeometry(300, 300, 600, 400)
        self.show()


    def create_label_edit_pair(self, label_text, line_edit):
        hbox = QHBoxLayout()
        lbl = QLabel(label_text)
        hbox.addWidget(lbl)
        hbox.addWidget(line_edit)
        return hbox

    def create_label_combobox_pair(self, label_text, combobox):
        hbox = QHBoxLayout()
        lbl = QLabel(label_text)
        hbox.addWidget(lbl)
        hbox.addWidget(combobox)
        return hbox

    def search_anime(self):
        name = self.nameEdit.text()
        self.output.clear()
        self.output.append("Searching for anime...\n")

        # Initial Search
        searchResults = self.provider.get_search(name)
        if not searchResults:
            self.output.append(f'No anime with name "{name}" found!')
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

        max_workers = int(self.maxWorkersComboBox.currentText())
        self.thread_pool.setMaxThreadCount(max_workers)

        self.progress.setValue(0)
        self.output.clear()
        self.output.append("Selecting anime...\n")

        selectedLanguage = LanguageTypeEnum.DUB if ('DUB' in [x.name for x in selectedAnime.languages]) and ver else LanguageTypeEnum.SUB
        worker = Worker(self, selectedAnime, season, ver, selectedLanguage)
        self.thread_pool.start(worker)

    def create_playlist_worker(self, selectedAnime, season, ver, selectedLanguage):
        episodes = selectedAnime.get_episodes(lang=selectedLanguage)

        # Gathering URLs
        self.output.append("Gathering URLs...\n")
        eps = {}
        failed = []

        total_episodes = len(episodes)  # Total number of episodes

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_pool.maxThreadCount()) as executor:
            future_to_episode = {executor.submit(self.fetch_episode, selectedAnime, e, selectedLanguage): e for e in episodes}
            for future in concurrent.futures.as_completed(future_to_episode):
                episode = future_to_episode[future]
                try:
                    ep_num, result = future.result()
                    if result:
                        eps[ep_num] = result
                    else:
                        failed.append(ep_num)
                except Exception as exc:
                    self.output.append(f'Episode {episode} generated an exception: {exc}\n')
                    failed.append(episode)

                progress_value = (len(eps) + len(failed)) / total_episodes * 100  # Update progress
                self.signals.update_progress.emit(int(progress_value))

        # Retry for failed episodes with GoGoProvider
        if failed:
            self.output.append('Retrying failed episodes...\n')
            ggsr = self.ggp.get_search(selectedAnime.name)
            gga = []
            for r in ggsr:
                ggsa = Anime(self.ggp, r.name, r.identifier, r.languages)
                gga.append(ggsa)

            if not gga:
                QMessageBox.warning(self, "Anime Not Found", "Selected anime not found on GoGoProvider.")
                return

            ggsa = gga[0]
            selectedLanguage = LanguageTypeEnum.DUB if ('DUB' in [x.name for x in ggsa.languages]) and ver else LanguageTypeEnum.SUB

            with concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_pool.maxThreadCount()) as executor:
                future_to_episode = {executor.submit(self.fetch_episode, ggsa, e, selectedLanguage): e for e in failed}
                newFail = []
                for future in concurrent.futures.as_completed(future_to_episode):
                    episode = future_to_episode[future]
                    try:
                        ep_num, result = future.result()
                        if result:
                            eps[ep_num] = result
                        else:
                            newFail.append(ep_num)
                    except Exception as exc:
                        self.output.append(f'Episode {episode} generated an exception: {exc}\n')
                        newFail.append(episode)

                    progress_value = (len(eps) + len(newFail)) / total_episodes * 100  # Update progress
                    self.signals.update_progress.emit(int(progress_value))

            if newFail:
                self.output.append(f'New Fails: {newFail}\n')
                QMessageBox.warning(self, "Failed Episodes", f"Failed to retrieve episodes: {newFail}")
                return

        # Setting array of URLs
        urlArr = [v.url for v in eps.values()]
        dubORsub = 'DUB' if ver else 'SUB'
        if len(urlArr) < 3:
            QMessageBox.warning(self, "Too Few Episodes", "The selected anime has too few episodes to create a playlist.")
            return

        title = removeSymbols(selectedAnime.get_info().name)
        file_path = f'{title} {titleGen(season, "S")} {dubORsub}.xspf'

        # Creating XSPF File
        with open(file_path, 'w') as f:
            f.write(f'''<?xml version="1.0" encoding="UTF-8"?>
<playlist xmlns="http://xspf.org/ns/0/" xmlns:vlc="http://www.videolan.org/vlc/playlist/ns/0/" version="1">
    <title>{title} {titleGen(season, "S")}</title>
    <trackList>''')
            for i, url in enumerate(urlArr):
                f.write(f'''\n        <track>
            <location>{url}</location>
            <title>{titleGen(season, "S")} {titleGen(i)}</title>
            <extension application="http://www.videolan.org/vlc/playlist/0">
                <vlc:id>{i}</vlc:id>
                <vlc:option>network-caching=1000</vlc:option>
            </extension>
        </track>''')
            f.write('''\n    </trackList>
</playlist>''')

        self.signals.update_output.emit(f'Playlist created: {file_path}\n')
        self.signals.update_output.emit('Open the file with VLC\n')
        self.signals.update_output.emit(f'File Path: {os.path.abspath(file_path)}\n')

    def fetch_episode(self, anime, episode, language):
        try:
            result = anime.get_video(
                episode=episode, 
                lang=language,
                preferred_quality=int(self.qualityComboBox.currentText())
            )
            self.signals.update_output.emit(f'Episode {episode} done\n')
            return episode, result
        except Exception as e:
            self.signals.update_output.emit(f'Episode {episode} failed: {str(e)}\n')
            return episode, None

    @pyqtSlot(int)
    def update_progress_bar(self, value):
        self.progress.setValue(value)

    @pyqtSlot(str)
    def update_output_text(self, text):
        self.output.append(text.strip())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = AnimeDownloaderGUI()
    sys.exit(app.exec_())
