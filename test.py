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
# client = Tibia.Objects.Client.GetClients()[0]
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
    # Unhandled Exception: System.NullReferenceException: Object reference not set to an instance of an object.
    # at Tibia.Objects.Map.GetTileWithPlayer()
    # at Tibia.Objects.Map.<GetTiles>d__6.MoveNext()
    # at Python.Runtime.Iterator.tp_iternext(IntPtr ob)
    # try:
    if client.LoggedIn:
        # floor_tiles = list(client.Map.GetTilesOnSameFloor())
        floor_tiles = get_floor_tiles()
        floor_obj_data = [[i.Data for i in list(j.Objects)] for j in floor_tiles]
        # floor_objs = [list(j.Objects) for j in floor_tiles]
        # floor_obj_ids = [[i.Data for i in j] for j in floor_objs]

        for obj in range(0, len(floor_obj_data)): # 252
            if player.Id in floor_obj_data[obj]:
                return floor_tiles[obj] # Player tile
    # except:
        # print 'FIND PLAYER TILE ERROR'
    print 'Player tile not found'
    return None

def get_floor_tiles():
    # floor_tiles = list(client.Map.GetTilesOnSameFloor()) # Bugged out often
    tiles = list(client.Map.GetTiles())

    # Calculate Memory Location
    if player.Z >= 8: # Below Ground
        mfloor = 2
    else:
        mfloor = abs(player.Z - 7)

    return tiles[(mfloor*252):((mfloor+1)*252)]

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

"""Next up: maybe do the first commit,
and then add the queue systems/objects in order to process rest of the GUI

Supp: Skinning creatures.

Cavebot fix, with checks
First commitTools/support/scripts
"""

def get_cl():
    creat_list = list(client.BattleList.GetCreatures())

    return creat_list

def ref():

    pass

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
        self.idx = 0
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

"""Testing
"""

class Simulated(object):

    def __init__(self):
        self.loot_creats = []
        self.loot_corpse_q = []
        self.pqi = PQItem()

    def foo(self):
        pass

if __name__ == '__main__':
    # sim = Simulated()
    # super(CavebotWalker, self).__init__(filename)
    wlkr = CavebotWalker('test.txt')
    set_trace()
