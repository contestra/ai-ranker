import requests

response = requests.post('http://localhost:8000/api/concordance', 
    json={'brand_name': 'TestBrand', 'vendor': 'openai', 'num_runs': 3})
print(f'Status: {response.status_code}')
if response.status_code != 200:
    print(response.text[:500])
else:
    print('Success!')