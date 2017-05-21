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
    while True:
        # print plyr_statuses(player.Flags)
        ref()
        sleep(0.5)
        # set_trace()
