# ==========================================
# Stray Legends - Cosmic Expedition Decoder
# ==========================================

from pathlib import Path
import json
from datetime import datetime


# Packet configuration
PACKET_TYPE = 31010
HEADER_SIZE = 6

# Location of our test packet
PACKET_FILE = Path(__file__).parent / "cx_content.data"

# Data storage locations
DATA_DIRECTORY = Path(__file__).parent.parent / "data" / "cx"

CURRENT_FILE = DATA_DIRECTORY / "current.json"

HISTORY_DIRECTORY = DATA_DIRECTORY / "history"

MAX_HISTORY = 3


def decode_packet(packet_data):

    # Verify packet size
    if len(packet_data) < HEADER_SIZE:
        raise ValueError("Packet is too small.")

    # Extract packet header
    header = packet_data[:HEADER_SIZE]

    # Decode header values
    packet_type = int.from_bytes(header[0:2], "little")
    body_length = int.from_bytes(header[2:6], "little")

    # Extract protobuf body
    protobuf_data = packet_data[HEADER_SIZE:]

    print("\n--- Packet Information ---")
    print(f"Packet Type: {packet_type}")
    print(f"Declared Body Length: {body_length}")
    print(f"Actual Body Length: {len(protobuf_data)}")
    print(f"Total Packet Size: {len(packet_data)}")

    # Validate packet type
    if packet_type != PACKET_TYPE:
        raise ValueError(f"Unexpected packet type: {packet_type}")

    # Validate body length
    if body_length != len(protobuf_data):
        raise ValueError("Packet body length does not match header.")

    print("\nPacket successfully validated!")

    return protobuf_data

# Protobuf varint decoder
def read_varint(data, offset):

    result = 0
    shift = 0

    while True:

        byte = data[offset]
        offset += 1

        result |= (byte & 0x7F) << shift

        if not (byte & 0x80):
            break

        shift += 7

    return result, offset

# Parsing the protobuf fields
def parse_protobuf_fields(data):

    fields = []
    offset = 0

    while offset < len(data):

        # Read the field tag
        tag, offset = read_varint(data, offset)

        # Extract field number and wire type
        field_number = tag >> 3
        wire_type = tag & 0x07

        if field_number == 0:
            raise ValueError("Invalid Protobuf field number.")

        # Wire type 0: Varint
        if wire_type == 0:
            value, offset = read_varint(data, offset)

        # Wire type 1: 64-bit value
        elif wire_type == 1:
            value = data[offset:offset + 8]
            offset += 8

        # Wire type 2: Length-delimited value
        elif wire_type == 2:
            length, offset = read_varint(data, offset)
            value = data[offset:offset + length]
            offset += length

        # Wire type 5: 32-bit value
        elif wire_type == 5:
            value = data[offset:offset + 4]
            offset += 4

        else:
            raise ValueError(f"Unsupported Protobuf wire type: {wire_type}")

        if offset > len(data):
            raise ValueError("Unexpected end of Protobuf data.")

        fields.append({
            "field_number": field_number,
            "wire_type": wire_type,
            "value": value
        })

    return fields

# Decode individual player fields
def decode_player(player_data):

    fields = parse_protobuf_fields(player_data)

    player = {
        "rank": None,
        "player_id": None,
        "name": None,
        "cx_score": 0
}

    for field in fields:

        field_number = field["field_number"]
        value = field["value"]

        if field_number == 1:
            player["rank"] = value

        elif field_number == 2:
            player["player_id"] = value

        elif field_number == 3:
            player["name"] = value.decode("utf-8")

        elif field_number == 6:
            player["cx_score"] = value

    return player

# adds historical data
def save_cx_data(players):

    # Create directories if they don't exist
    HISTORY_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Check whether current data already exists
    if CURRENT_FILE.exists():

        with CURRENT_FILE.open("r", encoding="utf-8") as file:
            previous_players = json.load(file)

        # Only archive if the data has changed
        if previous_players != players:

            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")

            history_file = HISTORY_DIRECTORY / f"{timestamp}.json"

            # Move previous data into historical storage
            CURRENT_FILE.replace(history_file)

    # Save the latest leaderboard
    with CURRENT_FILE.open("w", encoding="utf-8") as file:
        json.dump(players, file, indent=4, ensure_ascii=False)

    # Retrieve historical files, newest first
    history_files = sorted(
        HISTORY_DIRECTORY.glob("*.json"),
        key=lambda file: file.name,
        reverse=True
    )

    # Remove anything beyond our retention limit
    for old_file in history_files[MAX_HISTORY:]:

        old_file.unlink()

    print(f"\nCurrent data saved: {CURRENT_FILE.name}")
    print(f"Historical versions retained: {min(len(history_files), MAX_HISTORY)}")

def main():

    print("Stray Legends - CX Decoder")
    print("==========================")

    # Check that our file exists
    if not PACKET_FILE.exists():
        raise FileNotFoundError(f"Could not find: {PACKET_FILE}")

    # Read binary file
    packet_data = PACKET_FILE.read_bytes()

    print(f"\nLoaded file: {PACKET_FILE.name}")
    print(f"File size: {len(packet_data)} bytes")

    # Decode packet
    protobuf_data = decode_packet(packet_data)

    print("\n--- CX Player Records ---")

    print("Rank\tPlayer ID\tName\tCX Score")

    fields = parse_protobuf_fields(protobuf_data)

    players = []

    for field in fields:

        if field["field_number"] == 3:

            player = decode_player(field["value"])

            players.append(player)

    for player in players:

        print(
            f"Rank: {player.get('rank')}\t "
            f"ID: {player.get('player_id')}\t "
            f"Name: {player.get('name')}\t "
            f"Score: {player.get('cx_score')}"
        )

    print(f"\nTotal players found: {len(players)}")

    # Export player records to JSON
    save_cx_data(players)


if __name__ == "__main__":
    main()