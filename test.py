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
                floor_obj_data = [[
                    i.Data for i in list(j.Objects)] for j in floor_tiles]
                # floor_objs = [list(j.Objects) for j in floor_tiles]
                # floor_obj_ids = [[i.Data for i in j] for j in floor_objs]

                for obj in range(0, len(floor_obj_data)): # 252
                    if player.Id in floor_obj_data[obj]:
                        return floor_tiles[obj] # Player tile
        except:
            pass

    print 'Player tile not found'
    return None

def get_floor_tiles():
    """Wrapper for GetTilesOnSameFloor that will catch
    System.NUllReferenceException
    """
    if client.LoggedIn:
        try:
            # Try to catch System.NUllReferenceException race condition
            if client.Map.GetTileWithPlayer(): #
                floor_tiles = list(client.Map.GetTilesOnSameFloor())
                return floor_tiles
        except:
            pass

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

def set_looter(bpid):
    """Will find the loot container. Will return container and a list of the
    loot bps inside
    """

    for i in inven.GetContainers():
        count = 0
        for j in list(i.GetItems()):
            if j.Id == bpid:
                count += 1

            if count > 2: # Arbitrary limit
                # Is the container with loot BP's
                # Find loot bps
                bp_list = []
                for k in i.GetItems():
                    if k.Id == bpid:
                        bp_list.append(k)
                return i, bp_list

    # print 'loot_cont not found'
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
    # targ = 'yourself' 'target' 'crosshairs', 'none'
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
    elif targ == 'none':
        args.append(0) # Index
        pkt = mk_itemuse(*args)
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
    0: Life: HP/E-Ring (Emergency?)
    1: Life: MP, Attacking runes
    2: Looter: Looting (Move Item, use item); Support: empty vials, eater
    3: Skinner
    4: Looter: Walk to corpse, use corpse.
    5: Cavebot waypoints: (Use, say?, Goto.) # Currently unused

    Will be a queue of lists in the format ['packettype', [args]]
    """

    def __init__(self):
        levels = 6
        super(PQItem, self).__init__(levels)
        self.tryct = [0]*levels
        self.maxct = [None, None, None, 20, 20]

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
            if flvl == 0: # 0: Life: HP/E-Ring (Emergency?)
                # Spam them? Send packets twice?
                pkt.Send()
            elif flvl == 1: # 1: Life: MP, Attacking runes
                # Should run until completion.
                pkt.Send()
            elif flvl == 2: # 2: Looter: (Move Item, use item); Support: EV
                # Should run until completion.
                pkt.Send()
            elif flvl == 3: # 3: Skinner

                conds = [not find_corpse_cont()
                   ]

                if all(conds):
                    toloc = Tibia.Objects.Location(*args[2])
                    if player.DistanceTo(toloc) < 2:
                        pkt.Send() # Should be sent when in position.
                    elif player.DistanceTo(toloc) < 10: #
                        player.GoTo = toloc
                        self.items[flvl].append(nxt)
                    else:
                        # Packet deqs, without sending
                        pass

            elif flvl == 4: # 4: Looter: Walk to corpse, use corpse.
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


            elif flvl == 4: # 4: Cavebot waypoints: (Use, say?, Goto.)
                # Implemented instead in cavebot walker
                pass

class PQSay(PQueue):
    """client.Console.Say
    0: Life: Heal spells
    1: Attack spells
    2: Utility, spells

    Is a queue full of strings.
    """


    def __init__(self):
        levels = 3
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

"""Code
"""
class TestObject(object):

    pqi = PQItem()
    pqs = PQSay()

    def __init__(self):

        # Looter Section
        # self.loot_lbl = QtGui.QLabel(self.loot_lbl_str + 'Off')
        # self.loot_findcb = QtGui.QCheckBox('Find Corpse On')
        # self.loot_lootcb = QtGui.QCheckBox('Looter On')
        # self.loot_skincb = QtGui.QCheckBox('Skinner On')

        # Shared between looters
        self.loot_cont = None
        self.loot_creats = []
        self.loot_corpse_q = []
        # self.loot_lootpb = QtGui.QPushButton('Looter PushButton')

        # Loot logic 0
        self.reset_loot_logic1()
        self.loot_lootfxn = self.loot_logic0
        # self.loot_lootcb.stateChanged.connect(self.set_ll0_bps)
        # self.loot_lootpb.clicked.connect(self.reset_loot_logic1)

        # Loot logic 1
        # self.reset_loot_logic1()
        # self.loot_lootfxn = self.loot_logic1
        # self.loot_lootpb.clicked.connect(self.reset_loot_logic1)

    def chng_loot_lbl(self, text):
        loot_lbl_str = 'Ltr Status: '
        # self.loot_lbl = QtGui.QLabel(loot_lbl_str + text)
        print loot_lbl_str + text

    def set_ll0_bps(self):
        """Sets loot logic 0 bps by finding container with number 15
        """
        # self.

        if not inven.GetContainer(15):
            self.reset_loot_logic1()

            bpmain = inven.GetItemInSlot(3)
            loc = bpmain.Location.ToLocation()
            mk_itemuse([loc.X, loc.Y, loc.Z], bpmain.Id, 0, 15).Send()
            # self.loot_cont_rares = inven.GetContainer(15)

            # bp_rare = self.loot_bps[self.idx_rare]
            # loc = bp_rare.Location.ToLocation()
            # mk_itemuse([loc.X, loc.Y, loc.Z], bp_rare.Id, 0, 15).Send()

            self.chng_loot_lbl('Loot SubConts Set')

        # print
        # self.loot_cont_rares = inven.GetContainer(15)

    def reset_loot_logic1(self):
        self.idx_rare = 0
        self.idx_stk = -1
        self.idx_com = -2
        self.ct_rare = 0
        self.ct_stk = 0
        self.ct_com = 0

        print 'Loot Logic1 Reset'

    def is_readytoloot(self):
        """Looting Algorithm needs:
        -Loot Container with the sub bp's
        -Container to count items

        Returns boolean
        """
        # Container for Rares Set
        self.loot_cont_rares = inven.GetContainer(15)
        if self.loot_cont_rares == None:
            self.chng_loot_lbl('Loot SubCont Missing')
            return False

        try:
            self.loot_cont, self.loot_bps = set_looter(9605)
            self.chng_loot_lbl('Ready')
            return True
        except:
            self.chng_loot_lbl('Loot Cont Missing')
            # self.loot_cont = set_looter(9605) # None Type
            return False

    def loot_enq_move(self, item, toloc):
        """Put a move item command in the pqi object.
        item = Tibia.Objects.Item object
        toloc = Location object to move item.
        """
        itemloc = item.Location.ToLocation()
        self.pqi.enq(2, ['move', [[itemloc.X, itemloc.Y, itemloc.Z],
                                item.Id, itemloc.Z,
                                [toloc.X, toloc.Y, toloc.Z],
                                item.Count
                                ]])

    def loot_logic0(self):
        """Placeholder for future implementation
        5 is reserved for corpses
        15 for rares.
        Will ignore stackables and commons for now.
        Return after every statement
        """
        corpse_items = list(self.corpse_cont.GetItems())

        for i in corpse_items:
            # print 'Scanning Corpse @ Item.Id: ', i.Id
            if i.Id in tid.loot_gold:
                bpmain_item = inven.GetItemInSlot(3)
                self.loot_enq_move(i, bpmain_item.Location.ToLocation())
                print 'Looting: ', tid.loot_list[i.Id]

                return

            elif i.Id in tid.loot_list: # and not in loot_gold

                if (i.Id in tid.loot_rares) or (i.Id in tid.loot_commons):
                    cntr = self.loot_cont_rares
                    if cntr.Amount == cntr.Volume:
                        self.idx_rare += 1
                        bp = self.loot_bps[self.idx_rare]
                        loc = bp.Location.ToLocation()
                        self.pqi.enq(2, ['use',
                                [[loc.X, loc.Y, loc.Z], bp.Id, 0, 15]])
                        # mk_itemuse([loc.X, loc.Y, loc.Z], bp.Id, 0, 15).Send()]
                        return
                    lootbp = self.loot_bps[self.idx_rare]
                    # print 'LOOT BP SET 722'
                elif i.Id in tid.loot_stack:
                    lootbp = self.loot_bps[self.idx_stk]
                    # print 'LOOT BP SET 725'

                # set_trace()
                self.loot_enq_move(i, lootbp.Location.ToLocation())
                # i.Move(lootbp.Location, System.Byte(i.Count)) # IMPLEMENT PACKET!
                print 'Looting: ', tid.loot_list[i.Id]

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

        self.corpse_cont.Close() # Should only occur if corpse is empty

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

    def looter(self):

        # Container names: "Dead, remains, slain, lifeless nettle"
        # cb checked and player's loot container is open
        # if self.loot_lootcb.isChecked() and self.looter_ready():
        if True and self.is_readytoloot():
            self.corpse_cont = find_corpse_cont()
            # self.loot_bps = self.get_loot_bps(9605)
            if self.corpse_cont: # Corpse container detected
                if self.corpse_cont.IsOpen:
                    self.loot_lootfxn()
        # elif not self.loot_lootcb.isChecked():
        #     # Update string: Looter Off
        #     pass
        # elif not self.looter_ready:
        #     # Update string: No Loot BP
        #     pass

    def main_loop(self):

        # self.bot_status = 'loot'
        self.looter()

        self.pqi.deq()
        self.pqs.deq()

    # def anti_stuck(self):
    #     """Workaround for an unknown bug where player walker is stuck.
    #     Player is shown in one location but is actually one square away. Is
    #     likely a bug with 'goto' function
    #     """
    #     currtime = time()
    #     conditions = [self.as_loc_old == player.Location,
    #         player.IsWalking # , self.pqi.isempty()
    #         ]
    #
    #     if self.as_loc_old != player.Location:
    #         self.as_time = time()
    #
    #     if all(conditions):
    #         if currtime > self.as_time + 60:
    #             # Machete, on playertile, ground
    #             # self.pqi.enq(3, ['hotkey', [3308, 'crosshairs',
    #             #                             [player.X, player.Y, player.Z],
    #             #                             454, 0]])
    #             # 84 FF FF 00 00 00 14 17 00 D9 95 9B 10
    #
    #             self.pqi.enq(2, ['hotkey', [5908, 'yourself']])
    #             # inc = 5
    #             #
    #             # mk_itemuse([player.X-inc, player.Y, player.Z], 0, 0, 0).Send()
    #             # mk_itemuse([player.X+inc, player.Y, player.Z], 0, 0, 0).Send()
    #             # mk_itemuse([player.X, player.Y+inc, player.Z], 0, 0, 0).Send()
    #             # mk_itemuse([player.X, player.Y-inc, player.Z], 0, 0, 0).Send()
    #
    #             print 'PLAYER UNSTUCK'
    #             self.as_time = time()
    #
    #     self.as_loc_old = player.Location

def ref():
    floor_tiles = get_floor_tiles()
    for tile in floor_tiles:
        tile_objs = list(tile.Objects)
        print [obj.Id for obj in tile_objs]
        set_trace()

def skin_test():
    floor_tiles = get_floor_tiles()
    for tile in floor_tiles:
        tile_objs = list(tile.Objects)
        # print [obj.Id for obj in tile_objs]
        for t_obj in tile_objs:
            if t_obj.Id in tid.skin_list:

                if t_obj.Id in tid.skin_obsidian:
                    # 5908 - obsidian knife
                    fsid = 5908
                elif t_obj.Id in tid.skin_stake:
                    # 5942 - blessed wooden stake
                    fsid = 5942
                elif t_obj.Id in tid.skin_fish:
                    # 3483 - fishing rod
                    fsid = 3483

                # def mk_hotkey_pkt(item_id, targ, toloc = None, tosid = 0, tosp = None)
                self.pqi.enq(2, ['hotkey', [
                                    fsid,
                                    'crosshairs',
                                    tile_to_world_loc(
                                        tile, find_player_tile()
                                        ), # This is a tuple
                                    t_obj.Id,
                                    t_obj.StackOrder
                                    ]])

def mana_sit():
    # while True:
    # sleep(0.1)
    # print "loop"
    client.Console.Say('utana vid')
    # client.Console.Say('utana vid')
    # inven.GetItems()
    for i in inven.GetItems():
        if i.Id == 3725:
            i.Use()

def test_fxn():
    """
    """
    inc = 5
    # player.GoTo = Tibia.Objects.Location(player.X-inc, player.Y, player.Z)
    # player.GoTo = Tibia.Objects.Location(player.X+inc, player.Y, player.Z)
    # player.GoTo = Tibia.Objects.Location(player.X+inc, player.Y, player.Z)

    mk_itemuse([player.X-inc, player.Y, player.Z], 0, 0, 0).Send()
    mk_itemuse([player.X+inc, player.Y, player.Z], 0, 0, 0).Send()
    mk_itemuse([player.X, player.Y+inc, player.Z], 0, 0, 0).Send()
    mk_itemuse([player.X, player.Y-inc, player.Z], 0, 0, 0).Send()

def tool_mwt_fxn():
    """
    """
    # client.Screen.DrawCreatureText(
    #     System.UInt32(player.Id),
    #     Tibia.Objects.Location(0, 1, 0),
    #     System.Drawing.Color.Green,
    #     Tibia.Constants.ClientFont.NormalBorder,
    #     '12345'
    #     )
    # Draw once, then update it.
    # is ready but something wrong with pipe.
    # Freezing here.  client.Dll.PipeIsReady.WaitOne()
    # Could send packet yourself
    # http://tpforums.org/forum/archive/index.php/t-5535.html
    # http://tpforums.org/forum/archive/index.php/t-3448.html
    # http://tpforums.org/forum/archive/index.php/t-1706.html
    # http://tpforums.org/forum/archive/index.php/t-1057.html

    # System.InvalidOperationException: Pipe hasn't been connected yet.
    # Pipe is not connected, but can't figure out at which point the event isn't working
    # client.Dll.InitializePipe()
    # client.Dll.PipeIsReady.WaitOne()
    Tibia.Packets.Pipes.DisplayCreatureTextPacket.Send(
        client,
        System.UInt32(player.Id),
        'MyChar',
        Tibia.Objects.Location(0, 1, 0),
        System.Drawing.Color.Green,
        Tibia.Constants.ClientFont.NormalBorder,
        'HELLO WORLD'
        )

def my_hndlr(type, data):

    pass

def splt_pkt_frm_server():
    void SplitMessageFromServer(byte type, byte[] data)
    {
        if (uxLogServer.Checked)
        {
            if (FilterPacket(type, true))
            {
                LogPacket(data, "SERVER", "CLIENT");
            }
        }
    }

def splt_pkt_frm_client():
    void SplitMessageFromServer(byte type, byte[] data)
    {
        if (uxLogServer.Checked)
        {
            if (FilterPacket(type, true))
            {
                LogPacket(data, "SERVER", "CLIENT");
            }
        }
    }

def pxy_test():
    """
    """
    client.IO.StartProxy()

    proxy = client.IO.Proxy

    # proxy.ReceivedTextMessageIncomingPacket += Tibia.Packets.Proxy.IncomingPacketListener(Proxy_ReceivedTextMessageIncomingPacket)
    # https://pythonnet.github.io/ # do a delegate
    # http://pythonnet.sourceforge.net/readme.html#delegates
    proxy.SplitPacketFromServer += SplitMessageFromServer
    proxy.SplitPacketFromClient += SplitMessageFromClient

    client.IO.Proxy.SplitPacketFromServer += delegate(byte type, byte[] data)

    bool Proxy_ReceivedTextMessageIncomingPacket(IncomingPacket packet)
        Tibia.Packets.Incoming.TextMessagePacket p = (Tibia.Packets.Incoming.TextMessagePacket)packet;
        return true;


if __name__ == '__main__':
    # thing = TestObject()
    # while True:
        # sleep(0.1)
        # floor_tiles = list(client.Map.GetTilesOnSameFloor())
        # test_fxn()
        # mana_sit()
        # thing.main_loop()
    # ref()
    # skin_test()
    tool_mwt_fxn()
