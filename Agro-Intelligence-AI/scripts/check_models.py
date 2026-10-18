"""Diagnóstico sanitizado: configuração local e uma prova mínima opt-in."""
import argparse
import hashlib
import json
import re
from types import SimpleNamespace
from google import genai
from google.genai import types
from pydantic import BaseModel

from agro_ai.config import ROOT,get_settings
from agro_ai.diagnostics import configure_logging
from agro_ai.api_limits import request_slot,limit_evidence
from agro_ai.observability import error_metadata
from agro_ai.rag import split_text


class Probe(BaseModel):
    ok: bool


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe',action='store_true',help='Uma geração mínima no modelo dos agentes, se listado. Consome cota.')
    args=parser.parse_args()
    configure_logging()
    s=get_settings()
    report={'configured':{'main':s.model,'agents':s.agent_model or s.model,
                         'judge':s.judge_model or s.agent_model or s.model,'embedding':s.embedding_model,
                         'min_interval_seconds':s.request_interval_seconds},
            'key_present':bool(s.api_key),'generation_calls':0}
    chunks=[]
    for path in sorted(s.documents.glob('*.md')):
        for number,chunk in enumerate(split_text(path.read_text(encoding='utf-8'))):
            chunks.append((f'{path.name}:{number}',chunk,{'source':path.name,'chunk':number+1}))
    name='comercial-'+hashlib.sha256(json.dumps([s.embedding_model,768,chunks],ensure_ascii=False).encode()).hexdigest()[:24]
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    client=chromadb.PersistentClient(path=str(s.chroma_dir),settings=ChromaSettings(anonymized_telemetry=False))
    existing={row.name for row in client.list_collections()}
    report['chroma']={'expected_collection':name,'existing':name in existing,'embedding_model':s.embedding_model}
    if name in existing:
        collection=client.get_collection(name,embedding_function=None)
        embeddings=collection.get(limit=1,include=['embeddings'])['embeddings']
        report['chroma'].update(count=collection.count(),dimensions=len(embeddings[0]) if embeddings is not None and len(embeddings) else None)
    if args.probe and s.api_key:
        model=s.agent_model or s.model
        listed=json.loads((ROOT/'reports/models/available.json').read_text(encoding='utf-8'))['models']
        if not any(row['name']=='models/'+model and 'generateContent' in row['supported_actions'] for row in listed):
            report['probe']={'status':'not_executed','reason':'model_not_listed_for_key'}
        else:
            api=genai.Client(api_key=s.api_key,vertexai=False,http_options=types.HttpOptions(
                timeout=30000,retry_options=types.HttpRetryOptions(attempts=1)))
            try:
                with request_slot(s,model):
                    report['generation_calls']=1
                    text=''
                    for chunk in api.models.generate_content_stream(model=model,contents='Retorne ok=true.',
                        config=types.GenerateContentConfig(response_mime_type='application/json',response_schema=Probe,max_output_tokens=128,temperature=0)):
                        text+=chunk.text or ''
                        version=getattr(chunk,'model_version',None)
                        if isinstance(version,str) and re.fullmatch(r'gemini-[a-z0-9.-]+',version):
                            report['response_model_version']=version
                    report['probe']={'status':'success','structured_json_valid':Probe.model_validate_json(text).ok}
            except Exception as error:
                report['probe']={'status':'failed',**error_metadata(error),**limit_evidence(error)}
            finally:
                api.close()
    path=ROOT/'reports/models/configuration.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
