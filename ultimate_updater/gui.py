from pathlib import Path
import sys
import threading

from PySide6.QtCore import QLockFile, QStandardPaths, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QFont
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QProgressBar, QPushButton,
    QVBoxLayout, QWidget)

from . import __version__
from .firmware import fetch_source, compose, import_source
from .protocol import HidTransport
from .service import Installer, Cancelled, load_backup

STYLE = '''
QMainWindow, QWidget#page { background: #F4F6F8; color: #182B3A; }
QLabel { color: #182B3A; }
QLabel#brand { font-size: 15px; font-weight: 700; color: #547080; }
QLabel#title { font-size: 29px; font-weight: 700; }
QLabel#sub { color: #607384; font-size: 13px; }
QLabel#tag { color: #146E61; background: #E0F2EC; padding: 6px 12px; border-radius: 10px; }
QFrame#card { background: white; border: 1px solid #DCE4EA; border-radius: 16px; }
QLabel#section { font-weight: 700; font-size: 16px; }
QLabel#status { color: #547080; font-size: 14px; }
QPushButton { border: 1px solid #D4DFE5; border-radius: 9px; padding: 10px 14px; background: white; color: #263E4D; }
QPushButton:hover { background: #EBF1F4; }
QPushButton:disabled { color: #91A0AA; background: #E7EDF0; border-color: #E7EDF0; }
QPushButton#primary { background: #166B5E; color: white; border: none; font-size: 16px; font-weight: 700; padding: 15px; }
QPushButton#primary:hover { background: #105447; }
QPushButton#primary:disabled { background: #D3E0DC; color: #7A9690; }
QProgressBar { background: #E8EEF1; border: none; border-radius: 5px; height: 10px; }
QProgressBar::chunk { background: #218572; border-radius: 5px; }
QCheckBox { color: #364F5F; spacing: 9px; }
'''


class Worker(QThread):
    progress = Signal(str, int, bool)
    succeeded = Signal(str)
    failed = Signal(str, bool)

    def __init__(self, cache, backups, restore=None):
        super().__init__()
        self.cache, self.backups, self.restore = cache, backups, restore
        self.cancel = threading.Event()

    def run(self):
        installer = Installer(HidTransport(), self.backups, self.progress.emit, self.cancel.is_set)
        try:
            if self.restore:
                target, version = load_backup(self.restore)
            else:
                def status(message):
                    if self.cancel.is_set():
                        raise Cancelled('설치 전에 취소했습니다. 기기는 변경되지 않았습니다.')
                    self.progress.emit(message,0,False)
                stock = fetch_source('stock',self.cache,status)
                donor = fetch_source('radio',self.cache,status)
                target, version = compose(stock,donor),111
            directory = installer.install(target,version,recovery=bool(self.restore))
            self.succeeded.emit(str(directory))
        except Exception as error:
            self.failed.emit(str(error),installer.writing)


class Window(QMainWindow):
    def __init__(self, data_dir=None, demo=False):
        super().__init__()
        self.data_dir = Path(data_dir or QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
        self.cache, self.backups = self.data_dir/'cache', self.data_dir/'backups'
        self.worker = None
        self.demo = demo
        self.connected = False
        self.setWindowTitle('Ultimate Bluetooth Updater')
        self.resize(760,760)
        self.setMinimumSize(700,720)
        page = QWidget(); page.setObjectName('page'); self.setCentralWidget(page)
        layout = QVBoxLayout(page); layout.setContentsMargins(32,28,32,26); layout.setSpacing(17)
        header = QHBoxLayout()
        brand = QLabel('ULTIMATE / COMMUNITY'); brand.setObjectName('brand')
        tag = QLabel('BETA  ·  '+__version__); tag.setObjectName('tag')
        header.addWidget(brand); header.addStretch(); header.addWidget(tag); layout.addLayout(header)
        title = QLabel('익숙한 컨트롤러에, 새로운 기능.'); title.setObjectName('title'); layout.addWidget(title)
        sub = QLabel('Ultimate Bluetooth 전용 · 백버튼 리매핑 + Switch 2 깨우기'); sub.setObjectName('sub'); layout.addWidget(sub)

        card = QFrame(); card.setObjectName('card'); box = QVBoxLayout(card); box.setContentsMargins(22,20,22,20); box.setSpacing(12)
        heading = QLabel('01  컨트롤러 연결'); heading.setObjectName('section'); box.addWidget(heading)
        instructions = QLabel('전원을 끈 뒤 L + R을 누른 채 USB 케이블을 연결하세요.\n빨간 LED가 깜박이면 업데이트할 준비가 된 상태입니다.'); instructions.setWordWrap(True); box.addWidget(instructions)
        self.device_label = QLabel('●  부트모드 컨트롤러를 기다리는 중'); self.device_label.setObjectName('status'); box.addWidget(self.device_label)
        self.confirm = QCheckBox('내 컨트롤러는 Ultimate Bluetooth 모델입니다.'); self.confirm.stateChanged.connect(self.refresh_buttons); box.addWidget(self.confirm)
        layout.addWidget(card)

        card2 = QFrame(); card2.setObjectName('card'); box2 = QVBoxLayout(card2); box2.setContentsMargins(22,20,22,20); box2.setSpacing(12)
        heading2 = QLabel('02  백업하고 업데이트'); heading2.setObjectName('section'); box2.addWidget(heading2)
        body = QLabel('기존 펌웨어와 페어링 정보를 자동으로 백업합니다.\n설치 후 전체 내용을 검증한 다음 컨트롤러를 다시 시작합니다.'); body.setWordWrap(True); box2.addWidget(body)
        self.progress_label = QLabel('준비되면 아래 버튼을 눌러 주세요.'); self.progress_label.setWordWrap(True); self.progress_label.setObjectName('status'); box2.addWidget(self.progress_label)
        self.bar = QProgressBar(); self.bar.setRange(0,100); self.bar.setTextVisible(False); box2.addWidget(self.bar)
        self.update_button = QPushButton('펌웨어 업데이트'); self.update_button.setObjectName('primary'); self.update_button.clicked.connect(self.update_firmware); box2.addWidget(self.update_button)
        row = QHBoxLayout(); self.restore_button = QPushButton('이전 펌웨어로 복구'); self.restore_button.clicked.connect(self.restore_firmware)
        self.cancel_button = QPushButton('취소'); self.cancel_button.clicked.connect(self.cancel_job); self.cancel_button.setEnabled(False)
        row.addWidget(self.restore_button); row.addWidget(self.cancel_button); box2.addLayout(row); layout.addWidget(card2)

        footer = QHBoxLayout()
        for text, slot in [('백업 폴더',self.open_backups),('공식 파일 가져오기',self.import_files),('사용 방법',self.help)]:
            button = QPushButton(text); button.clicked.connect(slot); footer.addWidget(button)
        layout.addLayout(footer)
        note = QLabel('비공식 커뮤니티 펌웨어입니다. 8BitDo와 제휴하지 않습니다.\nGUI 앱의 USB 설치는 실기기 미검증 베타입니다. 쓰는 동안 USB를 분리하지 마세요.'); note.setObjectName('sub'); note.setWordWrap(True); layout.addWidget(note)
        layout.addStretch()
        self.timer = QTimer(self); self.timer.timeout.connect(self.detect); self.timer.start(2000)
        self.detect()

    def detect(self):
        if self.worker:
            return
        try:
            devices = [] if self.demo else HidTransport.enumerate()
            self.connected = len(devices)==1
            self.device_label.setText('●  부트모드 컨트롤러 연결됨' if self.connected else ('●  한 대만 연결해 주세요' if devices else '●  부트모드 컨트롤러를 기다리는 중'))
        except Exception:
            self.connected = False
            self.device_label.setText('●  USB 장치 확인 실패 · 다른 업데이트 앱을 닫아 주세요')
        self.refresh_buttons()

    def refresh_buttons(self):
        ready = self.connected and self.confirm.isChecked() and not self.worker and not self.demo
        self.update_button.setEnabled(ready); self.restore_button.setEnabled(ready)
        self.confirm.setEnabled(not self.worker)

    def begin(self, restore=None):
        if self.worker or self.demo or not self.connected or not self.confirm.isChecked():
            return
        self.worker = Worker(self.cache,self.backups,restore)
        self.worker.progress.connect(self.on_progress)
        self.worker.succeeded.connect(self.on_success)
        self.worker.failed.connect(self.on_failure)
        self.worker.finished.connect(self.finished)
        self.refresh_buttons(); self.cancel_button.setEnabled(True); self.worker.start()

    def update_firmware(self):
        self.begin()

    def restore_firmware(self):
        path,_ = QFileDialog.getOpenFileName(self,'이전 백업 선택',str(self.backups),'Backup (backup.json)')
        if not path:
            return
        try:
            _,version = load_backup(path)
        except Exception as error:
            QMessageBox.warning(self,'백업 확인',str(error)); return
        answer = QMessageBox.question(self,'이전 펌웨어 복구',f'선택한 백업의 펌웨어 {version/100:.2f}로 되돌립니다.\n현재 내용도 먼저 백업하며, 페어링 영역은 덮어쓰지 않습니다.\n계속할까요?')
        if answer == QMessageBox.Yes:
            self.begin(path)

    def on_progress(self, label, percent, writing):
        self.progress_label.setText(label); self.bar.setValue(percent)
        self.cancel_button.setEnabled(not writing)

    def on_success(self, directory):
        self.progress_label.setText('완료했습니다. USB를 분리하고 컨트롤러를 사용하세요.')
        self.bar.setValue(100)
        QMessageBox.information(self,'업데이트 완료','펌웨어 전체 검증과 페어링 정보 보존 확인을 마쳤습니다.\n\nSwitch 2 깨우기는 오른쪽 조이콘 2로 한 번 학습해야 합니다.\n아래 ‘사용 방법’을 확인하세요.\n\n백업: '+directory)

    def on_failure(self, message, writing):
        self.progress_label.setText('중단됨 · USB 연결을 유지하고 백업으로 복구하세요.' if writing else '설치하지 않았습니다. 아래 내용을 확인하세요.')
        QMessageBox.warning(self,'업데이트 중단',message+('\n\n자동 재시도나 리셋은 하지 않았습니다. 부트모드 연결을 유지하세요.' if writing else ''))

    def finished(self):
        job = self.worker; self.worker = None
        if job: job.deleteLater()
        self.cancel_button.setEnabled(False); self.detect()

    def cancel_job(self):
        if self.worker:
            self.worker.cancel.set(); self.cancel_button.setEnabled(False)
            self.progress_label.setText('취소 중 · 현재 읽기가 끝나면 중단합니다.')

    def open_backups(self):
        self.backups.mkdir(parents=True,exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.backups)))

    def import_files(self):
        if self.worker:
            return
        paths,_ = QFileDialog.getOpenFileNames(self,'공식 펌웨어 파일 선택','','Firmware (*.dat)')
        if not paths:
            return
        try:
            kinds = [import_source(p,self.cache) for p in paths]
            QMessageBox.information(self,'파일 검증 완료','가져온 공식 파일: '+', '.join(kinds))
        except Exception as error:
            QMessageBox.warning(self,'파일 확인',str(error))

    def help(self):
        QMessageBox.information(self,'설치 후 사용 방법',
            'Switch 2 깨우기\n'
            '1. Ultimate를 Switch 2에 먼저 페어링합니다.\n'
            '2. 본체를 절전시키고 Ultimate를 켜 연결 대기시킵니다.\n'
            '3. 오른쪽 조이콘 2의 HOME으로 본체를 깨웁니다.\n'
            '4. Ultimate에서 학습 진동이 오면 다시 본체를 절전시킵니다.\n'
            '5. Ultimate를 켜고 연결 대기 중 흔들면 본체를 깨웁니다.\n\n'
            '학습 중에는 자신의 오른쪽 조이콘만 조작해 주세요.\n'
            '백버튼 할당: 백버튼과 대상 버튼을 누르고 프로필 변경 버튼으로 확정합니다.\n\n'
            'Ultimate 2, 2C, C, 2.4G 전용 모델은 설치 대상이 아닙니다.\n'
            '인식하지 못하는 기존 펌웨어는 백업 후 설치를 중단합니다.')

    def closeEvent(self,event: QCloseEvent):
        if self.worker:
            event.ignore()
            self.progress_label.setText('진행 중에는 앱을 닫을 수 없습니다. 설치 전에는 취소 버튼을 사용하세요.')
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName('UltimateBluetoothUpdater')
    app.setOrganizationName('UltimateCommunity')
    app.setFont(QFont('Segoe UI' if sys.platform=='win32' else 'Apple SD Gothic Neo',11))
    app.setStyleSheet(STYLE)
    folder = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)); folder.mkdir(parents=True,exist_ok=True)
    lock = QLockFile(str(folder/'updater.lock'))
    if not lock.tryLock(100):
        QMessageBox.warning(None,'이미 실행 중','업데이트 앱이 이미 실행 중입니다.'); return 1
    window = Window(); window.show()
    return app.exec()
