"""Prubot


"""
import pythoncom
pythoncom.CoInitialize() # To import CLR with PyQt4 without OLE Error
import clr
import sys
from PyQt4 import QtGui, QtCore

clr.AddReference('TibiaAPI')
import Tibia
import System  # System.UInt32

from ast import literal_eval
from os.path import isfile
from pdb import set_trace
from time import sleep, time

# from tibiaids import loot_gold, loot_stack, loot_commons, loot_rares
# from tibiaids import loot_list, loot_test
# from tibiaids import *
import tibiaids as tid


"""Initializations
"""
# variables needed for all functions

# Get Client
# client = Tibia.Objects.Client.GetClients()[1]
client = Tibia.Util.ClientChooser.ShowBox()
print client
inven = client.Inventory

# player = client.GetPlayer()
def bot_init():
    """Function refreshes objects that might get outdated after logging in/out
    """
    client.Console.Say('Hello World')
    global player
    player = client.GetPlayer()

bot_init()

# Remove path blocking objects
for i in tid.obstacle_list:
    item = Tibia.Objects.Item(client, System.UInt32(i))
    item.SetFlag(Tibia.Addresses.DatItem.Flag.BlocksPath, False)



"""General useful functions for working with TibiaAPI
"""
def find_player_tile():
    """Finds and returns the player tile map memory structure

    O(n^2) or less?
    """
    if client.LoggedIn:
        try:
            # Try to catch System.NUllReferenceException race condition
            if client.Map.GetTileWithPlayer(): #
                floor_tiles = list(client.Map.GetTilesOnSameFloor())
                # floor_tiles = get_floor_tiles()
                floor_obj_data = [[i.Data for i in list(j.Objects)] for j in floor_tiles]
                # floor_objs = [list(j.Objects) for j in floor_tiles]
                # floor_obj_ids = [[i.Data for i in j] for j in floor_objs]

                for obj in range(0, len(floor_obj_data)): # 252
                    if player.Id in floor_obj_data[obj]:
                        return floor_tiles[obj] # Player tile
        except:
            pass

    print 'Player tile not found'
    return None

# def get_floor_tiles():
#     # floor_tiles = list(client.Map.GetTilesOnSameFloor()) # Bugged out often
#     tiles = list(client.Map.GetTiles())
#
#     # Calculate Memory Location
#     if player.Z >= 8: # Below Ground
#         mfloor = 2
#     else:
#         mfloor = abs(player.Z - 7)
#
#     return tiles[(mfloor*252):((mfloor+1)*252)]

def tile_to_rel_loc(tile, player_tile):
    """Calculates relative position of two tile objects: 'tile' to 'player_tile'
    Returns a tuple XYZ

    """
    xbound = (-8, 9)
    ybound = (-6, 7)

    # Memory Location differences
    xmdiff = tile.MemoryLocation.X - player_tile.MemoryLocation.X
    ymdiff = tile.MemoryLocation.Y - player_tile.MemoryLocation.Y
    zmdiff = tile.MemoryLocation.Z - player_tile.MemoryLocation.Z

    if xbound[0] <= xmdiff <= xbound[1]: # within bounds
        xloc = xmdiff
    elif xmdiff < xbound[0]: # Actually to the right
        xloc = xmdiff + 18
    elif xmdiff > xbound[1]: # Actually to the left
        xloc = xmdiff - 18

    if ybound[0] <= ymdiff <= ybound[1]:
        yloc = ymdiff
    elif ymdiff < ybound[0]: # Actually north
        yloc = ymdiff + 18
    elif ymdiff > ybound[1]: # Actually south
        yloc = ymdiff - 18

    zloc = zmdiff

    return (xloc, yloc, zloc)

def tile_to_world_loc(tile, player_tile):
    """Calculates the global position of 'tile', using relative position to
    'player_tile'. Returns a tuple XYZ with world location

    """
    relxyz = tile_to_rel_loc(tile, player_tile)

    return (player.X + relxyz[0], player.Y + relxyz[1], player.Z + relxyz[2])

def get_bl_creats():
    return list(client.BattleList.GetCreatures())

def test_pnc(id):
    """Tests creature.Id to see if creature is player, creature, or NPC
    """
    if id < int('0x10ffffff', 16): # 285212671
        return 'player'
    elif id < int('0x40ffffff', 16): # 1090519039
        return 'creature'
    elif id < int('0x80000fff', 16): # 2147487743
        return 'npc'
    else:
        print 'creature.Id error', id
        return None

def find_player_bp():
    """Returns container with player's backpack/bag
    """
    for i in inven.GetContainers():
        if (i.Id == inven.GetItemInSlot(3).Id) and (i.HasParent == False):
            return i

    print 'Container not found'
    return None

def cont_to_itemloc(container):
    """Converts a container object to an ItemLocation. Makes the ItemLocation
    the last square in the container
    """
    iloc = Tibia.Objects.ItemLocation()
    iloc.FromContainer(
        System.Byte(container.Number),
        System.Byte(container.Volume - 1)
        )

    return iloc

def find_corpse_cont():

    for i in inven.GetContainers():
        if (not i.HasParent) and (i.Id != inven.GetItemInSlot(3).Id):
            return i
        elif (i.HasParent == True) and (i.Id in tid.loot_subcont):
            # May cause a problem if moon bp or bag open
            return i

    # print 'corpse_cont not found'
    return None

def find_target():

    for i in get_bl_creats():
        if i.Id == player.TargetId:
            return i

    return None

def get_statuses(num):
    ps = []

    total = 16
    enums = [2**i for i in range(total)]
    flags = ['None', 'Poisoned', 'Burning', 'Electrified', 'Drunk',
            'ProtectedByManaShield', 'Paralysed', 'Hasted', 'InBattle',
            'Drowning', 'Freezing', 'Dazzled', 'Cursed', 'Buffed',
            'CannotLogoutOrEnterProtectionZone', 'WithinProtectionZone',
            'Bleeding']
    enums.reverse()
    flags.reverse()

    if num == 0:
        return ps

    for i in range(total):
        if num >= enums[i]:
            num -= enums[i]
            ps.append(flags[i])

    return ps


"""Functions to make various packets
"""
def mk_itemuseon(flxyz, fsid, fsp, tlxyz, tsid, tsp):
    pkt = Tibia.Packets.Outgoing.ItemUseOnPacket(client)

    pkt.FromLocation = Tibia.Objects.Location(*flxyz)
    pkt.FromSpriteId = int(fsid)
    pkt.FromStackPosition = int(fsp)
    pkt.ToLocation = Tibia.Objects.Location(*tlxyz)
    pkt.ToSpriteId = int(tsid)
    pkt.ToStackPosition = int(tsp)

    return pkt

def mk_itemusebattlelist(flxyz, sid, fsp, cid):
    pkt = Tibia.Packets.Outgoing.ItemUseBattlelistPacket(client)

    pkt.FromLocation = Tibia.Objects.Location(*flxyz)
    pkt.SpriteId = int(sid)
    pkt.FromStackPosition = int(fsp)
    pkt.CreatureId = int(cid)

    return pkt

def mk_itemuse(flxyz, sid, fsp, idx):
    pkt = Tibia.Packets.Outgoing.ItemUsePacket(client)

    pkt.FromLocation = Tibia.Objects.Location(*flxyz)
    pkt.SpriteId = int(sid)
    pkt.FromStackPosition = int(fsp)
    pkt.Index = int(idx)

    return pkt

def mk_itemmove(flxyz, sid, fsp, tlxyz, count):
    pkt = Tibia.Packets.Outgoing.ItemMovePacket(client)

    pkt.FromLocation = Tibia.Objects.Location(*flxyz)
    pkt.SpriteId = int(sid)
    pkt.FromStackPosition = int(fsp)
    pkt.ToLocation =  Tibia.Objects.Location(*tlxyz)
    pkt.Count = int(count)

    return pkt

def mk_hotkey_pkt(item_id, targ, toloc = None, tosid = 0, tosp = None):
    # targ = 'yourself' 'target' 'crosshairs'
    args = []
    # Tibia.Objects.ItemLocation.FromHotkey().ToLocation()
    args.append((65535, 0, 0)) # FromLoc
    args.append(int(item_id)) # From Sprite Id
    args.append(0) # FromStackPosition, Always zero for hotkey?

    if targ == 'yourself':
        args.append(player.Id) # CreatureId
        pkt = mk_itemusebattlelist(*args)
    elif targ == 'target':
        args.append(player.TargetId)
        pkt = mk_itemusebattlelist(*args) # CreatureId
    elif targ == 'crosshairs':
        args.append(toloc) # ToLocation
        args.append(tosid) # ToSpriteId
        args.append(tosp) # ToStackPosition
        pkt = mk_itemuseon(*args)

    # print args
    return pkt

"""Priority Queue Section
"""
class PQueue(object):
    # Priority Queue, items enter from left, leave from right

    def __init__(self, levels):
        self.items = {}
        for i in range(levels):
            self.items[i] = []

    def __iter__(self):

        for i in range(len(self.items)):
            for j in self.items[i]:
                yield j

    def __contains__(self, key):
        # not sure how to do this yet.
        found = False
        for i in range(len(self.items)):
            if key in self.items[i]:
                found = True
                break

        return found

    def enq(self, lvl, obj):
        if obj in self.items[lvl]:
            pass
        else:
            self.items[lvl].insert(0, obj)

    def deq(self):
        print 'dequeue function in PQueue object not implemented'

    def isempty(self):

        for i in range(len(self.items)):
            if self.items[i] != []:
                return False

        return True

    # def findfirst(self):
    #     for i in range(len(self.items)):
    #         if self.items[i] = []:
    #             next
    #         else:
    #             return self.items[i][0]

    def popnext(self):
        for i in range(len(self.items)):
            if self.items[i] == []:
                next
            else:
                return self.items[i].pop()

        return None # Is Empty

class PQItem(PQueue):
    """ItemUseOn, ItemUseBattleList, ItemUse, ItemMove
    0: Life: MP/HP/E-Ring (Emergency?) Attacking runes
    1: Looter: Looting (Move Item, use item)
    2: Looter: Walk to corpse, use corpse.
    3: Cavebot waypoints: (Use, say?, Goto.)

    Will be a queue of lists in the format ['packettype', [args]]
    """

    def __init__(self):
        levels = 4
        super(PQItem, self).__init__(levels)
        self.tryct = [0]*levels
        self.maxct = [None, None, 20, 20]

        # self.tryct1 = [0]*levels # Packet Send Try Count

    # def enq(self, obj, lvl):
        # if obj in self:
        # alternate them
        # else:
        # self.items[lvl].insert(obj, 0)
        # pass

    def deq(self):

        # flvl = None # From Level
        for i in range(0, len(self.items)):
            if self.items[i] != []:
                flvl = i
                break

        print self.items
        nxt = self.popnext()
        if nxt != None:

            args = nxt[1]
            if nxt[0] == 'useon':
                fxn = mk_itemuseon
            elif nxt[0] == 'usebl':
                fxn = mk_itemusebattlelist
            elif nxt[0] == 'use':
                fxn = mk_itemuse
            elif nxt[0] == 'move':
                fxn = mk_itemmove
            elif nxt[0] == 'hotkey': # ItemUseBattleList/On
                fxn = mk_hotkey_pkt

            # print fxn, args
            pkt = fxn(*args)

            # Test pkt.Send() for completion.
            if flvl == 0: # 0: Life: MP/HP/E-Ring, atk runes
                # Spam them? Send packets twice?
                pkt.Send()
            elif flvl == 1: # 1: Looter: Looting (Move Item, use item)
                # Should run until completion.
                pkt.Send()
            elif flvl == 2: # 2: Looter: Walk to corpse, use corpse.
                # count containers and check that it has changed
                toloc = Tibia.Objects.Location(*args[0])
                # if (not player.IsWalking) & (not player.TargetId): # and (not player.TargetId)
                if (not player.IsWalking):
                    player.GoTo = toloc
                # else: # Waiting
                    # self.items[flvl].append(nxt)

                # In position: adj or on top
                if (player.DistanceTo(toloc) < 2) and (find_corpse_cont):
                    cn0 = len(list(inven.GetContainers()))
                    pkt.Send() # Should be sent when in position.
                    self.tryct[flvl] += 1
                    if not player.TargetId:
                        sleep(1)
                    else:
                        sleep(0.2)
                    # counter is currently too fast and container updates are
                    # based on ping and packets.
                    cn1 = len(list(inven.GetContainers()))

                    if cn0 < cn1: # This is what we want
                        self.tryct[flvl] = 0 # Reset
                        print 'CORPSE OPENED'
                    elif (cn0 == cn1) and (
                            self.tryct[flvl] >= self.maxct[flvl]):
                        self.tryct[flvl] = 0
                        print 'Failure and tryct RESET'
                    elif (cn0 == cn1) and (
                            self.tryct[flvl] < self.maxct[flvl]): # Failure
                        self.items[flvl].append(nxt)
                        print 'FAILURE ON TRY #: ', self.tryct[flvl]
                    elif cn0 > cn1: # Should never happen
                        print 'ERROR'
                elif player.Z != toloc.Z: # Corpse Remove Condition
                    print 'CORPSE REMOVE CONDTION Z'
                elif (abs(player.X - toloc.X) or abs(
                        player.Y - toloc.Y)) > 110:
                    print 'CORPSE REMOVE CONDITION XY'
                elif player.DistanceTo(toloc) >= 2: # Not There yet
                    if self.tryct[flvl] >= self.maxct[flvl]:
                        self.tryct[flvl] = 0
                        print 'OUTSIDE Failure and tryct RESET'
                    elif self.tryct[flvl] < self.maxct[flvl]: # Failure
                        self.items[flvl].append(nxt)
                        self.tryct[flvl] += 1
                        print 'OUTSIDE Failure ON TRY #', self.tryct[flvl]
                        # Represents a failure for packet?

                # 82 73 7D B0 79 00 00 00 01 00
                # 82 73 7D B0 79 00 74 1C 01 03

            elif flvl == 3: # 3: Cavebot waypoints: (Use, say?, Goto.)
                # Implemented instead in cavebot walker
                pass


class PQSay(PQueue):
    """client.Console.Say
    0: Life: Heal spells/attack spells
    1: Utility, spells?

    Is a queue full of strings.
    """


    def __init__(self):
        levels = 2
        super(PQSay, self).__init__(levels)

    # def enq(self, obj, lvl):
        # if obj in self:
        # alternate them
        # else:
        # self.items[lvl].insert(obj, 0)
        # pass

    def deq(self):
        print self.items
        nxt = self.popnext()
        if nxt != None:
            client.Console.Say(nxt)
            # sleep(0.5)

"""Cavebot section
"""
class Cavebot(object):
    """Currently used to hold top level functions. Maybe, in the future it
    will just
    """
    # Walk enumertions/directions
    # Up = 0, Right = 1, Down = 2, Left = 3
    # UpRight = 5, DownRight = 6, DownLeft = 7, UpLeft = 8

    def __init__(self, filename):
        self.waypts = []
        self.directory = 'cavebot/'
        self.filename = filename

    def walk(self, xyz, direction):
        """Wrapper
        """
        # xyz?
        direction = int(direction)
        player.Walk(direction)
        # Logic? checker?

    def autowalk():
        # Would send the autowalk packet, but not pathfind
        # Overshadowed by GoTo
        pass

    def goto(self, xyz):
        """TO BE IMPLEMENTED
        Max = +/- 110 for X/Y
        Can do stairs with this. Implement stairs based on direction facing.
        Possible error if stairs are not on screen.
        """
        loc = Tibia.Objects.Location(*xyz)
        player.GoTo = loc

    def goto_face(self, xyz):
        """TO BE IMPLEMENTED
        Max = +/- 110 for X/Y
        Can do stairs with this. Implement stairs based on direction facing.
        Possible error if stairs are not on screen.
        """
        loc = Tibia.Objects.Location(*xyz)

        # if player.Direction == 0: # Up
        #     loc.Y -= 1
        # elif player.Direction == 1: # Right
        #     loc.X += 1
        # elif player.Direction == 2: # Down
        #     loc.Y += 1
        # elif player.Direction == 3: # Left
        #     loc.X -= 1

        player.GoTo = loc

    def usetile(self, xyz, groundid, stackpos):
        """
        Considering using tiles as close as possible in order to path find
        """
        pkt = Tibia.Packets.Outgoing.ItemUsePacket(client)

        # xyz = list with world XYZ coordinates of tile
        pkt.FromLocation = Tibia.Objects.Location(*xyz)
        pkt.SpriteId = int(groundid) # can use zero
        pkt.FromStackPosition = int(stackpos)
        # Tile.Objects.StackOrder, should usually be 1 or 0
        pkt.Index = 1
        pkt.Send()

    def hotkey_useon(self, xyz, fromid, toid):
        """
        """
        pkt = Tibia.Packets.Outgoing.ItemUseOnPacket(client)

        pkt.FromLocation = Tibia.Objects.ItemLocation.FromHotkey().ToLocation()
        pkt.FromSpriteId = int(fromid)
        pkt.FromStackPosition = 0 # Always zero for hotkey?
        pkt.ToLocation = Tibia.Objects.Location(*xyz)
        pkt.ToSpriteId = int(toid) # ground id
        pkt.ToStackPosition = 0

        pkt.Send()

    def say(self, xyz, msg):
        """Wrapper
        # Think about having specific channels soon.
        """
        msg = str(msg)
        client.Console.Say(msg)

    def astarpathfinder():
        # Maybe not necessary with the Use Tile function.
        pass

class CavebotWalker(Cavebot):
    """
    """

    def __init__(self, filename):
        super(CavebotWalker, self).__init__(filename)
        self.load_waypts(self.directory + self.filename)
        self.restart()
        # self.attempts #Maybe to be implemented later to test for completion.

    def load_waypts(self, filename):

        with open(filename) as txt:
            waypts = [line.rstrip('\n').split(', ') for line in txt]

        # [[X,Y,Z], 'function', *[args]]
        self.waypts = [[[int(i) for i in line[0:3]], getattr(self, line[3]),
                        line[4:]] for line in waypts]

    def next(self):
        if self.idx < len(self.waypts) - 1:
            self.idx += 1
        else:
            self.idx = 0
        self.curr_waypt = self.waypts[self.idx]
        # check if complete?

    def go(self):
        print self.idx, self.curr_waypt
        xyz = self.curr_waypt[0]
        fxn = self.curr_waypt[1]
        args = self.curr_waypt[2]
        fxn(xyz, *args)

        self.next()

    def restart(self):
        self.moveto_waypt(0)

    def moveto_waypt(self, i):
        self.idx = i
        self.curr_waypt = self.waypts[self.idx]

class CavebotWriter(Cavebot):
    """Uses player XYZ to set certain arguments of functions
    """

    def __init__(self, filename):
        super(CavebotWriter, self).__init__(filename)

        if isfile(self.directory + self.filename):
            self.edit()
        # test = True

    def write_walk(self, direction):
        waypt = [player.X, player.Y, player.Z] # Filler
        waypt.append('walk')
        waypt.append(direction)

        self.waypts.append(waypt)

        # Test
        self.walk(waypt[0:3], direction)

    def write_autowalk(self):
        # Would send the autowalk packet, but not pathfind
        pass

    def write_goto(self):
        waypt = [player.X, player.Y, player.Z]
        waypt.append('goto')

        self.waypts.append(waypt)

        # Test
        self.goto(waypt[0:3])

    def write_goto_face(self):
        waypt = [player.X, player.Y, player.Z]
        waypt.append('goto')

        if player.Direction == 0: # Up
            waypt[1] -= 1
        elif player.Direction == 1: # Right
            waypt[0] += 1
        elif player.Direction == 2: # Down
            waypt[1] += 1
        elif player.Direction == 3: # Left
            waypt[0] -= 1

        self.waypts.append(waypt)

        # Test
        self.goto(waypt[0:3])

    def write_usetile(self):
        waypt = [player.X, player.Y, player.Z]
        waypt.append('usetile')
        waypt.append(find_player_tile().Ground.Id)
        # find_player_tile().Objects[0].StackOrder
        waypt.append(0) # 0 until implementation for grates

        self.waypts.append(waypt)

        # Test
        self.usetile(waypt[0:3], waypt[4], waypt[5])

    def write_hotkey_useon(self, fromid):
        """
        """
        waypt = [player.X, player.Y, player.Z]
        waypt.append('hotkey_useon')
        # waypt.append(tid.tool_list[fromid])
        waypt.append(fromid)
        waypt.append(find_player_tile().Ground.Id)
        # waypt.append(0) # 0 until implementation for grates

        self.waypts.append(waypt)

        # Test
        self.hotkey_useon(waypt[0:3], waypt[4], waypt[5])

    def write_say(self, msg):
        waypt = [player.X, player.Y, player.Z]
        waypt.append('say')
        waypt.append(msg)

        self.waypts.append(waypt)

        # Test
        self.say(waypt[0:3], waypt[4])

    def write_astarpathfinder():
        # Maybe not necessary with the Use Tile function.
        pass

    def test(self):
        # testing/performing each waypoint after?
        pass

    def save(self):
        # Will overwrite any existing files
        txt = open(self.directory + self.filename, 'w')

        for pt in self.waypts:
            line = ''
            # delimiter = ', '
            for i in pt:
                line += str(i) + ', '
            line = line.rstrip(', ')
            txt.write(line + '\n') # careful about new line at the end?

        txt.close()
        print 'Waypoints saved to:', self.directory + self.filename

    def del_last(self):
        del self.waypts[-1]

    def edit(self):
        # currently, waypts read as  list of string
        with open(self.directory + self.filename) as txt:
            for line in txt:
                waypt = line.rstrip('\n').split(', ')
                self.waypts.append(waypt)

    def close():
        # might not be necessary yet.
        pass

"""Code Section for QT GUI
"""
def debug_trace():
    """Set a tracepoint in the Python debugger that works with Qt
    http://stackoverflow.com/questions/1736015/debugging-a-pyqt4-app
    """
    QtCore.pyqtRemoveInputHook()
    set_trace()
    QtCore.pyqtRestoreInputHook()

class CustomSignals(QtCore.QObject):
    """http://pyqt.sourceforge.net/Docs/PyQt4/new_style_signals_slots.html
    Should consider implementation of new style slots in the future
    """
    pass
    # Define a new signal called 'trigger' that has no arguments.
    # mlt_signal = QtCore.pyqtSignal()
    # # This defines a signal called 'rangeChanged' that takes two
    # # integer arguments.
    # range_changed = pyqtSignal(int, int, name='rangeChanged')
    #
    # # This defines a signal called 'valueChanged' that has two overloads,
    # # one that takes an integer argument and one that takes a QString
    # # argument.  Note that because we use a string to specify the type of
    # # the QString argument then this code will run under Python v2 and v3.
    # valueChanged = pyqtSignal([int], ['QString'])

class MainLoopThread(QtCore.QThread):

    def __init__(self):
        super(MainLoopThread, self).__init__()
        # self._runflag_ = True

    # def __del__(self):
        # self.wait()

    def run(self):

        while self._runflag_:
            self.emit(QtCore.SIGNAL('update()'))
            # print 'run in mainloopthread'
            sleep(0.15)

class CavebotWriterDialog(QtGui.QDialog):

    walk_args = {'Up': 0, 'Right': 1, 'Down': 2, 'Left': 3,
                'UpRight': 5, 'DownRight': 6, 'DownLeft': 7, 'UpLeft': 8
                }

    say_args = {'exani tera': 'exani tera'
                } # magic rope

    # None or dictionary
    cmds_to_args = {'walk': walk_args,
                'autowalk': None,
                'usetile': None,
                'hotkey_useon': tid.tool_list,
                'say': say_args,
                'astarpathfinder': None,
                'goto' : None,
                'goto_face' : None
                }

    custom_argstr = 'Custom...'
    # Commands that will have custom arguments
    custom_args = ['say', 'hotkey_useon']

    def __init__(self):
        super(CavebotWriterDialog, self).__init__()
        self.wrtr = None
        self.initUI()

    def initUI(self):
        # New Toggle PB, Edit Pushbutton, Filename QLineEdit
        self.pb_new = QtGui.QPushButton('New')
        self.pb_new.setCheckable(True)
        self.pb_new.clicked[bool].connect(self.new_tpb)

        pb_edit = QtGui.QPushButton('Edit')
        pb_edit.clicked.connect(self.cavebot_edit)
        self.wrtr_le = QtGui.QLineEdit(self)
        self.wrtr_le.setReadOnly(True)
        lbl_txt = QtGui.QLabel('.txt')

        # Waypts list widget
        self.waypts_lw = QtGui.QListWidget(self)

        # Command combo box
        self.cmd_combox = QtGui.QComboBox(self)
        self.cmd_combox.addItem('Select command...')
        cmdslist = self.cmds_to_args.keys()
        cmdslist.sort()
        for cmd in cmdslist:
            self.cmd_combox.addItem(cmd)
        self.cmd_combox.activated.connect(self.cmd_actvtd)
        # self.cmd_combox.currentIndexChanged[
            # QtCore.QString].connect(self.cmd_select)

        # Argument combo box, custom argument LineEdit
        self.arg_combox = QtGui.QComboBox(self)
        self.arg_combox.currentIndexChanged.connect(self.arg_actvtd)
        self.arg_le = QtGui.QLineEdit(self)
        self.arg_le.setReadOnly(True)

        # Writer Pushbuttons
        pb_set = QtGui.QPushButton('Set Waypt')
        pb_set.clicked.connect(self.writer_setwp)
        pb_dellast = QtGui.QPushButton('Delete Last')
        pb_dellast.clicked.connect(self.writer_dellast)
        pb_save = QtGui.QPushButton('Save')
        pb_save.clicked.connect(self.writer_save)
        pb_cancel = QtGui.QPushButton('Cancel')
        pb_cancel.clicked.connect(self.close)

        vbox_wrt_dia = QtGui.QVBoxLayout()

        hbox_newedit = QtGui.QHBoxLayout()
        hbox_newedit.addWidget(self.pb_new)
        hbox_newedit.addWidget(pb_edit)
        hbox_file = QtGui.QHBoxLayout()
        hbox_file.addWidget(self.wrtr_le)
        hbox_file.addWidget(lbl_txt)
        hbox_file.addStretch(1)
        vbox_wrt_dia.addLayout(hbox_newedit)
        vbox_wrt_dia.addLayout(hbox_file)
        vbox_wrt_dia.addWidget(self.waypts_lw)
        vbox_wrt_dia.addWidget(self.cmd_combox)
        vbox_wrt_dia.addWidget(self.arg_combox)
        vbox_wrt_dia.addWidget(self.arg_le)

        grid_pb = QtGui.QGridLayout()
        grid_pb.setSpacing(10)
        grid_pb.addWidget(pb_set, 0, 0)
        grid_pb.addWidget(pb_dellast, 0, 1)
        grid_pb.addWidget(pb_save, 1, 0)
        grid_pb.addWidget(pb_cancel, 1, 1)
        vbox_wrt_dia.addLayout(grid_pb)

        self.setWindowTitle('Cavebot Writer')
        self.setLayout(vbox_wrt_dia)

    def new_tpb(self, pressed):
        """The 'New' Toggle Pushbutton
        """

        if pressed:
            self.wrtr_le.clear()
            self.wlkr = None
            self.wrtr_le.setReadOnly(False)
            self.pb_new.setText('Set Name')
        else:
            self.update_wrtr()
            self.pb_new.setText('New')

        self.update_waypts()

    def update_waypts(self):
        """Updates the self.wlkr object and also the waypts in QListWidget
        """
        self.waypts_lw.clear()
        if self.wrtr != None:
            # self.waypts_lw.clear()
            for waypt in self.wrtr.waypts:
                # print 'waypt', waypt
                # self.waypts_lw.addItem(waypt)
                # edit this to fix..
                self.waypts_lw.addItem(str(waypt))

        # if empty do nothing?

    def update_wrtr(self):
        self.wrtr_le.setReadOnly(True)
        fname = self.wrtr_le.text() + '.txt'
        self.wrtr = CavebotWriter(fname)
        print 'File:', self.wrtr.filename

    def cavebot_edit(self):

        fname = QtGui.QFileDialog.getOpenFileName(
                self, 'Edit Cavebot Waypoints...', 'cavebot/'
                )
        # print 'Editing:', fname

        fname = fname.split('/')[-1].split('.')[0]
        self.wrtr_le.setText(fname)

        self.update_wrtr()
        self.update_waypts()

    def cmd_actvtd(self):
        """Downwards nested functions upon cmd_combox being activated
        """
        self.update_argcombox()

    def update_argcombox(self):
        cmd_txt = str(self.cmd_combox.currentText())

        self.arg_combox.clear()

        self.arg_combox.addItem('Select argument...')
        if cmd_txt == 'Select command...':
            pass # Empty
        elif cmd_txt in self.cmds_to_args:
            if self.cmds_to_args[cmd_txt] != None:
                argslist = self.cmds_to_args[cmd_txt].keys()
                argslist.sort()
                for arg in argslist:
                    self.arg_combox.addItem(arg)
                if cmd_txt in self.custom_args:
                    self.arg_combox.addItem(self.custom_argstr)
            else: # CMD without arguments
                pass
        else:
            pass

        self.update_argle()

    def update_argle(self):
        self.arg_le.clear()

        if str(self.arg_combox.currentText()) == self.custom_argstr:
            self.arg_le.setReadOnly(False)
        else:
            self.arg_le.setReadOnly(True)

    def arg_actvtd(self):

        self.update_argle()

    def writer_setwp(self):
        """Sets waypoint by appending to self.wrtr.waypts object
        """
        arg_txt = str(self.arg_combox.currentText())
        argle_txt = str(self.arg_le.text())
        cmd_txt = str(self.cmd_combox.currentText())

        fxn = getattr(self.wrtr, 'write_' + cmd_txt)
        args = [] # All functions take at most one arg right now

        if arg_txt == self.custom_argstr: # Custom arg
            args.append(argle_txt)
        elif arg_txt == 'Select argument...': # No args
            pass
        else: # Arg is in combobox
            argdict = self.cmds_to_args[cmd_txt]
            args.append(argdict[arg_txt])

        fxn(*args)
        # print 'cmd_txt, arg_txt, argle_txt', cmd_txt, arg_txt, argle_txt,
        # print 'fxn, args', fxn, args
        # write out here
        self.update_waypts()

    def writer_dellast(self):
        self.wrtr.del_last()
        self.update_waypts()

    def writer_save(self):
        self.wrtr.save()

class PrubotWidget(QtGui.QWidget):

    mlt = MainLoopThread()
    pqi = PQItem()
    pqs = PQSay()

    def __init__(self):

        super(PrubotWidget, self).__init__()
        self.wlkr = None
        self.initUI()

    def initUI(self):

        # Main loop checkbox
        self.cb_main = QtGui.QCheckBox('Main Loop', self)
        self.cb_main.stateChanged.connect(self.maincb_changed)
        self.connect(self.mlt, QtCore.SIGNAL('update()'), self.main_loop)

        self.bot_status = None

        # All section labels
        secfont = QtGui.QFont() # Section font
        secfont.setBold(True)
        lbl_info = QtGui.QLabel('Info')
        lbl_info.setFont(secfont)
        lbl_atk = QtGui.QLabel('Attack')
        lbl_atk.setFont(secfont)
        lbl_def = QtGui.QLabel('Defense')
        lbl_def.setFont(secfont)
        lbl_supp = QtGui.QLabel('Support')
        lbl_supp.setFont(secfont)
        lbl_loot = QtGui.QLabel('Auto-looter')
        lbl_loot.setFont(secfont)
        lbl_cbot = QtGui.QLabel('Cavebot')
        lbl_cbot.setFont(secfont)
        lbl_settings = QtGui.QLabel('Settings')
        lbl_settings.setFont(secfont)
        lbl_tools = QtGui.QLabel('Tools')
        lbl_tools.setFont(secfont)
        lbl_script = QtGui.QLabel('Scripts')
        lbl_script.setFont(secfont)

        # All Pushbuttons as placeholders

        # Attack section
        self.atk_cb = QtGui.QCheckBox('Attack On', self)

        self.atk_type = QtGui.QComboBox(self)
        self.atk_type.addItem('None')
        self.atk_type.addItem('Spell')
        self.atk_type.addItem('Rune')
        # self.atk_type.currentIndexChanged.connect(self.atk_type_actvtd)
        self.atk_type.currentIndexChanged.connect(lambda: self.sel_type(0))
        self.atk_id = QtGui.QComboBox(self)
        self.atk_id.currentIndexChanged.connect(lambda: self.sel_id(0))
        self.atk_id_le = QtGui.QLineEdit(self)
        self.atk_id_le.setReadOnly(True)
        self.atk_atcb0 = QtGui.QCheckBox('Auto Target On', self)
        atk_atgb = QtGui.QGroupBox('Auto Target Logic', self)
        atk_atgb.setStyleSheet('QGroupBox {border:1px solid}')
        atk_atgb.setStyleSheet('QGroupBox::title {top: -2px;}')
        self.atk_atcb1 = QtGui.QCheckBox('Closest', self)
        self.atk_atcb1.stateChanged.connect(self.atcb_changed)
        self.atk_atcb2 = QtGui.QCheckBox('Lowest HP', self)
        self.atk_atcb2.stateChanged.connect(self.atcb_changed)
        self.atk_chasecb = QtGui.QCheckBox('Chase Target', self)
        self.target_priority = []
        vbox_atcb = QtGui.QVBoxLayout()
        vbox_atcb.addWidget(self.atk_atcb1)
        vbox_atcb.addWidget(self.atk_atcb2)
        vbox_atcb.addWidget(self.atk_chasecb)
        # add stretch?
        atk_atgb.setLayout(vbox_atcb)

        # Atk AOE Section
        self.atk_aoecb = QtGui.QCheckBox('AOE On', self)
        self.atk_aoetype = QtGui.QComboBox(self)
        self.atk_aoetype.addItems(['None', 'Spell', 'Rune'])
        # self.atk_aoetype.currentIndexChanged.connect(lambdaself.atk_aoetype_actvtd)
        self.atk_aoetype.currentIndexChanged.connect(lambda: self.sel_type(1))
        self.atk_aoeid = QtGui.QComboBox(self)
        # self.atk_aoeid.currentIndexChanged.connect(self.atk_aoeid_actvtd)
        self.atk_aoeid.currentIndexChanged.connect(lambda: self.sel_id(1))
        self.atk_aoeid_le = QtGui.QLineEdit(self)
        self.atk_aoeid_le.setReadOnly(True)
        grid_sb = QtGui.QGridLayout()
        # grid0.setSpacing(10)
        atk_aoesb1_lbl = QtGui.QLabel('# of monsters:')
        self.atk_aoesb1 = QtGui.QSpinBox(self)
        atk_aoesb2_lbl = QtGui.QLabel('Range (X/Y):')
        self.atk_aoesb2 = QtGui.QSpinBox(self)
        self.atk_aoesb2.setMinimum(1)
        self.atk_aoesb2.setMaximum(9)
        atk_aoesb3_lbl = QtGui.QLabel('Floors (Z):')
        self.atk_aoesb3 = QtGui.QSpinBox(self)
        self.atk_aoesb3.setMaximum(2)
        grid_sb.addWidget(atk_aoesb1_lbl, 0, 0)
        grid_sb.addWidget(self.atk_aoesb1, 0, 1)
        grid_sb.addWidget(atk_aoesb2_lbl, 1, 0)
        grid_sb.addWidget(self.atk_aoesb2, 1, 1)
        grid_sb.addWidget(atk_aoesb3_lbl, 2, 0)
        grid_sb.addWidget(self.atk_aoesb3, 2, 1)

        # Defense Section
        # def_hp = QtGui.QLabel('Health')
        self.def_hpcb = QtGui.QCheckBox('HP On')
        self.def_hpsb1 = QtGui.QSpinBox(self)
        self.def_hpsb1.setMaximum(9999)
        self.def_hpsb1.setSingleStep(10)
        def_hpsb1_lbl = QtGui.QLabel('/' + str(player.HealthMax))
        self.def_hptype1 = QtGui.QComboBox(self)
        self.def_hptype1.addItems(['None', 'Spell', 'Rune', 'Pot'])
        self.def_hptype1.currentIndexChanged.connect(lambda: self.sel_type(2))
        self.def_hpid1 = QtGui.QComboBox(self)
        self.def_hpid1.currentIndexChanged.connect(lambda: self.sel_id(2))

        self.def_hpsb2 = QtGui.QSpinBox(self)
        self.def_hpsb2.setMaximum(9999)
        self.def_hpsb2.setSingleStep(10)
        self.def_hptype2 = QtGui.QComboBox(self)
        self.def_hptype2.addItems(['None', 'Spell', 'Rune', 'Pot'])
        self.def_hptype2.currentIndexChanged.connect(lambda: self.sel_type(3))
        self.def_hpid2 = QtGui.QComboBox(self)
        self.def_hpid2.currentIndexChanged.connect(lambda: self.sel_id(3))

        # def_mp = QtGui.QLabel('Mana')
        self.def_mpcb = QtGui.QCheckBox('MP On')
        self.def_mpsb1 = QtGui.QSpinBox(self)
        self.def_mpsb1.setMaximum(99999)
        self.def_mpsb1.setSingleStep(10)
        def_mpsb1_lbl = QtGui.QLabel('/' + str(player.ManaMax))
        self.def_mptype1 = QtGui.QComboBox(self)
        self.def_mptype1.addItems(['None', 'Spell', 'Rune', 'Pot'])
        self.def_mptype1.currentIndexChanged.connect(lambda: self.sel_type(4))
        self.def_mpid1 = QtGui.QComboBox(self)
        self.def_mpid1.currentIndexChanged.connect(lambda: self.sel_id(4))

        grid_def = QtGui.QGridLayout()
        # grid_def.addWidget(def_hp, 0, 0)
        grid_def.addWidget(self.def_hpcb, 0, 0)
        grid_def.addWidget(self.def_hpsb1, 1, 0)
        grid_def.addWidget(def_hpsb1_lbl, 1, 1)
        grid_def.addWidget(self.def_hptype1, 2, 0, 1, 2)
        grid_def.addWidget(self.def_hpid1, 3, 0, 1, 2)
        grid_def.addWidget(self.def_hpsb2, 4, 0)
        grid_def.addWidget(self.def_hptype2, 5, 0, 1, 2)
        grid_def.addWidget(self.def_hpid2, 6, 0, 1, 2)
        # grid_def.addWidget(def_mp, 0, 2)
        grid_def.addWidget(self.def_mpcb, 0, 2)
        grid_def.addWidget(self.def_mpsb1, 1, 2)
        grid_def.addWidget(def_mpsb1_lbl, 1, 3)
        grid_def.addWidget(self.def_mptype1, 2, 2, 1, 2)
        grid_def.addWidget(self.def_mpid1, 3, 2, 1, 2)
        grid_def.setRowStretch(7, 1)
        # grid_def.setColumnStretch(7,1)

        def_ut = QtGui.QLabel('Utility')
        self.def_ut_haste = QtGui.QComboBox(self)
        self.def_ut_hastecb = QtGui.QCheckBox()
        self.hastetime = 0
        self.def_ut_haste.addItems(['Haste...', 'utani hur', 'utani gran hur',
            'utani tempo hur', 'utamo tempo san'])
        self.def_ut_invis = QtGui.QCheckBox('Invisible', self)
        self.invistime = 0
        self.def_ut_custcb = QtGui.QCheckBox('Custom On', self)
        self.custtime = 0
        self.def_ut_custsb = QtGui.QSpinBox(self)
        self.def_ut_custsb.setMaximum(999)
        self.def_ut_custsb.setSingleStep(5)
        self.def_ut_custle = QtGui.QLineEdit(self)
        grid_def.addWidget(def_ut, 0, 4)
        grid_def.addWidget(self.def_ut_hastecb, 1, 4)
        grid_def.addWidget(self.def_ut_haste, 1, 5)
        grid_def.addWidget(self.def_ut_invis, 2, 4, 1, 2)
        grid_def.addWidget(self.def_ut_custcb, 3, 4, 1, 2)
        grid_def.addWidget(self.def_ut_custsb, 4, 4)
        grid_def.addWidget(self.def_ut_custle, 4, 5)
        grid_def.setColumnStretch(6, 1)

        # Support Section
        # supp_pots = QtGui.QPushButton('Pots')
        supp_mi = QtGui.QPushButton('Move Item')

        # Looter Section
        self.loot_findcb = QtGui.QCheckBox('Find Corpse On')
        self.loot_lootcb = QtGui.QCheckBox('Looter On')
        self.loot_reset = QtGui.QPushButton('Reset Looter Count')
        self.loot_reset.clicked.connect(self.reset_loot_logic1)
        self.reset_loot_logic1()
        self.loot_cont = None
        self.loot_creats = []
        self.loot_corpse_q = []

        tools_floorspy = QtGui.QPushButton('Floorspy')
        tools_namespy = QtGui.QPushButton('Namespy')
        tools_mwtimer = QtGui.QPushButton('Magic Wall Timer')
        tools_wgtimer = QtGui.QPushButton('Wild Growth Timer')
        script_test = QtGui.QPushButton('Script Test')
        #client.map; level spy, light spy, replace trees

        # All sections being created...
        # Info
        hbox_info = QtGui.QHBoxLayout()
        vbox_info = QtGui.QVBoxLayout()
        self.lbl_plyr = QtGui.QLabel('')
        self.lbl_wxyz = QtGui.QLabel('')
        self.lbl_mxyz = QtGui.QLabel('')
        self.update_plyrinfo()
        vbox_info.addWidget(self.lbl_plyr)
        vbox_info.addWidget(self.lbl_wxyz)
        vbox_info.addWidget(self.lbl_mxyz)
        hbox_info.addLayout(vbox_info)

        # Attack
        hbox_atk = QtGui.QHBoxLayout()
        vbox_atk0 = QtGui.QVBoxLayout()
        vbox_atk1 = QtGui.QVBoxLayout()
        vbox_atk0.addWidget(self.atk_cb)
        vbox_atk0.addWidget(self.atk_type)
        vbox_atk0.addWidget(self.atk_id)
        vbox_atk0.addWidget(self.atk_id_le)
        vbox_atk0.addWidget(self.atk_atcb0)
        vbox_atk0.addWidget(atk_atgb)
        vbox_atk0.addStretch(1)
        hbox_atk.addLayout(vbox_atk0)
        vbox_atk1.addWidget(self.atk_aoecb)
        vbox_atk1.addWidget(self.atk_aoetype)
        vbox_atk1.addWidget(self.atk_aoeid)
        vbox_atk1.addWidget(self.atk_aoeid_le)
        vbox_atk1.addLayout(grid_sb)
        vbox_atk1.addStretch(1)
        # vbox_atk1.addWidget()
        hbox_atk.addLayout(vbox_atk1)

        # Auto-looter
        vbox_loot = QtGui.QVBoxLayout()
        vbox_loot.addWidget(self.loot_findcb)
        vbox_loot.addWidget(self.loot_lootcb)
        vbox_loot.addWidget(self.loot_reset)
        vbox_loot.addStretch(1)

        # Support
        vbox_supp = QtGui.QVBoxLayout()
        vbox_supp.addWidget(supp_mi)
        # vbox_supp.addWidget(supp_invis)
        vbox_supp.addStretch(1)

        # Cavebot: Walker/Writer
        hbox_cbot = QtGui.QHBoxLayout()
        vbox_wlkr = QtGui.QVBoxLayout()
        vbox_wrtr = QtGui.QVBoxLayout()
        cbot_load = QtGui.QPushButton('Load', self)
        lbl_wlkr = QtGui.QLabel('Walker')
        self.lbl_cbot_file = QtGui.QLabel('Waypoints: \n N/A')
        cbot_load.clicked.connect(self.cavebot_load)
        self.cb_cbot_wlkr = QtGui.QCheckBox('Walker On', self)
        self.lbl_cbot_currwaypt = QtGui.QLabel('Current Waypoint: \n N/A')
        cbot_restart = QtGui.QPushButton('Restart', self)
        cbot_restart.clicked.connect(self.cavebot_restart)
        lbl_wrtr = QtGui.QLabel('Writer')
        # cbotEdit = QtGui.QLineEdit()
        cbot_wrt = QtGui.QPushButton('Write')
        cbot_wrt.clicked.connect(self.cavebot_wrt_dia)
        # cbot_edit = QtGui.QPushButton('Edit')
        # cbot_edit.clicked.connect(self.cavebot_edit)
        vbox_wlkr.addWidget(lbl_wlkr)
        vbox_wlkr.addWidget(cbot_load)
        vbox_wlkr.addWidget(self.lbl_cbot_file)
        vbox_wlkr.addWidget(self.cb_cbot_wlkr)
        vbox_wlkr.addWidget(self.lbl_cbot_currwaypt)
        vbox_wlkr.addWidget(cbot_restart)
        vbox_wlkr.addStretch(1)
        vbox_wrtr.addWidget(lbl_wrtr)
        vbox_wrtr.addWidget(cbot_wrt)
        # vbox_wrtr.addWidget(cbot_edit)
        vbox_wrtr.addStretch(1)
        hbox_cbot.addLayout(vbox_wlkr)
        hbox_cbot.addLayout(vbox_wrtr)

        # Tools
        vbox_tools = QtGui.QVBoxLayout()
        vbox_tools.addWidget(tools_floorspy)
        vbox_tools.addWidget(tools_namespy)
        vbox_tools.addWidget(tools_mwtimer)
        vbox_tools.addWidget(tools_wgtimer)
        vbox_tools.addStretch(1)

        # Scripts?
        vbox_script = QtGui.QVBoxLayout()
        vbox_script.addWidget(script_test)
        vbox_script.addStretch(1)

        # Settings
        vbox_settings = QtGui.QVBoxLayout()
        settings_save = QtGui.QPushButton('Save Profile')
        settings_save.clicked.connect(self.prof_save)
        settings_load = QtGui.QPushButton('Load Profile')
        settings_load.clicked.connect(self.prof_load)
        vbox_settings.addWidget(settings_save)
        vbox_settings.addWidget(settings_load)
        vbox_settings.addStretch(1)

        grid0 = QtGui.QGridLayout()
        grid0.setSpacing(10)

        grid0.addWidget(lbl_info, 0, 0)
        grid0.addWidget(self.cb_main, 0, 1)
        grid0.addLayout(hbox_info, 1, 0, 1, 3)
        grid0.addWidget(lbl_atk, 2, 0)
        grid0.addLayout(hbox_atk, 3, 0, 1, 2)
        grid0.addWidget(lbl_def, 2, 2)
        # grid0.addLayout(hbox_def, 3, 1, 3, 2, QtCore.Qt.AlignTop)
        grid0.addLayout(grid_def, 3, 2, 1, 3)
        grid0.addWidget(lbl_loot, 4, 0)
        grid0.addLayout(vbox_loot, 5, 0)
        grid0.addWidget(lbl_supp, 4, 1)
        grid0.addLayout(vbox_supp, 5, 1)
        grid0.addWidget(lbl_cbot, 4, 2)
        grid0.addLayout(hbox_cbot, 5, 2, 2, 2)
        grid0.addWidget(lbl_settings, 4, 4)
        grid0.addLayout(vbox_settings, 5, 4)
        grid0.addWidget(lbl_tools, 6, 0)
        grid0.addLayout(vbox_tools, 7, 0, 1, 1)
        grid0.addWidget(lbl_script, 6, 1)
        grid0.addLayout(vbox_script, 7, 1, 1, 1)
        grid0.setColumnStretch(5,1)
        grid0.setRowStretch(10,1)

        self.setLayout(grid0)

    def update_plyrinfo(self):
        """
        """
        plyr = player.Name
        world_xyz = '%-10s X: %-7d Y: %-7d Z: %s' % (
                        'World:', player.X, player.Y, player.Z
                        )

        # client.HasExited?
        # if client.LoggedIn:
        plyr_tile = find_player_tile()

        if plyr_tile:
            mem_xyz = '%-10s X: %-7d Y: %-7d Z: %s' % (
                            'Memory:',
                            plyr_tile.MemoryLocation.X,
                            plyr_tile.MemoryLocation.Y,
                            plyr_tile.MemoryLocation.Z
                            )

            self.lbl_plyr.setText(plyr)
            self.lbl_wxyz.setText(world_xyz)
            self.lbl_mxyz.setText(mem_xyz)

    def maincb_changed(self):
        # print 'main_loop'

        if self.cb_main.isChecked() == True:
            # print 'main_loop checked is true, mlt start'
            bot_init()
            self.mlt._runflag_ = True
            self.mlt.start()
        elif self.cb_main.isChecked() == False:
            # print 'main_loop checked is false, mlt quit'
            self.mlt._runflag_ = False
            # self.mlt.quit()

    def atkcb_changed(self):
        pass

    def sel_type(self, loc):
        # 'type' combox activated, select type
        self.update_idcombox(loc)

    def update_idcombox(self, loc):

        if loc == 0: # Single Target
            type_txt = str(self.atk_type.currentText())
            idcombox = self.atk_id
        elif loc == 1: # AOE
            type_txt = str(self.atk_aoetype.currentText())
            idcombox = self.atk_aoeid
        elif loc == 2: # HP1
            type_txt = str(self.def_hptype1.currentText())
            idcombox = self.def_hpid1
        elif loc == 3: # HP2
            type_txt = str(self.def_hptype2.currentText())
            idcombox = self.def_hpid2
        elif loc == 4: # MP1
            type_txt = str(self.def_mptype1.currentText())
            idcombox = self.def_mpid1

        idcombox.clear()
        idcombox.addItem('Select...')

        if type_txt == 'None':
            pass
        elif (type_txt == 'Spell') & (loc <= 1):
            idcombox.addItems(tid.atk_spells) # change into dictionary? or keep
            idcombox.addItem('Other...')
        elif (type_txt == 'Spell') & (loc > 1):
            idcombox.addItems(tid.def_spells)
        elif (type_txt == 'Rune') & (loc <= 1):
            items = tid.atk_runes.keys()
            items.sort()
            for i in items:
                idcombox.addItem(i)
            idcombox.addItem('Other...')
        elif (type_txt == 'Rune') & (loc > 1):
            items = tid.def_runes.keys()
            items.sort()
            for i in items:
                idcombox.addItem(i)
        # elif (type_txt == 'Pot') & (loc <= 1): # No attack pots
        #     items = tid.atk_runes.keys()
        #     items.sort()
        #     for i in items:
        #         idcombox.addItem(i)
        #     idcombox.addItem('Other...')
        elif (type_txt == 'Pot') & (loc > 1):
            items = tid.def_pots.keys()
            items.sort()
            for i in items:
                idcombox.addItem(i)
        else:
            print 'INVALID type_txt'

    def sel_id(self, loc):
        self.update_id_le(loc)

    def update_id_le(self, loc):

        if loc == 0: # Single Target
            id_txt = str(self.atk_id.currentText())
            id_le = self.atk_id_le
        elif loc == 1: # AOE
            id_txt = str(self.atk_aoeid.currentText())
            id_le = self.atk_aoeid_le
        elif loc == 2:
            id_txt = None
            id_le = None
        elif loc == 3:
            id_txt = None
            id_le = None
        elif loc == 4:
            id_txt = None
            id_le = None

        if id_le:
            id_le.clear()
            if id_txt == 'Other...':
                id_le.setReadOnly(False)
            else:
                id_le.setReadOnly(True)

    def enq_atkdef(self, loc):

        if loc == 0:
            type_combox = self.atk_type
            id_combox = self.atk_id
            id_le = self.atk_id_le
        elif loc == 1:
            type_combox = self.atk_aoetype
            id_combox = self.atk_aoeid
            id_le = self.atk_aoeid_le
        elif loc == 2:
            type_combox = self.def_hptype1
            id_combox = self.def_hpid1
            id_le = None
        elif loc == 3:
            type_combox = self.def_hptype2
            id_combox = self.def_hpid2
            id_le = None
        elif loc == 4:
            type_combox = self.def_mptype1
            id_combox = self.def_mpid1
            id_le = None

        type_txt = str(type_combox.currentText())
        id_txt = str(id_combox.currentText())
        if id_le:
            id_le_txt = str(id_le.text())
        else:
            id_le_txt = None
        # print 'eqn_atkdef() %s %s %s' % (type_txt, id_txt, id_le_txt)

        if type_txt == 'None':
            pass
        elif id_txt == 'Select...':
            pass
        elif (type_txt == 'Spell') & (loc <= 1):
            if id_txt == 'Other...':
                arg = id_le_txt
            else:
                arg = id_txt
                self.pqs.enq(0, arg)
        elif (type_txt == 'Spell') & (loc > 1):
            if id_txt == 'Other...':
                arg = id_le_txt
            else:
                arg = id_txt
                self.pqs.enq(0, arg)
        elif (type_txt == 'Rune') & (loc <= 1):
            if id_txt == 'Other...':
                runeid = id_le_txt
            else:
                runeid = tid.atk_runes[id_txt]
                obj = ['hotkey', [runeid, 'target']]
                self.pqi.enq(0, obj)
        elif (type_txt == 'Rune') & (loc > 1):
            if id_txt == 'Other...':
                runeid = id_le_txt
            else:
                runeid = tid.def_runes[id_txt]
                obj = ['hotkey', [runeid, 'yourself']]
                self.pqi.enq(0, obj)
        # elif (type_txt == 'Pot') & (loc <= 1): # No attack pots
            # print 'pqi eqn arg'
            # if id_txt == 'Other...':
            #     potid = id_le_txt
            # else:
            #     potid = tid.def_pots[id_txt]
            #     obj = ['hotkey', [potid, 'target']]
            #     print obj
            #     self.pqi.enq(0, obj)
        elif (type_txt == 'Pot') & (loc > 1):
            if id_txt == 'Other...':
                potid = id_le_txt
            else:
                potid = tid.def_pots[id_txt]
                obj = ['hotkey', [potid, 'yourself']]
                self.pqi.enq(0, obj)

    def aoe_logic(self):
        xy_max = self.atk_aoesb2.value()
        z_floors = self.atk_aoesb3.value()

        creat_list = get_bl_creats()
        no_monst = 0
        for c in creat_list:
            pnc = test_pnc(c.Id)
            xyz_diff = (
                abs(c.X - player.X),
                abs(c.Y - player.Y),
                abs(c.Z - player.Z)
                )
            if (pnc == 'creature') and (c.Z == player.Z): # Creat on same floor
                if (xyz_diff[0] <= xy_max) and (xyz_diff[1] <= xy_max):
                    no_monst += 1
            elif (pnc == 'player') and (c.IsSelf() == False):
                if xyz_diff[2] <= z_floors:
                    return False

        # print no_monst, xy_max, z_floors
        return no_monst >= self.atk_aoesb1.value()

    def atk_logic(self):

        if self.atk_aoecb.isChecked() == True: # AOE On
            if self.aoe_logic() == True:
                self.enq_atkdef(1)
            elif self.aoe_logic() == False:
                self.enq_atkdef(0)
        else:
            self.enq_atkdef(0)

    def atcb_changed(self):
        source = self.sender()
        source_txt = source.text()
        if source_txt == 'Closest':
            txt = 'dist'
        elif source_txt == 'Lowest HP':
            txt = 'hp'
            # txt = 'HPBar'

        if source.isChecked():
            self.target_priority.append(txt)
        else:
            self.target_priority.remove(txt)

        print 'self.target_priority: ', self.target_priority

    def atk_chase_logic(self, chase):

        if self.atk_chasecb.isChecked():
            if chase == 0:
                targ = find_target()
                # targ.Approach()
                if player.DistanceTo(targ.Location) > 2:
                    targ.Approach()

            elif chase == 1:
                client.FollowMode = 1
            elif chase == 2: # Use tile where the creature is?
                #
                pass

    def auto_target_logic(self):
        # True/False Conditions, then sorting conditions

        if 'WithinProtectionZone' in get_statuses(player.Flags):
            return
        if player.TargetId:
            return

        creat_list = get_bl_creats()

        conditions = [Tibia.Objects.Creature.IsReachable
            # Tibia.Objects.Creature.IsAttacking
            ]

        # Make the list of attackable creatures
        atk_list = [] # Creatures on floor, and 'conditions' True
        for c in creat_list:
            if all([c.Z == player.Z, not c.IsSelf(),
                    test_pnc(c.Id) == 'creature',
                    c.Name not in tid.creat_excl_list]):
                if all([fxn(c) for fxn in conditions]): # T if all T, F if 1 F
                    atk_list.append(
                        (c, c.DistanceTo(player.Location), c.HPBar)
                        )
            else:
                pass

        # Sort list, attack the best candidate
        # Currently VERY hard coded; need to figure out better way
        if atk_list:
            if self.target_priority == ['dist']:
                atk_list.sort(key=lambda x: [x[1]])
            elif self.target_priority == ['hp']:
                atk_list.sort(key=lambda x: [x[2]])
            elif self.target_priority == ['dist', 'hp']:
                atk_list.sort(key=lambda x: [x[1], x[2]])
            elif self.target_priority == ['hp', 'dist']:
                atk_list.sort(key=lambda x: [x[2], x[1]])
            # target = atk_list[0][0]
            # player.Stop() # see how this turns out
            # target.
            atk_list[0][0].Attack()
        else:
            pass

    def find_corpse(self):
        new_cl = get_bl_creats()

        # Append to list under these conditions
        creat_ids = [i.Id for i in self.loot_creats]
        for c in new_cl:
            add_conds = [c.Id not in creat_ids,
                        test_pnc(c.Id) == 'creature',
                        c.Name not in tid.creat_excl_list,
                        c.Z == player.Z,
                        c.Name not in tid.creat_noloot_list
                        ]
            if all(add_conds):
                self.loot_creats.append(c)
        # print [i.Id for i in self.loot_creats]

        # Remove from list if out of range
        for c in self.loot_creats:
            rem_conds = [c.Z != player.Z,
                        8 < abs(c.X - player.X),
                        10 < abs(c.Y - player.Y)
                        ]
            if any(rem_conds):
                self.loot_creats.remove(c)
        # print [i.Id for i in self.loot_creats]

        for c in self.loot_corpse_q:
            rem_conds = [c.Z != player.Z,
                        8 < abs(c.X - player.X),
                        10 < abs(c.Y - player.Y)
                        ]
            if any(rem_conds):
                self.loot_corpse_q.remove(c)
        # print [i.Id for i in self.loot_creats]

        # Move from self.loot_creats to corpse_q

        lc_copy = self.loot_creats
        for c in lc_copy:
            if c.HPBar == 0:
                # FIFO
                self.loot_corpse_q.insert(0, c)
                self.loot_creats.remove(c)
        # print [i.Id for i in self.loot_creats]

    def loot_enq_corpse(self):

        # FIFO, list should be empty after this loop
        for i in range(0, len(self.loot_corpse_q)):
            # 1 and 2 should work as args, but better implementation possible

            c = self.loot_corpse_q.pop()
            # self.pqi.enq(2, ['use', [[c.X, c.Y, c.Z], 1000, 2, 0]])
            self.pqi.enq(2, ['use', [[c.X, c.Y, c.Z], 1000, 3, 0]])
            # Greater Wyrm?
            # self.pqi.enq(2, ['use', [[c.X, c.Y, c.Z], 8113, 2, 0]])

    def reset_loot_logic1(self):
        self.idx_rare = 0
        self.idx_stk = -1
        self.idx_com = -2
        self.ct_rare = 0
        self.ct_stk = 0
        self.ct_com = 0

        print 'Loot Logic1 Reset'

    def find_loot_cont(self, bpid):
        """Find Loot Container.
        """
        for i in inven.GetContainers():
            count = 0
            for j in list(i.GetItems()):
                if j.Id == bpid:
                    count += 1

                if count > 2: # Arbitrary
                    return i

        # print 'loot_cont not found'
        return None

    def looter_ready(self):
        """Looting Algorithm needs self.loot_cont preset.
        Consider putting dependencies as function arguments

        Returns boolean
        """
        self.loot_cont = self.find_loot_cont(9605)

        if self.loot_cont == None:
            return False
        else: # is Tibia.Objects.Container
            return True

    def get_loot_bps(self, bpid):
        """Assumes self.loot_cont is set.
        bpid = item id of containers to hold loot.
        """

        bp_list = []
        for i in self.loot_cont.GetItems():
            if i.Id == bpid:
                bp_list.append(i)
        return bp_list

    # def find_corpse_cont(self):
    #
    #     for i in inven.GetContainers():
    #         if (not i.HasParent) and (i.Id != inven.GetItemInSlot(3).Id):
    #             return i
    #         elif (i.HasParent == True) and (i.Id in tid.loot_subcont):
    #             # May cause a problem if moon bp or bag open
    #             return i
    #
    #     # print 'corpse_cont not found'
    #     return None

    def loot_enq_move(self, item, toloc):
        """Put a move item command in the pqi object.
        item = Tibia.Objects.Item object
        toloc = Location object to move item.
        """
        itemloc = item.Location.ToLocation()
        self.pqi.enq(1, ['move', [[itemloc.X, itemloc.Y, itemloc.Z],
                                item.Id, itemloc.Z,
                                [toloc.X, toloc.Y, toloc.Z],
                                item.Count
                                ]])

    def loot_logic0(self):
        """Placeholder for future implementation
        """
        pass

    def loot_logic1(self):
        """Looting works by moving items into a variety of crown BP's
        Needs: self.corpse_cont, self.loot_cont, self.loot_bps
        """

        # self.statusflag = 'looting'
        corpse_items = list(self.corpse_cont.GetItems())
        precount = len(corpse_items)

        for i in corpse_items:
            # print 'Scanning Corpse @ Item.Id: ', i.Id
            if i.Id in tid.loot_gold:
                bpmain_item = inven.GetItemInSlot(3)
                # i.Move(bpmain_item.Location, System.Byte(i.Count))
                # sleep(0.3)
                self.loot_enq_move(i, bpmain_item.Location.ToLocation())
                print 'Looting: ', tid.loot_list[i.Id]

                # Can Also try putting into into last slot of container.
                # toloc = list(bpmain.GetItems())[0].Location... change Z to Volume-1
                #  (0, +1, ID, containerid+64, +1)
                return

            elif i.Id in tid.loot_list: # and not in loot_gold
                if i.Id in tid.loot_rares:
                    lootbp = self.loot_bps[self.idx_rare]
                elif i.Id in tid.loot_commons:
                    lootbp = self.loot_bps[self.idx_com]
                elif i.Id in tid.loot_stack:
                    lootbp = self.loot_bps[self.idx_stk]
                elif i.Id in tid.loot_test: # Test
                    lootbp = self.loot_bps[self.idx_rare]

                # i.Move(lootbp.Location, System.Byte(i.Count)) # IMPLEMENT PACKET!
                # sleep(0.3)
                self.loot_enq_move(i, lootbp.Location.ToLocation())
                print 'Looting: ', tid.loot_list[i.Id]

                # Check for completion:
                postcount = len(list(self.corpse_cont.GetItems()))
                if postcount == precount: # Item did not move
                        pass
                elif postcount < precount:
                    if i.Id in tid.loot_rares:
                        self.ct_rare += 1
                        if self.ct_rare == 20:
                            self.idx_rare += 1
                            print 'changing bp'
                    elif i.Id in tid.loot_commons:
                        self.ct_com += 1
                        if self.ct_com == 20:
                            self.idx_com -= 1
                    elif i.Id in tid.loot_stack:
                        self.ct_stk += 1
                        if self.ct_stk == 20:
                            self.idx_stk -= 1
                    elif i.Id in tid.loot_test: # Test
                        self.ct_rare += 1
                        if self.ct_rare == 20:
                            self.idx_rare += 1

                return

            elif i == corpse_items[-1]: # At last item, and not in tid.loot_list
                for j in corpse_items:
                    if j.Id in tid.loot_subcont:
                        # PQI Implementation should not be needed here
                        j.OpenAsContainer(System.Byte(self.corpse_cont.Number))
                        return

                # No subcont
                # PQI Implementation should not be needed here
                self.pqi.tryct[2] = 0
                self.corpse_cont.Close()
                # Consider using an 'islooting' flag

        # PQI Implementation should not be needed here
        self.pqi.tryct[2] = 0
        self.corpse_cont.Close() # Should only occur if corpse is empty

    def cavebot_logic(self):

        cb_conds = [self.pqi.isempty(), not player.IsWalking,
                    not player.TargetId
                    ]

        # walk(self, xyz, direction), autowalk(),
        # goto(self, xyz), goto_face(self, xyz),
        # usetile(self, xyz, groundid, stackpos),
        # hotkey_useon(self, xyz, fromid, toid)
        # say(self, xyz, msg), astarpathfinder()
        if all(cb_conds):
            cidx = self.wlkr.idx
            cwp = self.wlkr.curr_waypt

            toloc = Tibia.Objects.Location(*cwp[0])

            self.wlkr.go()

            # Only tests the "Go"
            if player.DistanceTo(toloc) == 0:
                print 'ONTOP OF TILE'
            elif player.DistanceTo(toloc) < 2:
                print 'ADJACENT TO TILE'
            else:
                # Try Again
                self.wlkr.moveto_waypt(cidx)

    def attack(self):
        if self.atk_cb.isChecked() == True:
            if player.TargetId:
                self.atk_logic()
                self.atk_chase_logic(0)
            elif self.atk_atcb0.isChecked():
                # Auto target
                self.auto_target_logic()
            elif not self.atk_atcb0.isChecked(): # No target, no auto targ
                pass
        elif self.atk_cb.isChecked() == False:
            # print 'atk_cb is checked false'
            pass

    def defense(self):
        # Defense Logic

        # HP
        if self.def_hpcb.isChecked():
            if player.Health < self.def_hpsb2.value():
                self.enq_atkdef(3)
            elif player.Health < self.def_hpsb1.value():
                self.enq_atkdef(2)

        # MP
        if self.def_mpcb.isChecked():
            if player.Mana < self.def_mpsb1.value():
                self.enq_atkdef(4)

        # Utility
        currtime = time()
        # Haste
        if self.def_ut_hastecb.isChecked() and \
                (not 'WithinProtectionZone' in get_statuses(player.Flags)):
            hastetxt = str(self.def_ut_haste.currentText())
            if hastetxt != 'Haste...':
                if hastetxt == 'utani hur':
                    hastecd = 31
                elif hastetxt == 'utani gran hur':
                    hastecd = 22
                elif hastetxt == 'utani tempo hur':
                    hastecd = 5 + 1.5
                elif hastetxt == 'utamo tempo san':
                    hastecd = 10

                if currtime - self.hastetime > hastecd - 1.5:
                    self.pqs.enq(1, hastetxt)
                    self.hastetime = time()
            else:
                pass

        # Invis
        if self.def_ut_invis.isChecked():
            invistxt = 'utana vid'
            inviscd = 200

            if currtime - self.invistime > inviscd - 10:
                self.pqs.enq(1, invistxt)
                self.invistime = time()

        # Custom
        if self.def_ut_custcb.isChecked():
            custtxt = str(self.def_ut_custle.text())
            custcd = self.def_ut_custsb.value()

            if currtime - self.custtime > custcd - 0:
                self.pqs.enq(1, custtxt)
                self.custtime = time()

    def looter(self):

        # Finds Corpses, enqs corpse
        if self.loot_findcb.isChecked():
            self.find_corpse()
            self.loot_enq_corpse()

        # Container names: "Dead, remains, slain, lifeless nettle"
        if self.loot_lootcb.isChecked() and self.looter_ready():
            # self.corpse_cont = self.find_corpse_cont()
            self.corpse_cont = find_corpse_cont()
            if self.corpse_cont: # Corpse container detected
                if self.corpse_cont.IsOpen:
                    self.loot_bps = self.get_loot_bps(9605)
                    # self.loot_logic0()
                    self.loot_logic1()
            else: # No Corpse Open
                pass

    def cavebot_load(self):
        fname = QtGui.QFileDialog.getOpenFileName(
                self, 'Open Cavebot Waypoints...', 'cavebot/'
                )

        print 'Loading:', fname
        fname = fname.split('/')[-1]
        self.wlkr = CavebotWalker(fname) # Takes name without path
        self.lbl_cbot_file.setText('Waypoints: \n' + fname)
        self.cavebot_setcwlbl()

    def cavebot_setcwlbl(self):
        """Sets 'lbl_cbot_currwaypt' current waypoint text lbl
        """
        # if self.wlkr != None:
        # Code to get the bound method as string at curr_waypt
        # wp_str = str(
        #     self.wlkr.curr_waypt[1]).split('.')[1].split(' ')[0]
        self.lbl_cbot_currwaypt.setText(
            'Current Waypoint: \n' +
            str(self.wlkr.idx) + str(self.wlkr.curr_waypt[0])
            )

    def cavebot_restart(self):
        if self.wlkr != None:
            self.wlkr.restart()
            self.cavebot_setcwlbl()
            self.cb_cbot_wlkr.setCheckState(False)

    def cavebot_walker(self):
        if self.cb_cbot_wlkr.isChecked() == True:

            if self.wlkr != None:
                self.cavebot_logic()
                self.cavebot_setcwlbl()

        elif self.cb_cbot_wlkr.isChecked() == False:
            pass

    def cavebot_wrt_dia(self):

        # Set to parent object and show to make non-modal dialog
        self.wrt_dialog = CavebotWriterDialog()
        self.wrt_dialog.show()

    def main_loop(self):

        self.update_plyrinfo()

        self.bot_status = 'atk'
        self.attack()
        self.bot_status = 'def'
        self.defense()
        self.bot_status = 'loot'
        # self.support
        self.looter()

        self.bot_status = 'wlkr'
        self.cavebot_walker()

        # self.scripts

        self.pqi.deq()
        self.pqs.deq()

    def prof_save(self):
        #  QFileDialog.getSaveFileName(...)
        # settings = QSettings settings("/home/petra/misc/myapp.ini",
                    # QSettings.IniFormat)
        fname = QtGui.QFileDialog.getSaveFileName(
                    self, 'Save Profile', 'profiles/', '*.ini'
                    )

        print 'Saving...:', fname

        settings = QtCore.QSettings(fname, QtCore.QSettings.IniFormat)

        # Attack
        settings.setValue('atk_cb', self.atk_cb.checkState())
        settings.setValue('atk_type', self.atk_type.currentIndex())
        settings.setValue('atk_id', self.atk_id.currentIndex())
        settings.setValue('atk_id_le', self.atk_id_le.text())
        settings.setValue('atk_atcb0', self.atk_atcb0.checkState())
        settings.setValue('atk_atcb1', self.atk_cb.checkState())
        settings.setValue('atk_atcb2', self.atk_cb.checkState())
        settings.setValue('target_priority', str(self.target_priority)) # care
        settings.setValue('atk_chasecb', self.atk_chasecb.checkState())
        settings.setValue('atk_aoecb', self.atk_aoecb.checkState())
        settings.setValue('atk_aoetype', self.atk_aoetype.currentIndex())
        settings.setValue('atk_aoeid', self.atk_aoeid.currentIndex())
        settings.setValue('atk_aoesb1', self.atk_aoesb1.value())
        settings.setValue('atk_aoesb2', self.atk_aoesb2.value())
        settings.setValue('atk_aoesb3', self.atk_aoesb3.value())

        # Defense
        settings.setValue('def_hpcb', self.def_hpcb.checkState())
        settings.setValue('def_hpsb1', self.def_hpsb1.value())
        settings.setValue('def_hptype1', self.def_hptype1.currentIndex())
        settings.setValue('def_hpid1', self.def_hpid1.currentIndex())
        settings.setValue('def_hpsb2', self.def_hpsb2.value())
        settings.setValue('def_hptype2', self.def_hptype2.currentIndex())
        settings.setValue('def_hpid2', self.def_hpid2.currentIndex())
        settings.setValue('def_mpcb', self.def_mpcb.checkState())
        settings.setValue('def_mpsb1', self.def_mpsb1.value())
        settings.setValue('def_mptype1', self.def_mptype1.currentIndex())
        settings.setValue('def_mpid1', self.def_mpid1.currentIndex())
        settings.setValue('def_ut_hastecb', self.def_ut_hastecb.checkState())
        settings.setValue('def_ut_haste', self.def_ut_haste.currentIndex())
        settings.setValue('def_ut_invis', self.def_ut_invis.checkState())
        settings.setValue('def_ut_custcb', self.def_ut_custcb.checkState())
        settings.setValue('def_ut_custsb', self.def_ut_custsb.value())
        settings.setValue('def_ut_custle', self.def_ut_custle.text())

        # Spaceholder for next section

    def prof_load(self, filename):
        fname = QtGui.QFileDialog.getOpenFileName(
            self, 'Load Profile', 'profiles/', '*.ini'
            )
        print 'Loading...:', fname

        settings = QtCore.QSettings(fname, QtCore.QSettings.IniFormat)

        self.cb_main.setCheckState = False

        for key in settings.allKeys():
            key = str(key)
            # print key
            obj = getattr(self, key)
            # print obj

            if type(obj) == QtGui.QPushButton:
                pass # Future implementation
            elif type(obj) == QtGui.QCheckBox:
                obj.setCheckState(QtCore.Qt.CheckState(
                    settings.value(key).toPyObject()
                    ))
            elif type(obj) == QtGui.QSpinBox:
                obj.setValue(int(str(
                    settings.value(key).toPyObject()
                    )))
            elif type(obj) == QtGui.QComboBox:
                idx = str(settings.value(key).toPyObject())
                if idx:
                    obj.setCurrentIndex(int(idx))
            elif type(obj) == QtGui.QLineEdit:
                obj.setText(str(
                    settings.value(key).toPyObject()
                    ))
            elif type(obj) == list: # self.target_priority
                txt = str(settings.value(key).toPyObject())
                self.target_priority = literal_eval(txt)
            else:
                print 'invaid qtgui object'
                print type(obj)

        # Necessary for dependent widgets, to be processed after.
        delayed_keys = ['atk_id', 'atk_id_le', 'target_priority', 'atk_aoeid',
            'def_hpid1', 'def_hpid2', 'def_mpid1']
        for key in delayed_keys:
            obj = getattr(self, key)

            # Recycled code from previous section.
            if type(obj) == QtGui.QComboBox:
                idx = str(settings.value(key).toPyObject())
                if idx:
                    obj.setCurrentIndex(int(idx))
            elif type(obj) == QtGui.QLineEdit:
                obj.setText(str(
                    settings.value(key).toPyObject()
                    ))
            elif type(obj) == list: # self.target_priority
                txt = str(settings.value(key).toPyObject())
                self.target_priority = literal_eval(txt)
            else:
                print 'invaid qtgui object'
                print type(obj)

        print 'Loaded target priority: ', self.target_priority

class PrubotWindow(QtGui.QMainWindow):

    def __init__(self):

        super(PrubotWindow, self).__init__()

        self.initUI()

    def initUI(self):

        self.widget1 = PrubotWidget()
        self.setCentralWidget(self.widget1)

        self.setGeometry(150, 150, 700, 200)
        self.setWindowTitle('Prubot')
        # prufrock 8.6, ping?
        self.show()

        # self.main_loop()
        # if checkbox clicked?

def main():

    app = QtGui.QApplication(sys.argv)
    ex = PrubotWindow()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
