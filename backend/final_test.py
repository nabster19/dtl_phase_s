import urllib.request, json

tests = [
    ('REGISTER NEW USER', 'POST', 'http://localhost:5000/api/auth/register',
     {'name':'Final Test','mobile_number':'9123456781','password':'secure123','role':'patient'}),
    ('LOGIN EXISTING',   'POST', 'http://localhost:5000/api/auth/login',
     {'mobile_number':'7795273421','password':'password123'}),
    ('DUPLICATE BLOCK',  'POST', 'http://localhost:5000/api/auth/register',
     {'name':'Dupe','mobile_number':'7795273421','password':'test123','role':'patient'}),
    ('SHORT PASSWORD',   'POST', 'http://localhost:5000/api/auth/register',
     {'name':'Bad','mobile_number':'9999988877','password':'abc','role':'patient'}),
    ('INVALID MOBILE',   'POST', 'http://localhost:5000/api/auth/register',
     {'name':'Bad','mobile_number':'12345','password':'abc123','role':'patient'}),
    ('WRONG PASSWORD',   'POST', 'http://localhost:5000/api/auth/login',
     {'mobile_number':'7795273421','password':'wrongpassword'}),
]

print("=" * 60)
print("CuraAI Auth System - Final Verification")
print("=" * 60)
for label, method, url, payload in tests:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
          headers={'Content-Type':'application/json'}, method=method)
    try:
        res = urllib.request.urlopen(req)
        body = json.loads(res.read().decode())
        msg = body.get('message','')[:55]
        print(f"  PASS   {label}: {msg}")
    except urllib.error.HTTPError as e:
        body = json.loads(e.read().decode())
        msg = body.get('message','')[:55]
        print(f"  BLOCK  {label}: {msg}")
    except Exception as ex:
        print(f"  ERROR  {label}: {ex}")

print("=" * 60)
print("Done.")
