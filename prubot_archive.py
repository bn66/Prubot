"""Putting away future functions or tests...
"""
import clr
# clr.System.Reflection.Assembly.LoadFile("C:\Users\Bill\Anaconda\Lib\site-packages\TibiaAPI.dll")
clr.AddReference('TibiaAPI')
from pdb import set_trace
from time import sleep

import Tibia
# import Tibia.Objects
# import Tibia.Properties
# import Tibia.Util

# from tibiaids import loot_gold, loot_stack, loot_commons, loot_rares
# from tibiaids import loot_list, loot_test
from tibiaids import *

# variables needed for all functions

# Get Client
client = Tibia.Util.ClientChooser.ShowBox()
# client = Tibia.Objects.Client.GetClients()[1]
print client
client.Console.Say('Hello World')

player = client.GetPlayer()
floor_tiles = client.Map.GetTilesOnSameFloor()

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

def mk_speechpkt():
    p = Tibia.Packets.Outgoing.PlayerSpeechPacket(client)

    p.SpeechType = Tibia.Constants.SpeechType.Say
    p.Receiver = ''
    # p.Receiver = System.String('')
    p.Message = 'TESTING'
    # p.Message = System.String('TESTING')
    p.ChannelId = Tibia.Constants.ChatChannel.None

    return p

def refresh_south():
    """Tiles initialize based on something? and i'm not sure when they
    update.
    """
    floor_tiles = [i for i in client.Map.GetTilesOnSameFloor()]
    # player_tile = floor_tiles[116]
    tile = floor_tiles[134] # items
    ground = tile.Ground #6591
    obj = [i for i in tile.Objects] # 6857
    items = [i for i in tile.Items] # 6856

    print 'TILE NUMBER', tile.TileNumber
    print ground.Id
    print [i.Id for i in obj]
    print [i.Id for i in items]

def tile_ref():
    """
    """
    tiles = list(client.Map.GetTiles())
    tiles_items = [list(i.Items) for i in tiles]

    # tiles_items_ids = []
    # for items in tiles_items:
        # for item in items:
    tiles_items_ids = [[i.Id for i in j] for j in tiles_items]
    return tiles, tiles_items, tiles_items_ids
    # tiles_ids = [i.Id for j in tiles_items for i in j]

    # what the fuck? try to understand his list comprehension.

def search_lofl(item, lofl):
    """search list of lists
    """
    for i in range(0,len(lofl)):
        if item in lofl[i]:
            print i, lofl[i].index(item)
            # return

    # if item in [j for i in lol for j in i]:
        # print 'FOUND'
        # return j.index(item), i.index(j)
    # 'd' in [elem for sublist in mylist for elem in sublist]

def foo_test():
    a,b,c = tile_ref()
    # search_lofl(3031, c)
    floor_tiles = list(client.Map.GetTilesOnSameFloor())
    floor_item_ids = [[i.Id for i in list(j.Items)] for j in floor_tiles]
    # floor_objs = [list(j.Objects) for j in floor_tiles]
    # floor_obj_ids = [[i.Data for i in j] for j in floor_objs]

    # set_trace()
    for i in range(0, len(floor_item_ids)): # 252
        if 3031 in floor_item_ids[i]:
            gold_tile = floor_tiles[i]
            break
        else:
            if i == len(floor_item_ids)-1:
                print 'GOLD NOT FOUND'
                return None
                # gold_tile = None

    # player_tile =
    print tile_to_rel_loc(gold_tile, find_player_tile())
    print tile_to_world_loc(gold_tile, find_player_tile())

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

def getbattlelist():
    battlelist = client.BattleList
    # battlelist.ShowInvisible()
    creatures = list(battlelist.GetCreatures())
    # for i in range(0, len(creatures)):
    #     if creatures[i].IsSelf() == True:
    #         creat_player = creatures[i]
    #         creat_player_index = i

def get_cl():
    creat_list = list(client.BattleList.GetCreatures())

    return creat_list

master = []
def ref():
    creat_list = list(client.BattleList.GetCreatures())

    for c in creat_list:
        line = (c.Name, c.Address, c.Data, c.Id, hex(c.Id))
        if c not in master:
            print line
            master.append(line)

def write_out():

    with open('creat.txt', 'w') as txt:
        for i in master:
            txt.write(str(i)+ '\n')

def creat_test(targ):
    """targ = creature object, test to remember how the GoTo function works.
    """
    print "Player GoTo: ", (player.GoTo.X,player.GoTo.Y,player.GoTo.Z)
    targ.Approach()
    print "Approach: ", (targ.X, targ.Y, targ.Z)
    print "Player GoTo: ", (player.GoTo.X,player.GoTo.Y,player.GoTo.Z)
    print "Player XYZ: ", (player.X,player.Y,player.Z)
    print "Diffs GoTo ", (targ.X - player.GoTo.X,
                        targ.Y - player.GoTo.Y,
                        targ.Z - player.GoTo.Z
                        )
    print "Diffs xyz ", (targ.X - player.X,
                        targ.Y - player.Y,
                        targ.Z - player.Z
                        )
    #approach? Follow?

"""Code to find memory xyz
tile_z = cellNr / (14*18);
tile_y = (cellNr - tile_z*14*18) / 18;
tile_x = (cellNr - tile_z*14*18 - tile_y*18);
"""

def tile_test():
    """Test to remember how tile objects and commands work
    """
    adj_tiles = get_adj_tiles()

    floor_ground_id = [i.Ground.Id for i in adj_tiles] # Single Item Object?)
    # floor_ground_data = [i.Ground.Data for i in adj_tiles] # Single Item Object?)
    floor_objs = [list(j.Objects) for j in adj_tiles]
    floor_obj_ids = [[i.Data for i in j] for j in floor_objs] # corpses?
    floor_items = [list(i.Items) for i in adj_tiles] # think about what about Sprite/SpriteIDs
    floor_item_ids = [[i.Id for i in j] for j in floor_items] # Actual items
    # set_trace()

    print 'Ground.Id', floor_ground_id # Tile Data/Id's?, literal ground.
    # print 'Ground.Data', floor_ground_data # None?
    print 'Objects.Data', floor_obj_ids # amount of items on the tile? Had object.Address when alive, 5 when dead
    print 'Items.Id', floor_item_ids # item ids on tile.; this is the thing that has the correct corpse, items that are on top are from position 0

    # Read about these objects and their data.  objects.data most confusing.

def inven_test():
    """Test to remember how client.Inventory and Containers are organized
    """
    # inven = client.Inventory
    # inven.Getcontainer # gets container at byte
    # inven.GetContainers gets all open containers
    # getcontaineritems # just container items
    # getItem(ItemLocation)
    # GetItem in slots
    # GetItems = Get all items, GetSlot Items (10) +Get Container items
    # Y =
    # Z = Location in individual container
    # GetItemINSlot starts at 1->10 : helm, neck, bp, arm, LH (below BP), RH, LEGS, boots, ring, arrowslot
    # Number containers? renumbers them or some shit?

    # Container Args
    # c.Amount = Number of items inside
    # c.HasParent = has parent backpack
    # c.Number # The client will assign the lowest AVAILABLE number, so if a container at 1 is closed and 0 and 2 are taken, 1 will be the new opened
    # c.OpenParent
    # c.Name name at the title bar of container
    citems = list(inven.GetItems())

    for i in citems:
        print (i.Location.ContainerId, i.Location.ContainerSlot,
            i.Id, i.Location.ToLocation().X,
            i.Location.ToLocation().Y, i.Location.ToLocation().Z)

    # (ItemLoc.ContainerId, ItemLoc.ContainerSlot,.Id, Loc().X, Loc().Y, Loc().Z)
    # ContainerId = Slot number?
    # ContainerSlot = location.Z
    # SlotItems (0, 0, ID, +1 0->9, 0)
    # (0, 0, 3390L, 0, 0)
    # (0, 0, 3055L, 1, 0)
    # Other containers First Container (containerId, +1, ID, containerid+64, +1)
    # Other containers Second Container (containerId, +1, ID, containerid+64, +1)

def plyr_idtype_ref():
    """Havne't figured out what these are yet
    """
    print player.TargetBattlelistId, 'BLID'
    print player.TargetBattlelistType, 'BLTYPE'
    print player.TargetId, 'ID' # Target id type...
    print player.TargetType, 'TYPE' # Non zero, unchanging?

if __name__ == '__main__':
    tile_test()


# auto 10 | dontlist | if ?$amuletslot.id != 3081 && $winitemcount.3081 >= 1] {equipammy 3081 | if ?$amuletslot.id == 3081] statusmessage 'SSA Equipped!' | end} | if [$winitemcount.3081 == 0 && $winitemcount.2867 >= 1] {openitem 2867 1 | statusmessage 'Open
# statusmessage 'Opening next SSA backpack!' | end}
class CustomSpeech(Tibia.Packets.OutgoingPacket):
    """
    """

    def __init__(self, client, st = None, rec = None, mes = None, cid = None):
        """
        """
        super(CustomSpeech, self).__init__(client)
        # pkt = Tibia.Packets.OutgoingPacket(client)

        self.SpeechType = st
        self.Receiver = rec
        self.Message = mes
        self.ChannelId = cid

        # Inherited
        self.Type = 150 # OutgoingPacketType.PlayerSpeech #0x96
        self.Destination = 1 # PacketDestination.Server 1
        # self.msg = Tibia.Packets.NetworkMessage(client, 4048)

    def ParseMessage(self):
        """
        """
        pass

    def ToNetworkMessage(self, msg):
        """
        """
        # set_trace()
        self.msg.AddByte(System.Byte(pkt.Type))
        # 0, 1, 1
        info = Tibia.Constants.SpeechTypeInfo(
                    Tibia.Constants.SpeechType.Say, System.Byte(1),
                    Tibia.Constants.AdditionalSpeechData.Location
                    )
        self.msg.AddByte(info.Value)

        # if (SpeechType == SpeechType.Private):
            # msg.AddString(Receiver)
        # elif (info.AdditionalSpeechData == AdditionalSpeechData.ChannelId):
            # msg.AddUInt16(ChannelId)

        self.msg.AddString('HELLO WORLD')


    # def Send(self):
    #     """
    #     """
    #     pass



def speech_pkt():
    """Make speech packet from scratch
    """
    # return msg, pkt

def SendPacketToServerByMemory(packet):
    """Objects.Client client, byte[] packet
    """
    pass
    # # turns packet/msg into a byte array
    # # packet_byte = System.Array.CreateInstance(System.Byte, packet.Length)
    # # for i in range(packet.Length):
    #     # # msg. add bytes,add byte, adduint32, add location...
    #     # packet[i] = System.Byte(0)
    #
    # bool ret = false
    # if (not client.IO.IsSendToServerCodeWritten):
    #     if (not client.IO.WriteSocketSendCode()):
    #         return false
    #
    # bufferSize = 4 + msg.Length
    # readyPacket = new byte[bufferSize]
    # Array.Copy(BitConverter.GetBytes(msg.Length), readyPacket, 4);
    # Array.Copy(packet, 0, readyPacket, 4, packet.Length);
    #
    # IntPtr pRemote = WinApi.VirtualAllocEx(client.ProcessHandle, IntPtr.Zero, /*bufferSize*/
    #     bufferSize,
    #     WinApi.AllocationType.Commit | WinApi.AllocationType.Reserve,
    #     WinApi.MemoryProtection.ExecuteReadWrite);
    #
    # if (pRemote != IntPtr.Zero)
    #     if (client.Memory.WriteBytes(pRemote.ToInt64(), readyPacket, bufferSize))
    #         IntPtr threadHandle = Tibia.Util.WinApi.CreateRemoteThread(client.ProcessHandle, IntPtr.Zero, 0,
    #             client.IO.SendToServerAddress, pRemote, 0, IntPtr.Zero);
    #         Tibia.Util.WinApi.WaitForSingleObject(threadHandle, 0xFFFFFFFF);//INFINITE=0xFFFFFFFF
    #         Tibia.Util.WinApi.CloseHandle(threadHandle);
    #
    #         ret = true;
    # if (pRemote != IntPtr.Zero)
    #     WinApi.VirtualFreeEx(
    #         client.ProcessHandle,
    #         pRemote,
    #         bufferSize,
    #         WinApi.AllocationType.Decommit | WinApi.AllocationType.Release);

    return ret;

def mem_test(msg):
    """
    """
    if msg == None:
        msg = Tibia.Packets.NetworkMessage.NetworkMessage(Client, 4048)
    # buffersize = 4048, buffer = new byte[buffer size]....

    msg.Reset()
    # ToNetworkMessage(msg)

    # if msg.Length > 8:
        # msg.InsetLogicalPacketHeader()
        # msg.PrepareToSend()
        # return SendPacketToServerByMemory(Client, msg.Data)
