import subprocess

try:
    import stockfish
except ImportError:
    subprocess.run(["pip", "install", "stockfish"])
    import stockfish

class Engine():
  # initialize engine
  def __init__(self):
    self.__board = stockfish.Stockfish()
    self.last_captured = None

  # takes fen notation and outputs list of raw board positions
  def __get_raw_board(self, fen):
    
    # get the piece placement part of the FEN string
    piece_placement = fen.split(" ")[0]
    
    board = []
    
    # loop through the rows of the board
    for row in piece_placement.split("/"):
      # loop through the squares of the row
      for square in row:
        if square.isdigit():
          for blank in range(int(square)):
            board.append(None)
        else:
          board.append(square)
    
    return board
          
  # returns the captured piece between two board states
  def __find_captured_piece(self, fen_old, fen_new):

    board_old = self.__get_raw_board(fen_old)
    board_new = self.__get_raw_board(fen_new)

    # just to verivy nothings incredibly broken
    if len(board_old) != len(board_new):
      return None

    # loop through each square on the board and return captured piece
    for index in range(len(board_old) - 1):
      if (board_old[index] != board_new[index]) and not (board_new[index] is None):
        return board_old[index]
      
    return None

  # get bot move and save claimed pieces if any
  def get_move(self):

    old_fen = self.__board.get_fen_position()

    # Make the best move on the board
    self.__board.make_moves_from_current_position([self.__board.get_best_move()])

    new_fen = self.__board.get_fen_position()
    
    # save captured pieces if any
    self.last_captured = self.__find_captured_piece(old_fen, new_fen)
    
    # return the updated FEN position of the board
    return new_fen

  # input player move and save claimed pieces
  def input_move(self, fen):
    
    if self.__board.is_fen_valid(fen):
      self.last_captured = self.__find_captured_piece(self.__board.get_fen_position(), fen)
      self.__board.set_fen_position(fen)

  # print board
  def show_board(self):
    print(self.__board.get_board_visual())
     