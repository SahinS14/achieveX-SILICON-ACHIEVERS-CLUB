"""Vercel entry point; reuse the local API without exposing the local filesystem."""
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import Handler
class handler(Handler):
    def normalize_path(self):
        endpoint=parse_qs(urlparse(self.path).query).get('endpoint',[''])[0]
        if endpoint:self.path='/api/'+endpoint
    def do_GET(self):
        self.normalize_path()
        if not urlparse(self.path).path.startswith('/api/'):
            return self.json_response({'error':'Not found'},404)
        return super().do_GET()
    def mutate(self):
        self.normalize_path()
        return super().mutate()
