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
def injection():
    """
    """
    global client
    global inven

    # Get Client
    # client = Tibia.Objects.Client.GetClients()[1]
    client = Tibia.Util.ClientChooser.ShowBox()
    print client
    inven = client.Inventory

    # Remove path blocking objects
    for i in tid.obstacle_list:
        item = Tibia.Objects.Item(client, System.UInt32(i))
        item.SetFlag(Tibia.Addresses.DatItem.Flag.BlocksPath, False)

injection()

def bot_init():
    """Function refreshes objects that might get outdated after logging in/out
    """
    client.Console.Say('Hello World')
    global player
    player = client.GetPlayer()

bot_init()

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

def rel_to_tile(relx, rely, relz = 0):
    """Takes positions relative to player and returns the corresponding tile.
    relz not implemented.
    """
    xbound = (-8, 9)
    ybound = (-6, 7)
    # zbound = ()

    # Out of bounds check
    if (relx < xbound[0]) or (relx > xbound[1]):
        print 'relx out of bounds'
        return
    if (rely < ybound[0]) or (rely > ybound[1]):
        print 'rely out of bounds'
        return
    # if (relx < xbound[0]) or (relx > xbound[1]):
        # print 'relx out of bounds'
        # return

    pt = find_player_tile()
    floor_tiles = [i for i in client.Map.GetTilesOnSameFloor()] # 2D
    pt_no = pt.TileNumber


    # Find relative location of tile_no in memory
    dx = pt.MemoryLocation.X + relx
    dy = pt.MemoryLocation.Y + rely

    # Adjust memory locations
    adjx = dx
    adjy = dy
    if (dx < 0):
        adjx = dx + 18
    elif (dx > 17): # out of bounds, flip
        adjx = dx - 18
    if (dy < 0):
        adjy = dy + 14
    elif (dy > 13): # out of bounds, flip
        adjy = dy - 14

    # correct tile
    corr_tile = 1*adjx + 18*adjy

    return floor_tiles[corr_tile]

def get_adj_tiles():
    adj_tiles = []
    adj_coord = [(-1, -1), (0, -1), (+1, -1),
                 (-1, +0), (0, +0), (+1, +0),
                 (-1, +1), (0, +1), (+1, +1)]
    adj_coord.remove((0, +0)) # Can comment out later or add functionality

    for relxy in adj_coord:
        adj_tiles.append(rel_to_tile(*relxy))

    return adj_tiles

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

def test_fxn():
    # while True:
    # sleep(0.1)
    # print "loop"
    client.Console.Say('utana vid')
    # client.Console.Say('utana vid')
    # inven.GetItems()
    for i in inven.GetItems():
        if i.Id == 3725:
            i.Use()


if __name__ == '__main__':
    while True:
        sleep(0.1)
        test_fxn()
