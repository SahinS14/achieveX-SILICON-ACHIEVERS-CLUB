"""Durable, private cloud sessions and atomic login-attempt slots."""
import hashlib,hmac,json,time,secrets
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError

def request(url,key,path,method='GET',body=None):
    headers={'apikey':key,'Content-Type':'application/json'}
    if key.startswith('eyJ'):headers['Authorization']='Bearer '+key
    try:
        with urlopen(Request(url+'/storage/v1/object/achievex-config/security/'+path,headers=headers,method=method,data=json.dumps(body).encode() if body is not None else None),timeout=15) as r:
            raw=r.read();return json.loads(raw) if raw else {}
    except HTTPError as e:
        try:detail=json.loads(e.read())
        except ValueError:detail={}
        code=str(detail.get('statusCode',e.code))
        if code=='404':return None
        if method=='POST' and (code=='409' or detail.get('error')=='Duplicate'):return False
        raise RuntimeError('Admin security storage unavailable. Check the private achievex-config bucket.') from e
    except (URLError,TimeoutError) as e:raise RuntimeError('Admin security storage unavailable.') from e

def digest(secret,value):return hmac.new(secret.encode(),value.encode(),hashlib.sha256).hexdigest()
def allow_attempt(url,key,secret,ip,now=None):
    # Object creation is atomic: at most six attempts per IP per fixed ten-minute window.
    window=int((time.time() if now is None else now)//600)
    prefix='attempts/'+digest(secret,ip)+'/'+str(window)+'/'
    for slot in range(6):
        if request(url,key,prefix+str(slot)+'.json','POST',{'attempt':secrets.token_hex(8)}) is not False:return True
    return False

def session(url,key,secret,token,action='read',expires=None):
    path='sessions/'+digest(secret,token)+'.json'
    if action=='create':return request(url,key,path,'POST',{'expires':expires})
    if action=='revoke':return request(url,key,path,'PUT',{'expires':0})
    record=request(url,key,path)
    return bool(record and record.get('expires',0)>time.time())
