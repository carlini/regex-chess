## Copyright (C) 2025, Nicholas Carlini <nicholas@carlini.com>.
##
## This program is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program.  If not, see <http://www.gnu.org/licenses/>.

from instruction_set import *

def color_black(piece, inv=False):
    if isinstance(piece, str):
        return piece.upper() if inv else piece.lower()
    elif isinstance(piece, list):
        return [color_black(p, inv) for p in piece]
    
def color_white(piece, inv=False):
    if isinstance(piece, str):
        return piece.lower() if inv else piece.upper()
    elif isinstance(piece, list):
        return [color_white(p, inv) for p in piece]

def join_sub_to_main(variables, maxn, main="main", sub="sub"):
    variables.pause(sub)
    variables.reactivate(main)
    for _ in range(maxn):
        variables.join_pop(sub)


def king_moves(variables, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    variables['king'] = color('k')
    for ii,i in enumerate('abcdefgh'):
        for j in range(1,9):
            if (variables[str(i)+str(j)] == variables['king']).ite():
                variables['kingx'] = ii
                variables['kingy'] = j-1
                variables['kingpos'] = str(i)+str(j)
            variables.merge()

    def make_move(dx, dy):
        if dy == -1: dy = 7
        if dx == -1: dx = 7
        variables.fork_with_new_var('inactive',
                                    {"dy": i2s(dy),
                                     "dx": i2s(dx)})
            

    if (variables['kingx'] > 0).ite():
        make_move(-1, 0)
        if (variables['kingy'] > 0).ite():
            make_move(-1, -1)
        variables.merge()
        if (variables['kingy'] < 7).ite():
            make_move(-1, 1)
        variables.merge()
    variables.merge()
    if (variables['kingx'] < 7).ite():
        make_move(1, 0)
        if (variables['kingy'] > 0).ite():
            make_move(1, -1)
        variables.merge()
        if (variables['kingy'] < 7).ite():
            make_move(1, 1)
        variables.merge()
    variables.merge()
    
    if (variables['kingy'] > 0).ite():
        make_move(0, -1)
    variables.merge()
    if (variables['kingy'] < 7).ite():
        make_move(0, 1)
    variables.merge()

    variables.pause("main")
    variables.reactivate("inactive")

    variables['kingx'] = variables['kingx'] + variables['dx']
    variables['kingy'] = variables['kingy'] + variables['dy']

    if (variables['kingx'] >= 8).ite():
        variables['kingx'] = variables['kingx'] - 8
    variables.merge()

    if (variables['kingy'] >= 8).ite():
        variables['kingy'] = variables['kingy'] - 8
    variables.merge()

    variables.intxy_to_location('kingx', 'kingy')
    variables.assign_pop("newking")
    if (variables[variables['newking']].isany(color([' ', 'K', 'Q', 'R', 'B', 'N', 'P'], inv=True))).ite():
        variables.lookup("newking")
        variables.push(color("k"))
        variables.indirect_assign()
        variables.lookup("kingpos")
        variables.push(" ")
        variables.indirect_assign()
    else:
        variables.destroy_active_threads()
    variables.merge()

    variables["ep"] = '-'
    
    variables.contract_chess()
    join_sub_to_main(variables, 8)

    variables.assign_stack_to('legal_king_moves', 8)

    variables.delete_var('kingx')
    variables.delete_var('kingy')
    variables.delete_var('kingpos')
    variables.delete_var('king')
    variables.contract_chess()
    variables.pop()
    
    return variables

def rook_moves(variables, color, rook_piece='r'):
    return bishop_moves(variables, color, rook_piece, 'rook', dydx=[(7, 0), (1, 0), (0, 1), (0, 7)])


def bishop_moves(variables, color, bishop_piece='b', name='bishop', dydx=[(7, 7), (7, 1), (1, 7), (1, 1)]):
    # This is a brutal function, I'm very sorry if you're reading this.
    
    variables.lookup('initial_board')
    variables.expand_chess()
    

    # Initialize lists to hold bishop positions
    variables[name+'x_lst'] = ''
    variables[name+'y_lst'] = ''
    variables[name+'pos_lst'] = ''
    variables[name+'piece_lst'] = ''

    # Identify positions of all bishops of the given color
    for ii, i in enumerate('abcdefgh'):
        for j in range(1, 9):
            if (variables[str(i)+str(j)].isany(color(['q', 'r', 'b']))).ite():
                variables[name+'x_lst'] += i2s(ii) + ";"
                variables[name+'y_lst'] += i2s(j-1) + ";"
                variables[name+'pos_lst'] += str(i)+str(j) + ";"
                variables[name+'piece_lst'] += variables[str(i)+str(j)]
                variables[name+'piece_lst'] += ';'
            variables.merge()

    MAX_BISHOPS = 6  # Maximum bishops to process
    for iteration in range(MAX_BISHOPS):
        if (variables[name+'x_lst'] != "").ite():
            variables.settype(name+'x', 'int')
            variables.settype(name+'y', 'int')
            variables.list_pop(name+'x_lst', name+'x')
            variables.list_pop(name+'y_lst', name+'y')
            variables.list_pop(name+'pos_lst', name+'pos')
            variables.list_pop(name+'piece_lst', 'rook_piece')
            variables.fork_inactive("wait1")
        variables.merge()

    variables.pause("toplevel")
    variables.reactivate("wait1")

    variables['legal_'+name+'_moves'] = ''
    if True:
        if True:
            variables['next_lst'] = ''
            variables[name+'x_tmp'] = variables[name+'x']
            variables[name+'y_tmp'] = variables[name+'y']

            if (variables['rook_piece'] == color('B')).ite():
                for dx, dy in [(7, 7), (7, 1), (1, 7), (1, 1)]:
                    variables['dy'] = dy
                    variables['dx'] = dx
                    variables[name+'x'] = variables[name+'x_tmp']
                    variables[name+'y'] = variables[name+'y_tmp']
                    variables['ok'] = "True"
                    variables.fork_inactive("waiting")
            variables.merge()
            if (variables['rook_piece'] == color('R')).ite():
                for dx, dy in [(7, 0), (1, 0), (0, 7), (0, 1)]:
                    variables['dy'] = dy
                    variables['dx'] = dx
                    variables[name+'x'] = variables[name+'x_tmp']
                    variables[name+'y'] = variables[name+'y_tmp']
                    variables['ok'] = "True"
                    variables.fork_inactive("waiting")
            variables.merge()
            if (variables['rook_piece'] == color('Q')).ite():
                for dx, dy in [(7, 0), (1, 0), (0, 7), (0, 1)] + [(7, 7), (7, 1), (1, 7), (1, 1)]:
                    variables['dy'] = dy
                    variables['dx'] = dx
                    variables[name+'x'] = variables[name+'x_tmp']
                    variables[name+'y'] = variables[name+'y_tmp']
                    variables['ok'] = "True"
                    variables.fork_inactive("waiting")
            variables.merge()

            if True:
                variables.pop()
                variables.pause("bishwait")
                variables.reactivate("waiting")
                for i in range(8):
                    variables[name+'x'] += variables['dx']
                    if (variables[name+'x'] >= 8).ite():
                        variables[name+'x'] -= 8
                    variables.merge()

                    if (variables['dx'] == 1).ite():
                        variables['ok'] = variables['ok'] & (variables[name+'x'] != 0)
                    variables.merge()
                    if (variables['dx'] == 7).ite():
                        variables['ok'] = variables['ok'] & (variables[name+'x'] != 7)
                    variables.merge()

                    variables[name+'y'] += variables['dy']
                    if (variables[name+'y'] >= 8).ite():
                        variables[name+'y'] -= 8
                    variables.merge()
                    
                    if (variables['dy'] == 1).ite():
                        variables['ok'] = variables['ok'] & (variables[name+'y'] != 0)
                    variables.merge()
                    if (variables['dy'] == 7).ite():
                        variables['ok'] = variables['ok'] & (variables[name+'y'] != 7)
                    variables.merge()

                    if variables['ok'].ite():

                        variables.intxy_to_location(name+'x', name+'y')
                        variables.assign_pop("newbishop")

                        if (variables[variables['newbishop']].isany(color([' ', 'K', 'Q', 'R', 'B', 'N', 'P'], inv=True))).ite():
                            variables['next_lst'] += variables['newbishop'] + ";"
                        variables.merge()

                        variables['ok'] &= variables[variables['newbishop']] == " "
                    variables.merge()

            variables.lookup("next_lst")
            join_sub_to_main(variables, 32, main="bishwait", sub="3sub")
            variables.assign_stack_to('next_lst', 40)
            variables.fix_double_list()

            variables.variable_uniq("next_lst")
            for _ in range(32):
                if (variables['next_lst'] != "").ite():
                    variables.list_pop('next_lst', 'new_bishpos')
                    variables.fork_inactive("inactive")
                variables.merge()

            variables.pause("main")
            variables.reactivate("inactive")

            variables.lookup("new_bishpos")
            variables.lookup('rook_piece')
            variables.indirect_assign()
            variables.lookup(name+"pos")
            variables.push(" ")
            variables.indirect_assign()
            variables["ep"] = '-'
            variables.contract_chess()
            join_sub_to_main(variables, 32, sub="2sub")
            variables.assign_stack_to('xtmp', 40)
    variables.lookup("xtmp")
    join_sub_to_main(variables, 32, main="toplevel", sub="4sub")
    variables.assign_stack_to('legal_'+name+'_moves', 64)

    variables.contract_chess()
    variables.pop()

    # Cleanup temporary variables
    variables.delete_var('new_bishpos')
    variables.delete_var('newbishop')
    variables.delete_var(name+'pos')
    variables.delete_var(name+'x')
    variables.delete_var(name+'y')
    variables.delete_var(name+'x_tmp')
    variables.delete_var(name+'y_tmp')
    variables.delete_var(name+'x_lst')
    variables.delete_var(name+'y_lst')
    variables.delete_var(name+'pos_lst')
    variables.delete_var('next_lst')
    variables.delete_var('xtmp')
    variables.delete_var('ok')

    return variables

def queen_moves(variables, color):
    rook_moves(variables, color, 'q')
    variables['legal_queen_moves'] = variables['legal_rook_moves']
    variables.variable_uniq("legal_queen_moves")

def pawn_moves(variables, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    
    if color == color_white:
        ep_rank = 4  # White pawns must be on rank 5 to capture EP
    else:
        ep_rank = 3  # Black pawns must be on rank 4 to capture EP

    find_pieces(variables, color, 'pawn', 'p')

    MAX_PAWNS = 8
    for iteration in range(MAX_PAWNS):
        if (variables['pawnx_lst'] != "").ite():
            variables.settype('pawnx', 'int')
            variables.settype('pawny', 'int')
            variables.list_pop('pawnx_lst', 'pawnx')
            variables.list_pop('pawny_lst', 'pawny')
            variables.list_pop('pawnpos_lst', 'pawnpos')
            variables.fork_inactive("inactivep1")
        variables.merge()
    
    
    variables.pause("mainp1")
    variables.reactivate("inactivep1")
    variables.delete_var('pawnx_lst')
    variables.delete_var('pawny_lst')
    variables.delete_var('pawnpos_lst')

    if True:
        if True:
            variables['next_lst'] = ''
            
            if color == color_white:
                variables['forward'] = variables['pawny'] + 1
            else:
                variables['forward'] = variables['pawny'] - 1
            variables['left'] = variables['pawnx'] + 1
            variables['right'] = variables['pawnx'] - 1

            variables.intxy_to_location('pawnx', 'forward')
            variables.assign_pop("newpawn")

            if (variables[variables['newpawn']] == " ").ite():
                variables['next_lst'] += variables['newpawn'] + ";"
            variables.merge()

            variables.intxy_to_location('left', 'forward')
            variables.assign_pop("newpawn")
            if (variables[variables['newpawn']].isany(color(['K', 'Q', 'R', 'B', 'N', 'P'], inv=True))).ite():
                variables['next_lst'] += variables['newpawn'] + ";"
            variables.merge()
            
            if ((variables['pawny'] == ep_rank) & (variables['newpawn'] == variables['ep'])).ite():
                variables['next_lst'] += variables['newpawn'] + ";"
            variables.merge()

            variables.intxy_to_location('right', 'forward')
            variables.assign_pop("newpawn")
            if ((variables['pawnx'] != 0) & variables[variables['newpawn']].isany(color(['K', 'Q', 'R', 'B', 'N', 'P'], inv=True))).ite():
                variables['next_lst'] += variables['newpawn'] + ";"
            variables.merge()

            if ((variables['pawny'] == ep_rank) & (variables['newpawn'] == variables['ep'])).ite():
                variables['next_lst'] += variables['newpawn'] + ";"
            variables.merge()
            
            # first rank
            if (variables['pawny'] == (1 if color == color_white else 6)).ite():
                if color == color_white:
                    variables['forward2'] = variables['pawny'] + 2
                else:
                    variables['forward2'] = variables['pawny'] - 2
                pass
            else:
                variables['forward2'] = variables['pawny']
            variables.merge()

            # En passant captures
            if (variables['pawny'] == ep_rank).ite():
                # Check if pawn is in correct position for EP capture
                variables.intxy_to_location('pawnx', 'forward')
                variables.assign_pop("ep_dest")
                if (variables['ep_dest'] == variables['ep']).ite():
                    # EP capture is available
                    variables['next_lst'] += variables['ep_dest'] + ";"
                variables.merge()
            variables.merge()

            variables.intxy_to_location('pawnx', 'forward')
            variables.assign_pop("newpawn1")
            variables.intxy_to_location('pawnx', 'forward2')
            variables.assign_pop("newpawn2")
            if ((variables[variables['newpawn1']] == " ") & (variables[variables['newpawn2']] == " ")).ite():
                variables['next_lst'] += variables['newpawn2'] + ";"

            variables.merge()

            variables.variable_uniq("next_lst")
            for _ in range(4):
                if (variables['next_lst'] != "").ite():
                    variables.list_pop('next_lst', 'new_pawnpos')
                    variables.fork_inactive("inactive")
                variables.merge()

            variables.contract_chess()
            variables.pause("main")
            variables.reactivate("inactive")

            variables.lookup("new_pawnpos")
            variables.push(color("p"))
            variables.indirect_assign()
            variables.lookup("pawnpos")
            variables.push(" ")
            variables.indirect_assign()

            if (variables['new_pawnpos'] == variables['ep']).ite():
                variables.lookup('ep')
                variables.square_to_xy()
                variables.settype('ep_x', 'int')
                variables.settype('ep_y', 'int')
                variables.assign_pop('ep_x')
                variables.assign_pop('ep_y')
                variables['ep_y'] += -1 if color == color_white else 1
                variables.intxy_to_location('ep_x', 'ep_y')
                variables.push(" ")
                variables.indirect_assign()
            variables.merge()

            variables.settype('np_x', 'int')
            variables.settype('np_y', 'int')
            variables.settype('op_y', 'int')
            
            variables.lookup('new_pawnpos')
            variables.square_to_xy()
            variables.assign_pop("np_x")
            variables.assign_pop("np_y")

            variables.lookup('pawnpos')
            variables.square_to_xy()
            variables.pop()
            variables.assign_pop("op_y")
            
            if color == color_white:
                variables["top"] = variables["np_y"] - variables["op_y"]
            else:
                variables["top"] = variables["op_y"] - variables["np_y"]
                
            if (variables['top'] == 2).ite():
                if color == color_white:
                    variables["ep_y"] = 2
                else:
                    variables["ep_y"] = 5
                variables.intxy_to_location('np_x', 'ep_y')
                variables.assign_pop("ep")
            else:
                variables["ep"] = '-'
            variables.merge()

            variables.promote_to_queen()
            
            variables.contract_chess()
            join_sub_to_main(variables, 4)

    variables.assign_stack_to('legal_pawn_moves', 4)
    variables.variable_uniq("legal_pawn_moves")
    variables.lookup("legal_pawn_moves")
    join_sub_to_main(variables, 8, main="mainp1")
    variables.assign_stack_to('legal_pawn_moves', 32)
    
    
    variables.delete_var('pawnx_lst')
    variables.delete_var('pawny_lst')
    variables.delete_var('pawnpos_lst')
    variables.delete_var('pawnx')
    variables.delete_var('pawny')
    variables.delete_var('pawnpos')
    variables.delete_var('forward')
    variables.delete_var('forward2')
    variables.delete_var('left')
    variables.delete_var('right')
    variables.delete_var('newpawn')
    variables.delete_var('newpawn1')
    variables.delete_var('newpawn2')
    variables.delete_var('next_lst')
    variables.delete_var('new_pawnpos')
    variables.delete_var('ep_dest')
    variables.delete_var('ep_x')
    variables.delete_var('ep_y')
    variables.delete_var('op_x')
    variables.delete_var('op_y')
    variables.delete_var('np_x')
    variables.delete_var('np_y')
    variables.contract_chess()
    variables.pop()

    
def knight_moves(variables, color, knight_piece='n'):
    variables.lookup('initial_board')
    variables.expand_chess()

    variables['knightx_lst'] = ''
    variables['knighty_lst'] = ''
    variables['knightpos_lst'] = ''

    for ii, i in enumerate('abcdefgh'):
        for j in range(1, 9):
            if (variables[str(i)+str(j)] == color(knight_piece)).ite():
                variables['knightx_lst'] += i2s(ii) + ";"
                variables['knighty_lst'] += i2s(j - 1) + ";"
                variables['knightpos_lst'] += str(i) + str(j) + ";"
            variables.merge()

    MAX_KNIGHTS = 2
    for iteration in range(MAX_KNIGHTS):
        if (variables['knightx_lst'] != "").ite():
            variables.settype('knightx', 'int')
            variables.settype('knighty', 'int')
            variables.list_pop('knightx_lst', 'knightx')
            variables.list_pop('knighty_lst', 'knighty')
            variables.list_pop('knightpos_lst', 'knightpos')

            variables['next_lst'] = ''

            # Handle +2 moves first (no safety check needed for addition)
            if (variables['knightx'] < 6).ite():  # Has room to move +2 in x
                if (variables['knighty'] < 7).ite():  # Has room for +1 in y
                    variables['tmpx'] = variables['knightx'] + 2
                    variables['tmpy'] = variables['knighty'] + 1
                    add_knight_move(variables, color)
                variables.merge()
                if (variables['knighty'] >= 1).ite():  # Has room for -1 in y
                    variables['tmpx'] = variables['knightx'] + 2
                    variables['tmpy'] = variables['knighty'] - 1
                    add_knight_move(variables, color)
                variables.merge()
            variables.merge()

            # Handle -2 moves (need check for x >= 2)
            if (variables['knightx'] >= 2).ite():
                if (variables['knighty'] < 7).ite():  # Has room for +1 in y
                    variables['tmpx'] = variables['knightx'] - 2
                    variables['tmpy'] = variables['knighty'] + 1
                    add_knight_move(variables, color)
                variables.merge()
                if (variables['knighty'] >= 1).ite():  # Has room for -1 in y
                    variables['tmpx'] = variables['knightx'] - 2
                    variables['tmpy'] = variables['knighty'] - 1
                    add_knight_move(variables, color)
                variables.merge()
            variables.merge()

            # Handle +1 moves in x
            if (variables['knightx'] < 7).ite():  # Has room for +1 in x
                if (variables['knighty'] < 6).ite():  # Has room for +2 in y
                    variables['tmpx'] = variables['knightx'] + 1
                    variables['tmpy'] = variables['knighty'] + 2
                    add_knight_move(variables, color)
                variables.merge()
                if (variables['knighty'] >= 2).ite():  # Has room for -2 in y
                    variables['tmpx'] = variables['knightx'] + 1
                    variables['tmpy'] = variables['knighty'] - 2
                    add_knight_move(variables, color)
                variables.merge()
            variables.merge()

            # Handle -1 moves in x
            if (variables['knightx'] >= 1).ite():  # Has room for -1 in x
                if (variables['knighty'] < 6).ite():  # Has room for +2 in y
                    variables['tmpx'] = variables['knightx'] - 1
                    variables['tmpy'] = variables['knighty'] + 2
                    add_knight_move(variables, color)
                variables.merge()
                if (variables['knighty'] >= 2).ite():  # Has room for -2 in y
                    variables['tmpx'] = variables['knightx'] - 1
                    variables['tmpy'] = variables['knighty'] - 2
                    add_knight_move(variables, color)
                variables.merge()
            variables.merge()

            variables.variable_uniq("next_lst")
            for _ in range(8):
                if (variables['next_lst'] != "").ite():
                    variables.list_pop('next_lst', 'new_knightpos')
                    variables.fork_inactive("inactive")
                variables.merge()

            variables.contract_chess()
            variables.pause("main")
            variables.reactivate("inactive")

            variables.lookup("new_knightpos")
            variables.push(color(knight_piece))
            variables.indirect_assign()

            variables.lookup("knightpos")
            variables.push(" ")
            variables.indirect_assign()

            variables["ep"] = '-'

            variables.contract_chess()
            join_sub_to_main(variables, 16)
        else:
            variables.contract_chess()

        variables.merge()
        if iteration != MAX_KNIGHTS - 1:
            variables.lookup('initial_board')
            variables.expand_chess()

    variables.assign_stack_to('legal_knight_moves', 40)

    # Cleanup
    variables.delete_var('knightx')
    variables.delete_var('knighty')
    variables.delete_var('knightpos')
    variables.delete_var('knightx_lst')
    variables.delete_var('knighty_lst')
    variables.delete_var('knightpos_lst')
    variables.delete_var('new_knightpos')
    variables.delete_var('newknight')
    variables.delete_var('next_lst')
    variables.delete_var('tmpx')
    variables.delete_var('tmpy')

    return variables

# Helper method to add a valid
def add_knight_move(variables, color):
    variables.intxy_to_location('tmpx', 'tmpy')
    variables.assign_pop("newknight")
    if (variables[variables['newknight']]
        .isany(color([' ', 'K', 'Q', 'R', 'B', 'N', 'P'], inv=True))
        ).ite():
        variables['next_lst'] += variables['newknight'] + ";"
    variables.merge()

def is_square_under_attack_by_rook(variables, sq, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    def square(x, y):
        return variables[chr(0x61+x)+str(y)]
    start_x = ord(sq[0])-0x61
    start_y = int(sq[1])

    for dy, dx in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        for i in range(1, 8):
            end_x = start_x + i * dx
            end_y = start_y + i * dy
            if 0 <= end_x < 8 and 1 <= end_y < 9:
                if i > 1:
                    empty = (square(start_x + dx, start_y + dy) == ' ')
                    for j in range(2, i):
                        empty = empty & (square(start_x + j * dx, start_y + j * dy) == ' ')
                    variables['attacked'] |= empty & (square(end_x, end_y).isany(color(['R', 'Q'])))
                else:
                    variables['attacked'] |= (square(end_x, end_y).isany(color(['R', 'Q'])))
    variables.contract_chess()
    return variables

def is_square_under_attack_by_bishop(variables, sq, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    def square(x, y):
        return variables[chr(0x61+x)+str(y)]
    start_x = ord(sq[0])-0x61
    start_y = int(sq[1])
    
    # Change to diagonal directions
    for dy, dx in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        for i in range(1, 8):
            end_x = start_x + i * dx
            end_y = start_y + i * dy
            if 0 <= end_x < 8 and 1 <= end_y < 9:
                if i > 1:
                    empty = (square(start_x + dx, start_y + dy) == ' ')
                    for j in range(2, i):
                        empty = empty & (square(start_x + j * dx, start_y + j * dy) == ' ')
                    variables['attacked'] |= empty & (square(end_x, end_y).isany([color('B'), color('Q')]))
                else:
                    variables['attacked'] |= square(end_x, end_y).isany([color('B'), color('Q')])
    variables.contract_chess()
    return variables

def is_square_under_attack_by_knight(variables, sq, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    def square(x, y):
        return variables[chr(0x61+x)+str(y)]
    start_x = ord(sq[0])-0x61
    start_y = int(sq[1])

    # Check all 8 knight move squares:
    for dx, dy in [
        (-2,-1), (-2,1),  # Left 2, up/down 1
        (2,-1),  (2,1),   # Right 2, up/down 1
        (-1,-2), (-1,2),  # Left 1, up/down 2
        (1,-2),  (1,2)    # Right 1, up/down 2
    ]:
        end_x = start_x + dx
        end_y = start_y + dy
        if 0 <= end_x < 8 and 1 <= end_y <= 8:
            variables['attacked'] |= (square(end_x, end_y) == color('N'))

    variables.contract_chess()
    return variables

def is_square_under_attack_by_pawn(variables, sq, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    def square(x, y):
        return variables[chr(0x61+x)+str(y)]
    start_x = ord(sq[0])-0x61
    start_y = int(sq[1])

    # Direction depends on attacking color
    # White pawns attack upward (target must be above them)
    # Black pawns attack downward (target must be below them)
    dy = -1 if color == color_white else 1

    # Check the two possible attacking pawn positions
    for dx in [-1, 1]:
        end_x = start_x + dx
        end_y = start_y + dy
        if 0 <= end_x < 8 and 1 <= end_y <= 8:
            variables['attacked'] |= (square(end_x, end_y) == color('P'))

    variables.contract_chess()
    return variables

def is_square_under_attack_by_king(variables, sq, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    def square(x, y):
        return variables[chr(0x61+x)+str(y)]
    start_x = ord(sq[0])-0x61
    start_y = int(sq[1])

    # Check all 8 adjacent squares:
    for dx, dy in [
        (-1,-1), (0,-1), (1,-1),  # Below
        (-1,0),          (1,0),   # Same rank
        (-1,1),  (0,1),  (1,1)    # Above
    ]:
        end_x = start_x + dx
        end_y = start_y + dy
        if 0 <= end_x < 8 and 1 <= end_y <= 8:
            variables['attacked'] |= (square(end_x, end_y) == color('K'))

    variables.contract_chess()
    return variables

def is_square_under_attack(variables, sq, color, push=True):
    if push:
        variables['attacked'] = 'False'
    is_square_under_attack_by_rook(variables, sq, color)
    variables.pop()
    is_square_under_attack_by_bishop(variables, sq, color)
    variables.pop()
    is_square_under_attack_by_knight(variables, sq, color)
    variables.pop()
    is_square_under_attack_by_pawn(variables, sq, color)
    variables.pop()
    is_square_under_attack_by_king(variables, sq, color)
    variables.pop()

def prepare_human_move(variables, has_move):
    variables.expand_chess()
    variables.make_pretty(has_move)

def make_human_move(variables, has_move):
    variables.unpretty(has_move)
    if not has_move:
        variables.contract_chess()
        variables.assign_pop('initial_board')
        return

    variables.contract_chess()
    variables.assign_pop('before_move_board')
    variables.lookup('before_move_board')
    variables.expand_chess()

    #variables.doprint()
    
    if ((variables['src'] == 'e1') & (variables['dst'] == 'g1')  & (variables[variables['src']] == 'K')).ite():
        variables['f1'] = 'R'
        variables['h1'] = ' '
    variables.merge()
    if ((variables['src'] == 'e1') & (variables['dst'] == 'c1')  & (variables[variables['src']] == 'K')).ite():
        variables['d1'] = 'R'
        variables['a1'] = ' '
    variables.merge()
    if ((variables['dst'] == variables['ep'])  & (variables[variables['src']] == 'P')).ite():
        for s in 'abcdefgh':
            if (variables['ep'] == s+'6').ite():
                variables[s+'5'] = ' '
            variables.merge()
    variables.merge()

    variables['tmp3'] = variables[variables['src']]
    variables['tmp2'] = variables[variables['dst']]
    
    if ((variables[variables['src']] == 'P') & ((variables['dst'] == 'a1') | (variables['dst'] == 'b1') | (variables['dst'] == 'c2') | (variables['dst'] == 'd1') | (variables['dst'] == 'e1') | (variables['dst'] == 'f1') | (variables['dst'] == 'g1') | (variables['dst'] == 'h1'))).ite():
        variables['tmp3'] = 'Q'
    variables.merge()
    

    variables.lookup("dst")
    variables.lookup("tmp3")
    variables.indirect_assign()

    variables.lookup("src")
    variables.push(" ")
    variables.indirect_assign()

    
    
    variables.contract_chess()
    variables.assign_pop("after_move")

    variables.delete_var('tmp3')
    variables.delete_var('tmp2')
    variables.delete_var('dst')
    variables.delete_var('src')
    variables.delete_var('move')

       

    variables['initial_board'] = variables['before_move_board']
    variables.delete_var('before_move_board')
    
    compute_legal_boards(variables, color_white, color_black)

    if (variables['initial_board'].fen() != variables['after_move'].fen()).ite():
        variables.destroy_active_threads()
    variables.merge()
    variables.illegal_move()

    variables.delete_var('after_move')

def castle_moves(variables, color):
    variables.lookup('initial_board')
    variables.expand_chess()
    
    variables['legal_castle_moves'] = ''

    # Check kingside castle
    if (variables['castle_' + ('white' if color == color_white else 'black') + '_king']).ite():
        # Check if squares between king and rook are empty
        if color == color_white:
            king_empty = (variables['f1'] == ' ') & (variables['g1'] == ' ')
            path_squares = ['e1', 'f1']
        else:
            king_empty = (variables['f8'] == ' ') & (variables['g8'] == ' ')
            path_squares = ['e8', 'f8']

        variables.contract_chess()
            
        # Check if path is under attack
        variables['attacked'] = 'False'
        for sq in path_squares:
            is_square_under_attack(variables, sq, color_white if color == color_black else color_black, push=False)

        variables.expand_chess()

        if (king_empty & ~variables['attacked']).ite():
            if color == color_white:
                # Move white king
                variables['e1'] = ' '
                variables['g1'] = color('K')
                # Move white rook
                variables['h1'] = ' '
                variables['f1'] = color('R')
            else:
                # Move black king
                variables['e8'] = ' '
                variables['g8'] = color('K')
                # Move black rook  
                variables['h8'] = ' '
                variables['f8'] = color('R')
            variables.contract_chess()
            variables['legal_castle_moves'] += variables.peek()
            variables['legal_castle_moves'] += ";"
            variables.lookup('initial_board')
            variables.expand_chess()
        variables.merge()
    variables.merge()

    # Check queenside castle
    if (variables['castle_' + ('white' if color == color_white else 'black') + '_queen']).ite():
        # Check if squares between king and rook are empty
        if color == color_white:
            queen_empty = (variables['b1'] == ' ') & (variables['c1'] == ' ') & (variables['d1'] == ' ')
            path_squares = ['d1', 'e1']
        else:
            queen_empty = (variables['b8'] == ' ') & (variables['c8'] == ' ') & (variables['d8'] == ' ')
            path_squares = ['d8', 'e8']

        variables.contract_chess()
            
        # Check if path is under attack
        variables['attacked'] = 'False'
        for sq in path_squares:
            is_square_under_attack(variables, sq, color_white if color == color_black else color_black, push=False)

        variables.expand_chess()

        if (queen_empty & ~variables['attacked']).ite():
            if color == color_white:
                # Move white king
                variables['e1'] = ' '
                variables['c1'] = color('K')
                # Move white rook
                variables['a1'] = ' '
                variables['d1'] = color('R')
            else:
                # Move black king  
                variables['e8'] = ' '
                variables['c8'] = color('K')
                # Move black rook
                variables['a8'] = ' '
                variables['d8'] = color('R')
            variables.contract_chess()
            variables['legal_castle_moves'] += variables.peek()
            variables['legal_castle_moves'] += ";"
            variables.lookup('initial_board')
            variables.expand_chess()
        variables.merge()
    variables.merge()

    variables.contract_chess()
    return variables    

def compute_next_boards(variables, color, castle=True):
    """
    Returns the output boards in the next_boards variable
    """

    variables.fork_inactive("tmp")
    variables.pause("cur_state")
    variables.reactivate("tmp")
    #variables.delete_var("before_move_board")
    #variables.delete_var("after_move")
    #variables.delete_var("saved_board")
    
    if castle:
        castle_moves(variables, color)
        variables['legal_moves'] = variables['legal_castle_moves']
        variables.delete_var('legal_castle_moves')
        variables.fork_inactive("save")
        variables.delete_var('legal_moves')
    
    king_moves(variables, color)
    variables['legal_moves'] = variables['legal_king_moves']
    variables.delete_var('legal_king_moves')
    variables.fork_inactive("save")
    variables.delete_var('legal_moves')
    
    bishop_moves(variables, color)
    variables['legal_moves'] = variables['legal_bishop_moves']
    variables.delete_var('legal_bishop_moves')
    variables.fork_inactive("save")
    variables.delete_var('legal_moves')
    
    knight_moves(variables, color)
    variables['legal_moves'] = variables['legal_knight_moves']
    variables.delete_var('legal_knight_moves')
    variables.fork_inactive("save")
    variables.delete_var('legal_moves')
    
    pawn_moves(variables, color)
    variables['legal_moves'] = variables['legal_pawn_moves']
    variables.delete_var('legal_pawn_moves')
    variables.fork_inactive("save")
    variables.delete_var('legal_moves')

    variables.pause("main")
    variables.reactivate("save")
    variables.lookup("legal_moves")
    join_sub_to_main(variables, 8)
    variables.assign_stack_to('next_boards', 8)
    variables.lookup("next_boards")
    variables.pause("sub")
    variables.fix_double_list()

    variables.reactivate("cur_state")
    variables.join_pop("sub")
    variables.assign_pop("next_boards")
    
    return variables

def compute_legal_boards(variables, color_one, color_two, do_score=False):
    variables['saved_board'] = variables['initial_board']
    compute_next_boards(variables, color_one)

    variables.fix_double_list()
    for _ in range(100):
        if (variables['next_boards'] != '').ite():
            variables.fork_list_pop('next_boards', 'initial_board', 'maybe')
        variables.merge()
    variables.destroy_active_threads()
    variables.reactivate("maybe")

    if (variables['initial_board'] == variables['saved_board']).ite():
        variables.destroy_active_threads()
    variables.merge()
    
    # Castling won't invalidate any more boards than just rook moves
    compute_next_boards(variables, color_two, castle=False)
    variables.fix_double_list()

    variables.check_king_alive()

    if (variables['alive']).ite():
        variables.pause('legal')
    variables.merge()
    variables.destroy_active_threads()
    variables.reactivate('legal')

    if (variables['saved_board'] == variables['initial_board']).ite():
        variables.destroy_active_threads()
    variables.merge()
    
    if do_score:
        for _ in range(100):
            if (variables['next_boards'] != '').ite():
                variables.fork_list_pop('next_boards', 'toscore', 'nmaybe')
            variables.merge()
        variables.pause("waiting")
        variables.reactivate("nmaybe")
        variables.lookup("toscore")

        variables.piece_value()
        variables.keep_only_max_thread()
        variables.pause("scored")
        variables.reactivate("waiting")
        variables.destroy_active_threads()
        variables.reactivate("scored")
        variables.delete_var("next_boards")
        variables.delete_var('saved_board')
        variables.delete_var('alive')
        return
        
    variables.delete_var("next_boards")
    variables.delete_var('saved_board')
    variables.delete_var('alive')
    variables.lookup('initial_board')

def flip_square(square):
    """
    Convert a chess square to its mirror position.
    e.g., 'a1' -> 'h8', 'b2' -> 'g7', etc.
    
    Args:
        square (str): Chess square in format 'a1' through 'h8'
    
    Returns:
        str: Mirrored square position
    """
    file, rank = square[0], int(square[1])
    
    # Flip rank (1->8, 2->7, etc.) 
    new_rank = 9 - rank
    
    return file + str(new_rank)


def is_flipped_board(variables):
    variables.expand_chess()
    variables.push("True")
    for row in "1234":
        for col in "abcdefgh":
            square = col+row
            variables.lookup(square)
            variables.lookup(flip_square(square))
            variables.is_same_kind()
            variables.boolean_and()
    variables.assign_pop("foo")
    if (variables['foo'] == 'True').ite():
        variables.push("AA")
    else:
        variables.push("A")
    variables.merge()
        
    variables.contract_chess()
    
def make_reply_move(variables, has_move=True):
    make_human_move(variables, has_move)
    variables.pop()

    compute_legal_boards(variables, color_black, color_white, do_score=True)

    variables.lookup("initial_board")
    is_flipped_board(variables)
    variables.pop()
    variables.sub_unary()
    variables.keep_only_min_thread()
    variables.keep_only_last_thread()
    variables.pop()

    variables.lookup('initial_board')
    variables.test_checkmate()
    
    prepare_human_move(variables, has_move)
