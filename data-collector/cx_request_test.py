from pathlib import Path
import requests

URL = "https://prod-game.survivorio.com/"

BASE_DIRECTORY = Path(__file__).parent
REQUEST_FILE = BASE_DIRECTORY / "cx_request.data"
RESPONSE_FILE = BASE_DIRECTORY / "cx_content.data"

DXX_CHECK = "BD09E0B15B49FFA0D1AC10B70BB507FE89D88CFE9ACC4A83DCC231DFFB654502"


def main():

    print("CX Request Replay Test")
    print("======================")

    if not REQUEST_FILE.exists():
        raise FileNotFoundError(REQUEST_FILE)

    request_body = REQUEST_FILE.read_bytes()

    print(f"\nRequest body size: {len(request_body)} bytes")

    headers = {
        "User-Agent": "UnityPlayer/2022.3.62f2 (UnityWebRequest/1.0, libcurl/8.10.1-DEV)",
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "DxxVersion": "5410",
        "DxxHotVersion": "5400",
        "DxxTime": "0",
        "DxxCheck": DXX_CHECK,
        "DxxType": "31009",
        "DxxREQ": "oy7c",
        "GAME_PLATFORM": "Android",
        "Content-Type": "application/octet-stream",
        "X-Unity-Version": "2022.3.62f2"
    }

    print("\nSending request...")

    response = requests.put(
        URL,
        headers=headers,
        data=request_body,
        timeout=30
    )

    print(f"\nHTTP Status: {response.status_code}")
    response.raise_for_status()

    response_data = response.content

    print(f"Response size: {len(response_data)} bytes")

    if len(response_data) < 6:
        raise ValueError("Response is too small to contain a packet header.")

    packet_type = int.from_bytes(response_data[0:2], "little")
    body_length = int.from_bytes(response_data[2:6], "little")

    print(f"Packet Type: {packet_type}")
    print(f"Declared Body Length: {body_length}")
    print(f"Actual Body Length: {len(response_data) - 6}")

    if packet_type != 31010:
        raise ValueError("Unexpected CX response packet type.")

    if body_length != len(response_data) - 6:
        raise ValueError("CX response packet length mismatch.")

    RESPONSE_FILE.write_bytes(response_data)

    print("\nSUCCESS!")
    print(f"Response saved to: {RESPONSE_FILE.name}")


if __name__ == "__main__":
    main()