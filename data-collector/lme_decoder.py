# ==========================================
# Stray Legends - LME Decoder
# ==========================================

from pathlib import Path
import json
from datetime import datetime


# Packet configuration
PACKET_TYPE = 30906
HEADER_SIZE = 6

# Location of our test packet
PACKET_FILE = Path(__file__).parent / "lme_content.data"

# Data storage locations
DATA_DIRECTORY = Path(__file__).parent.parent / "data" / "lme"

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
        "lme_score": 0
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
            player["lme_score"] = value

    return player

# adds historical data
def save_lme_data(players):

    # Create directories if they don't exist
    HISTORY_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Always update the current leaderboard
    with CURRENT_FILE.open("w", encoding="utf-8") as file:
        json.dump(players, file, indent=4, ensure_ascii=False)

    print(f"\nCurrent data saved: {CURRENT_FILE.name}")

    # Save the last updated timestamp
    timestamp_file = CURRENT_FILE.parent / "last_updated.json"

    with timestamp_file.open("w", encoding="utf-8") as file:
        json.dump({
            "last_updated": datetime.now().astimezone().isoformat(timespec="minutes")
        }, file, indent=4)

    print("Last updated timestamp saved.")

    # Create or update this week's snapshot on Wednesday
    if datetime.now().weekday() == 2:

        snapshot_date = datetime.now().strftime("%Y-%m-%d")
        history_file = HISTORY_DIRECTORY / f"{snapshot_date}.json"

        with history_file.open("w", encoding="utf-8") as file:
            json.dump(players, file, indent=4, ensure_ascii=False)

        # Keep this week plus the three previous weekly snapshots
        history_files = sorted(
            (
                file for file in HISTORY_DIRECTORY.glob("*.json")
                if file.name != "index.json"
            ),
            key=lambda file: file.name,
            reverse=True
        )

        for old_file in history_files[4:]:
            old_file.unlink()

        # Create an index of the available weekly snapshots
        history_files = sorted(
            (
                file for file in HISTORY_DIRECTORY.glob("*.json")
                if file.name != "index.json"
            ),
            key=lambda file: file.name,
            reverse=True
        )

        history_index = [
            file.name
            for file in history_files
        ]

        index_file = HISTORY_DIRECTORY / "index.json"

        with index_file.open("w", encoding="utf-8") as file:
            json.dump(history_index, file, indent=4)

        print(f"Weekly snapshot saved: {history_file.name}")
        print(f"Weekly snapshots retained: {min(len(history_files), 4)}")

    else:
        print("No weekly snapshot created (not Wednesday).")



def main():

    print("Stray Legends - LME Decoder")
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

    print("\n--- LME Player Records ---")

    print("Rank\tPlayer ID\tName\tLME Score")

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
            f"Score: {player.get('lme_score')}"
        )

    print(f"\nTotal players found: {len(players)}")

    # Export player records to JSON
    save_lme_data(players)


if __name__ == "__main__":
    main()