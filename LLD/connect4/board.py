

class Board:
    def __init__(self):
        self.ROWS = 6
        self.COLS = 7
        self.board = [[0 for _ in range(self.COLS)] for _ in range(self.ROWS)]
        self.result = None

    def getCurrentState(self):
        return self.board
    
    def setMove(self, player_id, column):
        try:
            if self.result:
                return self.getCurrentState(),self.result, ValueError("Game Finished already and ",self.result,'has won!!')
            
            row, _ = self.findAvailableRow(column)
            if row != -1:
                self.board[row][column] = player_id
                self.result = self.checkResult()
            return self.getCurrentState(), self.result, None

        except Exception as e:
        
            return None, None, e
        
    def checkResult(self):
        # 1. Check Horizontal Wins
        for r in range(self.ROWS):
            for c in range(self.COLS - 3):
                if (
                    self.board[r][c] != 0  # <--- Changed here
                    and self.board[r][c]
                    == self.board[r][c + 1]
                    == self.board[r][c + 2]
                    == self.board[r][c + 3]
                ):
                    return self.board[r][c]

        # 2. Check Vertical Wins
        for r in range(self.ROWS - 3):
            for c in range(self.COLS):
                if (
                    self.board[r][c] != 0  # <--- Changed here
                    and self.board[r][c]
                    == self.board[r + 1][c]
                    == self.board[r + 2][c]
                    == self.board[r + 3][c]
                ):
                    return self.board[r][c]

        # 3. Check Down-Right Diagonal Wins (\ direction)
        for r in range(self.ROWS - 3):
            for c in range(self.COLS - 3):
                if (
                    self.board[r][c] != 0  # <--- Changed here
                    and self.board[r][c]
                    == self.board[r + 1][c + 1]
                    == self.board[r + 2][c + 2]
                    == self.board[r + 3][c + 3]
                ):
                    return self.board[r][c]

        # 4. Check Up-Right Diagonal Wins (/ direction)
        for r in range(3, self.ROWS):
            for c in range(self.COLS - 3):
                if (
                    self.board[r][c] != 0  # <--- Changed here
                    and self.board[r][c]
                    == self.board[r - 1][c + 1]
                    == self.board[r - 2][c + 2]
                    == self.board[r - 3][c + 3]
                ):
                    return self.board[r][c]

        return None



    def findAvailableRow(self, column):
        if column >= len(self.board[0]) or column < 0:
            return -1, IndexError("Illegal Move")
        
        for i in range(len(self.board)-1, -1, -1):
            if self.board[i][column] == 0:
                return i, None
        return -1,ValueError("No legal move available in column.")
    

board1 = Board()

curr, result, err = board1.setMove(28, 2)
print('board',curr, '\n', 'result', result, '\n', err)
curr, result, err = board1.setMove(52, 1)
print('board',curr, '\n', 'result', result, '\n', err)

curr, result, err = board1.setMove(28, 3)
print('board',curr, '\n','result', result, '\n', err)
curr, result, err = board1.setMove(52, 0)
print('board',curr, '\n', 'result', result, '\n', err)

curr, result, err = board1.setMove(28, 4)
print('board',curr, '\n', 'result', result, '\n', err)
curr, result, err = board1.setMove(52,6)
print('board',curr, '\n','result',  result, '\n', err)

curr, result, err = board1.setMove(28, 5)
print('board',curr, '\n', 'result', result, '\n', err)


curr, result, err = board1.setMove(28, 5)
print('board',curr, '\n', 'result', result, '\n', err)