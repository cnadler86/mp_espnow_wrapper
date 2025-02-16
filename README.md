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
```

### Sending Messages
```python
import asyncio

async def send():
    message = b'Hello ESP-NOW!'
    await esp_manager.send_message(message)

asyncio.run(send())
```

### Receiving Messages
```python
asyncio.run(esp_manager.receive_message())
```

## Configuration
- `peer`: MAC address of the target device (default: broadcast)
- `rxbuf`: Buffer size for incoming messages
- `timeout`: Message receive timeout in ms
- `cycle_time`: Interval between message chunks (ms). In order to run stables needs to be > 2-3 ms
- `wait_msg_ack`: Whether to wait for message acknowledgment. This includes the respective on_receive callback at the receiver.
- `debug`: Enables debug output

## License
This project is licensed under the MIT License.

## Contribution
Feel free to submit issues or pull requests to improve the project!

