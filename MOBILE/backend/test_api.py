import time
import requests

time.sleep(4)
print('Testing API...')

# Test alerts endpoint
r = requests.get('http://127.0.0.1:8000/alerts')
print(f'Alerts Status: {r.status_code}')
if r.status_code == 200:
    data = r.json()
    print(f'Alerts count: {len(data["alerts"])}')
    if data["alerts"]:
        print(f'Sample alert: {data["alerts"][0]}')
    else:
        print('No alerts found')
else:
    print(f'Error: {r.text[:200]}')

print()

# Test stats endpoint
r2 = requests.get('http://127.0.0.1:8000/stats')
print(f'Stats Status: {r2.status_code}')
if r2.status_code == 200:
    print(f'Stats Response: {r2.json()}')
else:
    print(f'Error: {r2.text[:200]}')
