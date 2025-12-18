import psutil
import time
import requests
import sys
from datetime import datetime

try:
    from scapy.all import sniff, wrpcap
except ImportError:
    print("Scapy is not installed. Please install it with: pip install scapy")
    print("Note: On Linux, packet capture usually requires root privileges.")
    print("On Windows/macOS, additional setup (Npcap on Windows) may be needed.")
    sys.exit(1)

### Configuration ###
DISCORD_WEBHOOK_URL = "" # Add your Discord Webhook URL here
SERVER_NAME = "AWS, France" # Edit with your hosting provider and server location
PPS_THRESHOLD = 50000 # Change to a number significantly exceeding your server's average packets per second
CHECK_INTERVAL = 1  # Seconds between PPS checks

### Packet Capturing ###
CAPTURE_PACKET_COUNT = 10000  # How many packets you want to capture from the potential (D)DoS attack
CAPTURE_FILENAME_PREFIX = "attack_capture_"  # Saved as .pcap file, e.g., attack_capture_20251218_123456.pcap

def send_discord_alert(pps, capture_file=None):
    embed = {
        "title": "Potential (D)DoS Attack Detected!",
        "fields": [
            {"name": "Server", "value": SERVER_NAME, "inline": False},
            {"name": "Incoming PPS", "value": str(pps), "inline": False}
        ],
        "color": 16711680,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if capture_file:
        embed["description"] = f"A capture of {CAPTURE_PACKET_COUNT} packets has been saved to `{capture_file}` for analysis."
    
    payload = {"embeds": [embed]}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"[!] Potential attack detected, sending alert to Discord! {pps} PPS")
        if capture_file:
            print(f"[+] Captured packets from this potential attack: {capture_file}")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send alert: {e}")

def capture_packets(packet_count):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{CAPTURE_FILENAME_PREFIX}{timestamp}.pcap"
    
    print(f"[-] Starting capture of {packet_count} packets -> {filename}")
    packets = sniff(count=packet_count, store=True)  # Capture all interfaces by default
    wrpcap(filename, packets)
    print(f"[+] Capture complete: {filename}")
    return filename

def main():
    print("[+] Starting server monitor...")
    prev_packets = psutil.net_io_counters().packets_recv
    
    while True:
        time.sleep(CHECK_INTERVAL)
        current_packets = psutil.net_io_counters().packets_recv
        pps = current_packets - prev_packets
        
        if pps > PPS_THRESHOLD:
            print(f"High traffic detected: {pps} PPS")
            send_discord_alert(pps)
            
            import threading
            capture_thread = threading.Thread(target=lambda: send_discord_alert(pps, capture_packets(CAPTURE_PACKET_COUNT)))
            capture_thread.daemon = True
            capture_thread.start()
        
        prev_packets = current_packets

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[-] Monitor stopped.")
        sys.exit(0)
