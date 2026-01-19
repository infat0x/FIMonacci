# Running FIMonacci Client as Administrator

## Why Administrator Access is Required

The FIMonacci client needs Administrator privileges to:
- **Read Windows Security Event Log** - Authentication logs (Event IDs 4624, 4625)
- **Access file ownership information** - Get file owner details
- **Read protected system files** - Monitor system-level changes

Without Administrator access, the client will still work but:
- ❌ No authentication logs will be collected
- ❌ Limited file ownership information
- ⚠️ Some system files may not be accessible

## How to Run as Administrator

### Option 1: Run the Executable as Admin (Recommended)

1. Navigate to `client/dist/` folder
2. **Right-click** on `FIMonacci_Agent.exe`
3. Select **"Run as administrator"**
4. Click **Yes** when Windows asks for permission

### Option 2: Run Python Script as Admin

1. Open Command Prompt **as Administrator**:
   - Press `Win + X`
   - Select "Command Prompt (Admin)" or "Windows PowerShell (Admin)"
   - Or search for "cmd", right-click, and select "Run as administrator"

2. Navigate to the client folder:
   ```cmd
   cd C:\Users\orxan\OneDrive\Desktop\FIMonacci-main\client
   ```

3. Run the Python script:
   ```cmd
   python client.py
   ```

### Option 3: Create Admin Shortcut (Permanent)

1. Right-click on `FIMonacci_Agent.exe` → Create shortcut
2. Right-click the shortcut → **Properties**
3. Go to **Compatibility** tab
4. Check ✅ **"Run this program as an administrator"**
5. Click **OK**
6. Use this shortcut to always run as admin

## Verifying Administrator Access

When you run the client, you should see:
```
[OK] Collected X authentication log entries
```

If you see:
```
[WARNING] Cannot collect auth logs: Not running as Administrator
```

Then the client is **NOT** running with admin privileges.

## Testing Auth Log Collection

You can test if auth logs are accessible by running:
```cmd
python scripts/testing/test_auth_logs.py
```

This script will tell you:
- ✅ If you're running as Administrator
- ✅ If pywin32 is installed
- ✅ If auth logs can be read
- ✅ Show sample authentication events

## Important Notes

1. **Always rebuild after code changes** - If you modify `client.py`, rebuild with `build.bat`
2. **UAC Prompt** - Windows will show a User Account Control prompt - click "Yes"
3. **Antivirus** - Some antivirus software may block the client - add it to exceptions
4. **Logs are only collected for file events** - Auth logs are attached to created/modified/deleted file events, not collected separately

## Troubleshooting

### "No authentication logs collected" message

**Cause:** Not running as Administrator

**Fix:** Use one of the methods above to run as admin

### Event log error 1314

**Full error:** `(1314, 'OpenEventLogW', 'A required privilege is not held by the client.')`

**Cause:** No admin privileges

**Fix:** Run as Administrator

### No logon events found

**Possible causes:**
1. No recent logon events (Event IDs 4624, 4625) in Windows
2. Auditing is not enabled for logon events
3. The Security event log is empty or was recently cleared

**Check manually:**
1. Press `Win + R`
2. Type `eventvwr.msc` and press Enter
3. Go to **Windows Logs → Security**
4. Look for Event IDs 4624 (successful logon) and 4625 (failed logon)

If you don't see these events in Event Viewer, then Windows is not logging them, and the FIMonacci client won't be able to collect them either.
