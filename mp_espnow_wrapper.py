import asyncio
from aioespnow import AIOESPNow
from network import WLAN, STA_IF
import struct
from binascii import crc32
from time import ticks_ms, ticks_diff

def parse_mac_address(mac_addr_str):
    return bytes(int(b, 16) for b in mac_addr_str.split(':')) if mac_addr_str else None

def format_mac_address(mac_addr):
    return ':'.join('%02x' % b for b in mac_addr)

def alive_counter_generator():
    while True:
        for i in range(16):
            yield struct.pack('!B', i)

class ESPNowManager:
    START_BYTE = b'\x02' * 4
    END_BYTE = b'\x55'
    ACK_MSG = b'\x06\x06'  # Beispiel-ACK-Nachricht
    
    def __init__(self, peer=None, rxbuf=None, timeout=1000, cycle_time=5, wait_msg_ack=False, debug=False):
        if not WLAN().active():
            WLAN(STA_IF).active(True)
        self.esp = AIOESPNow()
        if rxbuf:
            self.esp.config(rxbuf=rxbuf)
        if not self.esp.active():
            self.esp.active(True)
        
        self.peer = parse_mac_address(peer) or b'\xFF' * 6
        self.debug = debug
        self.wait_msg_ack = wait_msg_ack
        self.cycle_time = cycle_time
        self.callbacks = {'on_receive': None, 'on_timeout': None}
        self.timeout = timeout
        self.alive_counter_gen = alive_counter_generator()
        self.CHUNK_SIZE = 250
        self.lock = asyncio.Lock()
        self.ACK_received = asyncio.Event()
        if self.peer:
            self.esp.add_peer(self.peer)
    
    def set_callback(self, event, callback):
        if event in self.callbacks:
            self.callbacks[event] = callback

    async def send_ACK(self):
        await self.lock.acquire()
        if self.debug:
            print('Sending ACK')
        self.esp.send(self.peer, self.ACK_MSG)
        self.lock.release()

    async def send_message(self, message: bytes):
        if message is None:
            return
        await self.lock.acquire()

        delta_first = len(self.START_BYTE) + 4
        delta_last = len(self.END_BYTE) + 4
        chunk_size_init = self.CHUNK_SIZE - 1
        send = self.esp.send
        peer = self.peer
        alive_counter = self.alive_counter_gen
        header = self.START_BYTE + struct.pack('!I', len(message))
        foot = struct.pack('!I', crc32(message)) + self.END_BYTE
        cycle_time = self.cycle_time
        
        is_first = True
        while message:
            chunk_size = chunk_size_init
            is_last = len(message) <= chunk_size - delta_last
            
            if is_first:
                chunk_size -= delta_first
            elif is_last:  
                chunk_size -= delta_last

            chunk = message[:chunk_size]
            message = message[chunk_size:]

            chunk = (header if is_first else b'') + next(alive_counter) + chunk + (foot if is_last else b'')
            if is_first:
                is_first = False
            
            try:
                if hasattr(send, '__iter__'):
                    await send(peer, chunk)
                else:
                    send(peer, chunk)
            except Exception as e:
                print('Fehler beim Senden:', e)
            await asyncio.sleep_ms(cycle_time)
        
        self.lock.release()
        
        if self.wait_msg_ack:
            if self.debug:
                print('Waiting for ACK')
            await asyncio.wait_for_ms(self.ACK_received.wait(), timeout=self.timeout)
            if self.ACK_received.is_set():
                if self.debug:
                    print("ACK erhalten")
            else:
                print("ACK nicht erhalten, Nachricht möglicherweise verworfen")
            self.ACK_received.clear()

    async def receive_message(self):
        last_alive_counter = None
        syncing = True
        expected_length = None
        received_crc = None
        airecv = self.esp.airecv
        timeout = self.timeout
        callbacks = self.callbacks
        debug = self.debug
        while True:
            try:
                _, msg = await asyncio.wait_for_ms(airecv(), timeout=timeout)
                
                if msg == self.ACK_MSG:
                    self.ACK_received.set()
                    continue
                
                if len(msg) > self.CHUNK_SIZE:
                    syncing = True
                    if debug:
                        print("Warnung: Nachricht zu groß! Warten auf Start-Byte...")
                    continue

                if syncing:
                    if msg.startswith(self.START_BYTE):
                        start = ticks_ms()
                        last_alive_counter = None
                        syncing = False
                        msg = msg[len(self.START_BYTE):]

                        if len(msg) < 5:
                            if debug:
                                print("Fehler: Ungültiger Start-Chunk")
                            syncing = True
                            continue

                        expected_length = struct.unpack('!I', msg[:4])[0]
                        msg = msg[4:]
                        msg_buffer = bytearray(expected_length)
                        buffer_index = 0
                    else:
                        continue

                alive_counter = msg[0]
                if last_alive_counter is not None and ((last_alive_counter + 1) % 16) != alive_counter:
                    if debug:
                        print(f"Warnung: Alive-Counter-Sprung erkannt!")
                    syncing = True
                    continue
                last_alive_counter = alive_counter
                msg = msg[1:]

                if expected_length - buffer_index <= self.CHUNK_SIZE and msg.endswith(self.END_BYTE):
                    if len(msg) < 5:
                        print("Fehler: Letztes Chunk zu klein!")
                        syncing = True
                        continue

                    received_crc = struct.unpack('!I', msg[-5:-1])[0]
                    msg = msg[:-5]
                    syncing = True

                if buffer_index + len(msg) > expected_length:
                    print("Fehler: Nachricht größer als erwartet!")
                    syncing = True
                    continue

                msg_buffer[buffer_index:buffer_index + len(msg)] = msg
                buffer_index += len(msg)

                if buffer_index >= expected_length and received_crc is not None:
                    calculated_crc = crc32(msg_buffer)
                    if received_crc == calculated_crc:
                        if callbacks['on_receive']:
                            callbacks['on_receive'](msg_buffer)
                            if debug:
                                print('Empfangszeit:', ticks_diff(ticks_ms(), start))
                        await self.send_ACK()
                    else:
                        print("CRC-Fehler: Nachricht beschädigt")
                    msg_buffer = None
                    received_crc = None
            except asyncio.TimeoutError:
                if callbacks['on_timeout']:
                    callbacks['on_timeout']()
