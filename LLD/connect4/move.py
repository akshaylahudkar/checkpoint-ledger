class Move:
    def __init__(self, game, player, column):
        self.game = game
        self.player = player
        self.column = column
        self.game.board.setMove(player.id, column)



    
