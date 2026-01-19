"""
Test script to check if authentication logs can be collected
Run this as Administrator to test auth log collection
"""

import platform
import sys

print("Testing Authentication Log Collection")
print("=" * 50)

# Test 1: Check if running as admin
try:
    import ctypes
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    print(f"Running as Administrator: {is_admin}")
    if not is_admin:
        print("WARNING: Not running as admin - auth logs may not be accessible!")
except:
    print("Could not check admin status")

# Test 2: Check if pywin32 is available
print("\n" + "=" * 50)
print("Checking pywin32 availability...")
try:
    import win32evtlog
    import win32security
    import win32api
    print("[OK] pywin32 modules imported successfully")
    WIN32_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] pywin32 not available: {e}")
    print("\nTo install pywin32, run:")
    print("  pip install pywin32")
    WIN32_AVAILABLE = False
    sys.exit(1)

# Test 3: Try to read Security Event Log
print("\n" + "=" * 50)
print("Attempting to read Windows Security Event Log...")
try:
    server = 'localhost'
    logtype = 'Security'

    print(f"Opening event log: {logtype}")
    hand = win32evtlog.OpenEventLog(server, logtype)

    flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

    print("Reading events...")
    events = win32evtlog.ReadEventLog(hand, flags, 0)

    count = 0
    auth_events = []

    # Look for logon events (4624, 4625)
    for event in events:
        if event.EventID in [4624, 4625] and count < 15:
            auth_events.append({
                'event_id': event.EventID,
                'time': event.TimeGenerated.isoformat() if event.TimeGenerated else None,
                'source': event.SourceName,
                'type': 'logon_success' if event.EventID == 4624 else 'logon_failure'
            })
            count += 1

    win32evtlog.CloseEventLog(hand)

    print(f"\n[OK] Successfully collected {len(auth_events)} authentication events")

    if auth_events:
        print("\nRecent authentication events:")
        for i, event in enumerate(auth_events[:5], 1):
            print(f"\n  Event {i}:")
            print(f"    Event ID: {event['event_id']} ({event['type']})")
            print(f"    Time: {event['time']}")
            print(f"    Source: {event['source']}")
    else:
        print("\n[WARNING] No authentication events found!")
        print("This could mean:")
        print("  - No recent logon events (Event IDs 4624, 4625)")
        print("  - Auditing is not enabled for logon events")
        print("  - The Security event log is empty")

except Exception as e:
    print(f"\n[ERROR] Failed to read event log: {e}")
    print("\nPossible causes:")
    print("  1. Not running as Administrator")
    print("  2. Event log service is not running")
    print("  3. Access denied to Security log")
    print("\nTry:")
    print("  - Run this script as Administrator")
    print("  - Check Event Viewer manually (eventvwr.msc)")

print("\n" + "=" * 50)
print("Test complete!")
