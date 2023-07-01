import subprocess
import sys

try:
    from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
    from PySide6.QtGui import QPixmap, QImage
    from PySide6.QtCore import Qt, QByteArray
    import darkdetect
    import win32mica
    import chess.svg
    import chess

except:
    subprocess.run(["pip", "install", "PySide6", "win32mica", "darkdetect", "chess"])

    from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
    from PySide6.QtGui import QPixmap, QImage
    from PySide6.QtCore import Qt, QByteArray
    import darkdetect
    import win32mica
    import chess.svg
    import chess



class Visual(QMainWindow):
    def __init__(self, fen):
        super().__init__()
        self.setWindowTitle("Chess Bot Board")

        win32mica.ApplyMica(self.winId(), darkdetect.isDark())

        self.setStyleSheet("background-color: rgba(0, 0, 0, 0)")
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        self.setCentralWidget(self.label)


        self.update(fen)

        self.setGeometry(100, 100, 400, 400)

        self.show()

    def resizeEvent(self, event):
        self.scaled_image = self.image.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        self.label.setPixmap(self.scaled_image)
        self.setMinimumSize(200, 200)

    def update(self, fen):
        board_svg = chess.svg.board(
            chess.Board(fen),
            size=1080
        )

        self.image = QPixmap()
        self.image.loadFromData(QByteArray(board_svg))

if __name__ == "__main__":
    app = QApplication(sys.argv)

    board = chess.Board()

    window = Visual(board.fen())

    sys.exit(app.exec())



