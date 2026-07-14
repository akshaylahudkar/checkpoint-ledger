from board import Board
from game import Game
from move import Move
from user import User
from gameplayer import GamePlayer

akshay = User(1, "Akshay")
neal = User(2,"Neal")

akshay_player = GamePlayer(akshay,"red")
neal_player = GamePlayer(neal, "blue")
board = Board()
game1 = Game(akshay_player, neal_player, board)

akshay_move1 = Move(game1, akshay_player, 2)

neal_move1 = Move(game1, neal_player, 1)

akshay_move2 = Move(game1, akshay_player, 3)

neal_move2 = Move(game1, neal_player, 0)

akshay_move3 = Move(game1, akshay_player, 4)

neal_move3 = Move(game1, neal_player, 6)

akshay_move4 = Move(game1, akshay_player, 5)

print(game1.board.result)





