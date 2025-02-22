# Micropython espnow wrapper
Send and receive data between ESPs over espnow without worries. This library provides asynchronous message sending and receiving with support for chunked data transmission and acknowledgments.

## Features
- Asynchronous ESP-NOW message handling
- Automatic chunking of large messages
- CRC32 verification for data integrity
- Optional acknowledgment (ACK) support
- Configurable timeout and cycle time
- Debugging mode for easier troubleshooting

## Usage

### Initializing the ESPNowManager
```python
from mp_espnow_wrapper import ESPNowManager

esp_manager = ESPNowManager(peer='AA:BB:CC:DD:EE:FF', debug=True)
esp_manager.set_callback('on_receive', lambda msg: print("Received:", msg))
esp_manager.init()
```

### Sending Messages
```python
import asyncio

async def send():
    message = b'Hello ESP-NOW!'
    await esp_manager.send(message)

asyncio.run(send())
```

### Receiving Messages
The `init` method starts the message receiving process automatically.
Register a receive-callback by `set_callback('on_receive',<calback>)`. The callback needs to accept only one argument, namely the message

## Configuration
- `peer`: MAC address of the target device (default: broadcast)
- `rxbuf`: Buffer size for incoming messages
- `timeout_ms`: Message receive timeout in ms
- `cycle_time_ms`: Interval between message chunks (ms). In order to run stables needs to be > 2-3 ms
- `wait_msg_ack`: Whether to wait for message acknowledgment. This includes the respective on_receive callback at the receiver.
- `send_ack_afetr_cb`: Whether to send ACK after the callback execution.
- `send_async`: Whether to send messages asynchronously.
- `debug`: Enables debug output
