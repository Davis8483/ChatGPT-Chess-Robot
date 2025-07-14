import time
import threading
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QByteArray
import darkdetect
import win32mica
import chess.svg
import chess

class Visual():
    def __init__(self):
        super().__init__()

        # set open flag to false
        self.is_open = False

        self.prev_move = None

        t = threading.Thread(target=self.start)
        t.start()

    def start(self):
        self.app = QApplication([])

        self.window = QMainWindow()

        self.window.setWindowTitle("Chess Bot Board")

        self.window.setStyleSheet("background-color: rgba(0, 0, 0, 0)")
        self.window.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.window.setCentralWidget(self.label)

        self.update("8/8/8/8/8/8/8/8")

        self.window.resizeEvent = self.resizeEvent
        self.window.closeEvent = self.closeEvent

        self.window.setGeometry(100, 100, 400, 400)

        while True:
            if self.is_open and not self.window.isActiveWindow():
                self.window.show()

                # apply mica style
                win32mica.ApplyMica(self.window.winId(), bool(darkdetect.isDark()))

            self.app.processEvents()
            time.sleep(0.2)


    def show(self):

        # set open flag to true
        self.is_open = True

    def resizeEvent(self, event):
        if not self.image.isNull():
            self.scaled_image = self.image.scaled(self.window.size(), Qt.AspectRatioMode.KeepAspectRatio)
            self.label.setPixmap(self.scaled_image)
            self.window.setMinimumSize(200, 200)

    def closeEvent(self, event):
        # set open flag to false
        self.is_open = False

    def update(self, fen, check=None, lastmove=None, valid_moves=None):

        board = chess.Board(fen)

        squares = {}
        if valid_moves != None:
            squares = {}
            
            # find valid moves
            for move in board.legal_moves:
                if chess.square_name(move.from_square) == valid_moves:
                    squares[move.to_square] = "#cc0000aa"

        # prev move is retained between updates
        if lastmove != None:
            self.prev_move = chess.Move.from_uci(lastmove)

        check_pos = None
        if check != None:
            check_pos = chess.parse_square(check)

        board_svg = chess.svg.board(
            board=board,
            fill=squares,
            lastmove=self.prev_move,
            check=check_pos,
            size=1080
        )

        self.image = QPixmap()
        self.image.loadFromData(QByteArray(board_svg.encode('utf-8')))

        self.resizeEvent(None)

if __name__ == "__main__":

    board = chess.Board("8/8/8/8/8/8/8/8")
    
    window = Visual()
    window.show()
    
    board = chess.Board()

    time.sleep(3)

    letters = ["a", "b", "c", "d", "e", "f", "g", "h"]

    while True:
        for index in letters:
            window.update(board.fen(), valid_moves=f"{index}2", lastmove="d7d5", check="e8")
            time.sleep(1)



