import importlib.util
import json
import os
from pathlib import Path
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

spec=importlib.util.spec_from_file_location('signalforge_server',Path(__file__).resolve().parents[1]/'server.py')
s=importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

class ResearchTests(unittest.TestCase):
    def test_pipeline_preserves_citations_and_limits_search_stages(self):
        calls=[]
        def fake(payload):
            calls.append(payload)
            return {'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'A finding [1]','annotations':[{'type':'url_citation','start_index':10,'end_index':13,'url':'https://example.com','title':'Source'}]}]}]}
        result=s.run_research('Investigate a company',fake)
        self.assertEqual(len(result['stages']),3)
        self.assertEqual(len(calls),3)
        self.assertIn('tools',calls[0]);self.assertIn('tools',calls[1]);self.assertNotIn('tools',calls[2])
        self.assertIn('https://example.com',calls[2]['input'])
        self.assertTrue(all(x['store'] is False for x in calls))
    def test_incomplete_research_is_not_reported_as_success(self):
        with self.assertRaises(ValueError):s.run_research('A question',lambda _: {'status':'incomplete','output':[]})
    def test_refusal_does_not_become_empty_success(self):
        with self.assertRaises(ValueError):s.run_research('A question',lambda _: {'status':'completed','output':[]})

class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=s.ThreadingHTTPServer(('127.0.0.1',0),s.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def call(self,path,body=None,headers=None):
        req=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers or {})
        try:
            with urlopen(req) as r:return r.status,r.read()
        except HTTPError as e:return e.code,e.read()
    def test_static_allowlist_blocks_secret_and_traversal_paths(self):
        for path in ['/server.py','/.env','/../README.md','/tests/test_server.py']:
            self.assertEqual(self.call(path)[0],404)
    def test_static_assets_and_config(self):
        self.assertEqual(self.call('/')[0],200)
        code,body=self.call('/api/config');self.assertEqual(code,200);self.assertIn('token',json.loads(body));self.assertNotIn('OPENAI_API_KEY',body.decode())
    def test_dns_rebinding_host_rejected(self):self.assertEqual(self.call('/api/config',headers={'Host':'attacker.example'})[0],403)
    def test_post_requires_session_token(self):self.assertEqual(self.call('/api/research',{'question':'An investigation'})[0],403)
    def test_cross_origin_post_rejected_even_with_token(self):self.assertEqual(self.call('/api/research',{'question':'An investigation'},{'X-SignalForge-Token':s.TOKEN,'Origin':'https://attacker.example'})[0],403)
    @patch.dict(os.environ,{'OPENAI_API_KEY':'test-placeholder','OPENAI_MODEL':'test-model'})
    def test_invalid_request_and_mock_success(self):
        headers={'X-SignalForge-Token':s.TOKEN}
        self.assertEqual(self.call('/api/research',{'question':'short'},headers)[0],400)
        with patch.object(s,'run_research',return_value={'stages':[]}) as run:
            self.assertEqual(self.call('/api/research',{'question':'Research this company'},headers)[0],200)
            run.assert_called_once_with('Research this company')

if __name__=='__main__':unittest.main()
