import jwt, datetime, requests
import os
SECRET = 'super-secret-key-change-in-production'
token = jwt.encode({'user_id': 2, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, SECRET, algorithm='HS256')
res = requests.post('http://127.0.0.1:5000/api/chat', json={'message': 'I have a headache'}, headers={'Authorization': f'Bearer {token}'})
print(res.status_code)
print(res.text)
