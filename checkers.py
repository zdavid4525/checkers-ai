from __future__ import annotations

import argparse
from copy import deepcopy
import sys
import time
from typing import Optional

WIDTH = 8
HEIGHT = 8

RED_PIECE = "r"
RED_KING = "R"
BLACK_PIECE = "b"
BLACK_KING = "B"
EMPTY_SQUARE = "."

MIN_UTILITY = -1000000000
MAX_UTILITY = 1000000000

cached = {}  # for state caching

DEPTH_LIMIT = 9


class State:
    # This class is used to represent a state.
    # board : a list of lists that represents the 8*8 board
    board: list[list[str]]  # index into position (x,y) by board[y][x]
    width: int
    height: int
    next_turn: str

    def __init__(self, board, next_turn):
        self.board = board
        self.next_turn = next_turn
        self.width = WIDTH
        self.height = HEIGHT

    def get_utility(self):
        """
        Utility is useful for the player who moves into this state. That is, if the next player in the state is
        Red/Black, then the player who advanced the game into this state is Black/Red, so the returned utility for this
        state should be for Black/Red.
        """
        # UTILITIES FOR TERMINAL (GAME END) STATES
        if self.red_win() and self.next_turn == RED_PIECE:  # red win from black's move
            return MIN_UTILITY  # return min utility so black doesn't pick this state
        elif self.red_win() and self.next_turn == BLACK_PIECE:  # red win from red's move
            return MAX_UTILITY  # return max utility so red picks this state and wins
        elif self.black_win() and self.next_turn == RED_PIECE:  # black win from black's move
            return MAX_UTILITY  # return max utility so black picks this state and wins
        elif self.black_win() and self.next_turn == BLACK_PIECE:  # black win from red's move
            return MIN_UTILITY  # return min utility so red doesn't pick this state

        # ESTIMATED UTILITY FOR NON-TERMINAL STATES
        (num_pieces_player, num_kings_player, num_center_player, num_advanced_player, num_edge_player,
         num_can_attack_player) = self._get_evaluation_params(BLACK_PIECE if self.next_turn == RED_PIECE else RED_PIECE)

        (num_pieces_other, num_kings_other, num_center_other, num_advanced_other, num_edge_other,
         num_can_attack_other) = (self._get_evaluation_params(self.next_turn))

        # CUSTOM EVAL FUNC
        return ((num_pieces_player + 2 * num_kings_player + 0.5 * num_center_player + 0.15 * num_edge_player) -
                (num_pieces_other + 2 * num_kings_other + 0.5 * num_center_other + 0.15 * num_edge_other))

    def _get_evaluation_params(self, player):
        player_piece = player
        player_king = RED_KING if player == RED_PIECE else BLACK_KING
        num_pieces, num_kings, num_center, num_advanced, num_edge, num_can_attack = (
            0, 0, 0, 0, 0, 0)

        for i in range(HEIGHT):
            for j in range(WIDTH):
                if self.board[i][j] == player_king:
                    num_kings += 1
                if self.board[i][j] == player_piece:
                    num_pieces += 1
                if (self.board[i][j] == player_piece or self.board[i][j] == player_king) and ((2 <= i <= 5 and 3 <= j <= 4) or (2 <= j <= 5 and 3 <= i <= 4)):
                    num_center += 1
                if (self.board[i][j] == player_piece or self.board[i][j] == player_king) and ((player_piece == RED_PIECE and i <= 3) or (player_piece == BLACK_PIECE and i >= 4)):
                    num_advanced += 1
                if ((self.board[i][j] == player_piece or self.board[i][j] == player_king) and
                        len(self._generate_jump_moves_for_curr(i, j, player_piece)) > 0):
                    num_can_attack += 1
                if (self.board[i][j] == player_piece or self.board[i][j] == player_king) and (j == 0 or j == WIDTH - 1):
                    num_edge += 1

        return num_pieces, num_kings, num_center, num_advanced, num_edge, num_can_attack

    def red_win(self):
        # red wins <==> there are no black pieces remaining
        for i in range(HEIGHT):
            for j in range(WIDTH):
                if self.board[i][j] == BLACK_PIECE or self.board[i][j] == BLACK_KING:
                    return False
        return True

    def black_win(self):
        # black wins <==> there are no red pieces remaining
        for i in range(HEIGHT):
            for j in range(WIDTH):
                if self.board[i][j] == RED_PIECE or self.board[i][j] == RED_KING:
                    return False
        return True

    def generate_successors(self) -> list[State]:
        # will only return jump moves, or will only return simple moves
        jump_moves = self._generate_jump_moves()  # if jumps are possible, consider jumping only
        return self._generate_simple_moves(self.next_turn) if len(jump_moves) == 0 else jump_moves

    def _generate_jump_moves(self) -> list[State]:
        next_player_piece = RED_PIECE if self.next_turn == RED_PIECE else BLACK_PIECE
        next_player_king = RED_KING if self.next_turn == RED_PIECE else BLACK_KING

        successors = []
        for i in range(HEIGHT):
            for j in range(WIDTH):
                if self.board[i][j] == next_player_king or self.board[i][j] == next_player_piece:
                    successors.extend(self._generate_jump_moves_for_curr(i, j, self.next_turn))
        return successors

    def _generate_jump_moves_for_curr(self, i, j, turn):
        next_player_piece = RED_PIECE if turn == RED_PIECE else BLACK_PIECE
        next_player_king = RED_KING if turn == RED_PIECE else BLACK_KING

        new_board = deepcopy(self.board)
        if self.board[i][j] == next_player_piece:
            return self._generate_jump_moves_for_piece(i, j, new_board)
        elif self.board[i][j] == next_player_king:  # check all 4 diagonals
            return self._generate_jump_moves_for_king(i, j, new_board)

    def _generate_jump_moves_for_piece(self, i, j, curr_board):
        next_player_piece = RED_PIECE if self.next_turn == RED_PIECE else BLACK_PIECE
        piece_moves = {(-1, -1), (-1, 1)} if self.next_turn == RED_PIECE else {(1, -1), (1, 1)}
        next_player_king = RED_KING if self.next_turn == RED_PIECE else BLACK_KING
        next_next_player_piece = BLACK_PIECE if self.next_turn == RED_PIECE else RED_PIECE
        next_next_player_king = BLACK_KING if self.next_turn == RED_PIECE else RED_KING

        successors = []

        # BASE CASE: Nothing to jump over
        all_empty = True
        for x, y in piece_moves:
            if self._can_jump(i + x, j + y, i + x + x, j + y + y, next_next_player_piece, next_next_player_king,
                              curr_board):
                all_empty = False

        if all_empty and self.board == curr_board:
            return []
        elif all_empty:
            return [State(curr_board, next_next_player_piece)]

        # RECURSIVE STEP
        for x, y in piece_moves:
            if self._can_jump(i + x, j + y, i + x + x, j + y + y, next_next_player_piece, next_next_player_king,
                              curr_board):
                new_board = deepcopy(curr_board)
                new_board[i][j], new_board[i + x][j + y] = EMPTY_SQUARE, EMPTY_SQUARE
                if (i + x + x == 0 and self.next_turn == RED_PIECE) or (i + x + x == HEIGHT - 1 and
                                                                        self.next_turn == BLACK_PIECE):
                    # piece has made it to top/bot ==> become king and end turn
                    new_board[i + x + x][j + y + y] = next_player_king
                    successors.append(State(new_board, next_next_player_piece))
                else:
                    new_board[i + x + x][j + y + y] = next_player_piece
                    successors.extend(self._generate_jump_moves_for_piece(i + x + x, j + y + y, new_board))
        return successors

    def _generate_jump_moves_for_king(self, i, j, curr_board):
        next_player_king = RED_KING if self.next_turn == RED_PIECE else BLACK_KING
        next_next_player_piece = BLACK_PIECE if self.next_turn == RED_PIECE else RED_PIECE
        next_next_player_king = BLACK_KING if self.next_turn == RED_PIECE else RED_KING

        successors = []

        # BASE CASE: Nothing to jump over
        all_empty = True
        for x, y in {(-1, -1), (-1, 1), (1, -1), (1, 1)}:
            if self._can_jump(i + x, j + y, i + x + x, j + y + y, next_next_player_piece, next_next_player_king,
                              curr_board):
                all_empty = False

        if all_empty and self.board == curr_board:
            return []
        elif all_empty:
            return [State(curr_board, next_next_player_piece)]

        # RECURSIVE STEP
        for x, y in {(-1, -1), (-1, 1), (1, -1), (1, 1)}:
            if self._can_jump(i + x, j + y, i + x + x, j + y + y, next_next_player_piece, next_next_player_king,
                              curr_board):
                new_board = deepcopy(curr_board)
                new_board[i][j], new_board[i + x][j + y] = EMPTY_SQUARE, EMPTY_SQUARE
                new_board[i + x + x][j + y + y] = next_player_king

                successors.extend(self._generate_jump_moves_for_king(i + x + x, j + y + y, new_board))
        return successors

    def _can_jump(self, jump_over_y, jump_over_x, jump_to_y, jump_to_x, next_next_player_piece, next_next_player_king,
                  curr_board) -> bool:
        """
        Checks whether we're (1) jumping over and (2) jumping into a square within the grid's bounds, (3) whether the
        square we're jumping over is occupied by an opponent piece, (4) whether the square we're jumping into is empty
        """
        return (0 <= jump_over_y < HEIGHT and 0 <= jump_over_x < WIDTH and 0 <= jump_to_y < HEIGHT
                and 0 <= jump_to_x < WIDTH and curr_board[jump_to_y][jump_to_x] == EMPTY_SQUARE and
                (curr_board[jump_over_y][jump_over_x] == next_next_player_piece or
                 curr_board[jump_over_y][jump_over_x] == next_next_player_king))

    def _generate_simple_moves(self, next_player) -> list[State]:
        # Pre: the only available moves are simple moves
        next_player_piece = RED_PIECE if next_player == RED_PIECE else BLACK_PIECE
        piece_moves = {(-1, -1), (-1, 1)} if next_player == RED_PIECE else {(1, -1), (1, 1)}
        next_player_king = RED_KING if next_player == RED_PIECE else BLACK_KING
        next_next_player = BLACK_PIECE if next_player == RED_PIECE else RED_PIECE

        successors = []

        for i in range(HEIGHT):
            for j in range(WIDTH):
                if self.board[i][j] == next_player_piece:  # check up left and up right
                    for x, y in piece_moves:
                        if 0 <= i + x < HEIGHT and 0 <= j + y < WIDTH and self.board[i + x][j + y] == EMPTY_SQUARE:
                            new_board = deepcopy(self.board)
                            new_board[i][j] = EMPTY_SQUARE
                            if (i + x == 0 and next_player == RED_PIECE) or (i + x == HEIGHT - 1 and
                                                                             next_player == BLACK_PIECE):
                                # piece has made it to top/bot ==> become king
                                new_board[i + x][j + y] = next_player_king
                            else:
                                new_board[i + x][j + y] = next_player_piece
                            successors.append(State(new_board, next_next_player))
                elif self.board[i][j] == next_player_king:  # check all 4 diagonals
                    for x, y in {(-1, -1), (-1, 1), (1, -1), (1, 1)}:
                        if 0 <= i + x < HEIGHT and 0 <= j + y < WIDTH and self.board[i + x][j + y] == EMPTY_SQUARE:
                            new_board = deepcopy(self.board)
                            new_board[i][j] = EMPTY_SQUARE
                            new_board[i + x][j + y] = next_player_king
                            successors.append(State(new_board, next_next_player))
        return successors

    def display_test(self):
        print("Next turn:", self.next_turn)
        for i in self.board:
            for j in i:
                print(j, end="")
            print("")
        print("")

    def display(self):
        for i in self.board:
            for j in i:
                print(j, end="")
            print("")
        print("")


def get_opp_char(player):
    if player in [BLACK_PIECE, BLACK_KING]:
        return [RED_PIECE, RED_KING]
    else:
        return [BLACK_PIECE, BLACK_KING]


def get_next_turn(curr_turn):
    if curr_turn == RED_PIECE:
        return BLACK_PIECE
    else:
        return RED_PIECE


def read_from_file(filename):

    f = open(filename)
    lines = f.readlines()
    board = [[str(x) for x in l.rstrip()] for l in lines]
    f.close()

    return board


class CachedState:
    def __init__(self, v, depth, successor):
        self.v = v
        self.depth = depth
        self.successor = successor


def alphabeta_max_node(state, turn, alpha, beta, current_depth) -> tuple[int, Optional[State]]:
    state_str = str(state.board) + turn
    if state_str in cached and cached[state_str].depth >= current_depth:
        return cached[state_str].v, cached[state_str].successor
    if current_depth == 0 or state.red_win() or state.black_win():
        return state.get_utility(), None

    successors = state.generate_successors()
    if not successors:
        cached[state_str] = CachedState(MIN_UTILITY, current_depth, None)
        return MIN_UTILITY, None

    successors.sort(key=lambda s: s.get_utility(), reverse=True)
    v = MIN_UTILITY
    best = successors[0]
    for successor in successors:
        tempval, _ = alphabeta_min_node(successor, get_next_turn(turn), alpha, beta, current_depth - 1)
        if tempval > v:
            v = tempval
            best = successor
        if tempval > beta:
            cached[state_str] = CachedState(v, current_depth, successor)
            return v, successor
        alpha = max(alpha, tempval)
        cached[state_str] = CachedState(v, current_depth, best)
    return v, best


def alphabeta_min_node(state, turn, alpha, beta, current_depth) -> tuple[int, Optional[State]]:
    state_str = str(state.board) + turn
    if state_str in cached and cached[state_str].depth >= current_depth:
        return cached[state_str].v, cached[state_str].successor
    if current_depth == 0 or state.red_win() or state.black_win():
        return state.get_utility(), None

    successors = state.generate_successors()
    if not successors:
        cached[state_str] = CachedState(MAX_UTILITY, current_depth, None)
        return MAX_UTILITY, None

    successors.sort(key=lambda s: s.get_utility())
    v = MAX_UTILITY
    best = successors[0]
    for successor in successors:
        tempval, _ = alphabeta_max_node(successor, get_next_turn(turn), alpha, beta, current_depth - 1)
        if tempval < v:
            v = tempval
            best = successor
        if tempval < alpha:
            cached[state_str] = CachedState(v, current_depth, successor)
            return v, successor
        beta = min(beta, tempval)
        cached[state_str] = CachedState(v, current_depth, best)
    return v, best


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inputfile",
        type=str,
        required=True,
        help="The input file that contains the puzzles."
    )
    parser.add_argument(
        "--outputfile",
        type=str,
        required=True,
        help="The output file that contains the solution."
    )
    args = parser.parse_args()

    initial_board = read_from_file(args.inputfile)
    state = State(initial_board, RED_PIECE)  # should always be RED_PIECE unless testing

    sys.stdout = open(args.outputfile, 'w')

    state.display()
    # PLAY GAME
    while not (state.red_win() or state.black_win()):
        if state.next_turn == RED_PIECE:
            _, state = alphabeta_max_node(state, RED_PIECE, MIN_UTILITY, MAX_UTILITY, DEPTH_LIMIT)
        else:  # next to move is black
            _, state = alphabeta_max_node(state, BLACK_PIECE, MIN_UTILITY, MAX_UTILITY, DEPTH_LIMIT)
        state.display()

    sys.stdout = sys.__stdout__
