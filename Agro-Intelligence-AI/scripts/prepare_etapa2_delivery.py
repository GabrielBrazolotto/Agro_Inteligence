"""Offline evidence consolidation. Never generates answers or calls any API."""
import csv
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import statistics

from dotenv import dotenv_values
from agro_ai.config import ROOT,get_settings
from agro_ai.evaluation.batches import golden
from agro_ai.evaluation.cache import EvaluationCache,reference_state,file_digest
from agro_ai.evaluation.reference import check_finances

OUT=ROOT/'entrega/etapa2'
NOTES={
 'G01':'Receita exata; juiz penalizou aviso operacional (2/3 relevantes).',
 'G02':'60 posições com disponível zero; separadas da insuficiência com saldo.',
 'G03':'60 posições em excesso. Relevancy igual a 0,8, não abaixo.',
 'G04':'Fallback corrigido contém 12 meses; documentos adicionais reduziram Relevancy (14/44). Zero histórico preservado.',
 'G05':'Margem regional ponderada por receita, somente itens faturados.',
 'G06':'Novo julgamento válido após inconsistência anterior; Relevancy anterior preservada.',
 'G07':'Desconto de 7% exige gerente comercial, conforme documento recuperado.',
 'G08':'Pagamento à vista: 2%, sem acumular outros descontos.',
 'G09':'9% não autorizado pela política, mesmo com aprovação gerencial.',
 'G10':'Síntese concluída com aviso do timeout de análise de estoque; carteira em ruptura conferida.',
 'G11':'Fallback após HTTP 503; carteira correta, mas só 2/33 linhas relevantes.',
 'G12':'Inferência scikit-learn local com sete entradas explícitas; score não calibrado.',
 'G13':'Segunda inferência local; não é validação adicional de generalização do ML.',
 'G14':'Tarefa composta de ML e análise comercial, sem mapear atributos automaticamente de SKU.',
 'G15':'14/15 fatos sustentados; aviso de indisponibilidade sem suporte nos snippets. Relevancy preservada.'}


def aggregate(rows):
    result={}
    for name in ('faithfulness','answer_relevancy'):
        metrics=[row['metrics'][name] for row in rows]
        if any(m.get('status')!='evaluated' or type(m.get('score')) not in (float,int)
               or not math.isfinite(m['score']) or not 0<=m['score']<=1 for m in metrics):
            raise ValueError('all_metrics_must_be_evaluated_with_real_finite_scores')
        scores=[m['score'] for m in metrics]
        result[name]={'count':len(scores),'mean':statistics.mean(scores),
            'threshold':.8,'below_threshold':[r['id'] for r in rows if r['metrics'][name]['score']<.8],
            'below_threshold_count':sum(s<.8 for s in scores)}
    return result


def collect():
    settings=get_settings();cache=EvaluationCache();state=reference_state(settings)
    cases=golden()[:15]
    if [c['id'] for c in cases]!=[f'G{i:02d}' for i in range(1,16)]:
        raise ValueError('unexpected_golden_case_ids')
    result=[];sources={}
    for case in cases:
        response=cache.response(case,state)
        if response is None:
            raise ValueError('validated_response_missing')
        metrics={};origins={};judgments={}
        for name in ('faithfulness','answer_relevancy'):
            record=cache.metric(response,name)
            if record is None:
                raise ValueError('metric_missing')
            metrics[name]=record['metric']
            path=Path(record['origin']['report']).resolve()
            if not path.is_relative_to(ROOT.resolve()) or path.suffix!='.json':
                raise ValueError('unexpected_source_report_path')
            source=json.loads(path.read_text(encoding='utf-8'))
            original=next(r for r in source['results'] if r['id']==case['id'])
            if (original['question']!=case['question'] or original['answer']!=response['answer']
                    or original['metrics'][name]['status']!='evaluated'
                    or original['metrics'][name]['score']!=metrics[name]['score']):
                raise ValueError('cache_does_not_match_original_report')
            relative=path.relative_to(ROOT).as_posix();sha=file_digest(path)
            sources[relative]=sha
            origins[name]={'report':relative,'sha256':sha,
                'protocol':metrics[name].get('protocol',record['protocol'])}
            a=record['assessment'];legacy=a.get('judgment',{})
            judgments[name]=(a.get('faithfulness_judgment',{'claims':legacy.get('claims',[])}) if name=='faithfulness'
                              else a.get('relevancy_judgment',{'relevance_units':legacy.get('relevance_units',[])}))
        for path in [cache.directory/'responses'/case['id']/(response['key']+'.json'),
                     *[(cache.directory/'metrics'/response['key']/(name+'.json')) for name in metrics]]:
            sources[path.relative_to(ROOT).as_posix()]=file_digest(path)
        result.append({'id':case['id'],'question':case['question'],'category':case['category'],
            'metrics':metrics,'deterministic_current_duckdb':check_finances(settings.database,case['checks'],response['answer']),
            'observation':NOTES[case['id']],'response_key':response['key'],'original_answer':response['answer'],
            'retrieved_evidence':response['evidence'],'tools':response['tools'],
            'metric_sources':origins,'saved_judgments':judgments})
    return {'generated_at':datetime.now(ZoneInfo('America/Sao_Paulo')).isoformat(),
        'mode':'offline_consolidation','new_api_calls':0,'cases':result,'summary':aggregate(result),
        'reference_state':state,'historical_source_hashes':sources}


def security_scan():
    """Report paths/types only; never include matched credential text."""
    sensitive=[]
    for filename in ('.env','.env.local'):
        path=ROOT/filename
        if path.exists():
            sensitive.extend(value for key,value in dotenv_values(path).items() if value and
                any(marker in key.upper() for marker in ('KEY','SECRET','TOKEN','PASSWORD')))
    excluded={'.venv','.git','__pycache__','.pytest_cache','.agents','.codex','raw','runtime','backups'}
    suffixes={'.py','.md','.json','.txt','.toml','.yaml','.yml','.csv','.ini','.cfg','.example'}
    findings=[];count=0
    for path in ROOT.rglob('*'):
        relative=path.relative_to(ROOT)
        if not path.is_file() or any(part in excluded for part in relative.parts):continue
        if path.name.startswith('.env') and path.name!='.env.example':continue
        if path.suffix.lower() not in suffixes and path.name!='.gitignore':continue
        if path.stat().st_size>15_000_000:continue
        try:content=path.read_text(encoding='utf-8')
        except (UnicodeError,OSError):continue
        count+=1;kinds=[]
        if any(value in content for value in sensitive):kinds.append('configured_secret_literal')
        if re.search(r'AIza[0-9A-Za-z_-]{30,}|(?:sk|pk)-lf-[0-9a-f-]{25,}',content):kinds.append('credential_pattern')
        if kinds:findings.append({'path':relative.as_posix(),'types':kinds})
    example=ROOT/'.env.example'
    invalid=[key for key,value in dotenv_values(example).items() if value and
             any(m in key.upper() for m in ('KEY','SECRET','TOKEN','PASSWORD'))] if example.exists() else []
    return {'text_files_scanned':count,'findings':findings,'env_example_nonempty_sensitive_names':invalid,
        'local_env_present':(ROOT/'.env').exists(),'git_history_available':(ROOT/'.git').exists(),
        'scope_note':'Current text files up to 15 MB, excluding secrets/env, runtime, venv, raw data and backups. Binary images and unavailable Git history are not audited.',
        'exclude_from_repository_or_zip':['.env','.env.* (except sanitized .env.example)',
            '.venv/','data/runtime/','data/ml/raw/','data/backups/','*.log','.git/','reports/ml/split_assignments.csv'],
        'archive_created':False}


def write_summary(evidence):
    rows=evidence['cases'];summary=evidence['summary']
    checks=[c for r in rows for c in r['deterministic_current_duckdb']]
    lines=['# Evidência técnica complementar — G01 a G15','',
        f"Consolidação offline em {evidence['generated_at']}. Novas chamadas à API: zero.",
        'Validação: 15 casos, 30 métricas com status evaluated e correspondência com os relatórios originais.','',
        '| ID | Pergunta original | Categoria | Faithfulness | Answer Relevancy | Determinístico DuckDB | Observações |',
        '|---|---|---|---:|---:|---|---|']
    for row in rows:
        det='; '.join(c['check']+': '+c['status'] for c in row['deterministic_current_duckdb']) or 'Não aplicável'
        lines.append(f"| {row['id']} | {row['question']} | {row['category']} | {row['metrics']['faithfulness']['score']:.6f} | {row['metrics']['answer_relevancy']['score']:.6f} | {det} | {row['observation']} |")
    lines+=['','## Agregações','',
        '| Métrica | Casos | Média não ponderada | Abaixo de 0,8 | IDs |','|---|---:|---:|---:|---|']
    for name,m in summary.items():
        lines.append(f"| {name} | {m['count']} | {m['mean']:.9f} | {m['below_threshold_count']} | {', '.join(m['below_threshold']) or 'Nenhum'} |")
    lines+=['',f"Oráculo DuckDB reexecutado localmente: {sum(c['status']=='passed' for c in checks)}/{len(checks)} verificações aprovadas.",
        'Sete casos não têm verificação financeira configurada; isso não significa reprovação nem aprovação determinística.',
        'O limite usa comparação estrita (<0,8): G03=0,8 não entra na contagem. Doze casos têm ambas as notas ≥0,8.',
        'Não confundir status evaluated (julgamento válido) com nota acima do limite. Notas baixas foram preservadas.',
        'Protocolos históricos diferem em segmentação (ver fonte por métrica); médias descritivas não constituem comparação controlada entre protocolos.',
        'G16–G18 não compõem esta amostra de 15. Não se conclui desempenho em perguntas ambíguas/fora de escopo a partir destes resultados.','',
        '## Origem por métrica','',
        '| Caso | Fonte Faithfulness | Fonte Answer Relevancy |','|---|---|---|']
    for row in rows:
        lines.append(f"| {row['id']} | `{row['metric_sources']['faithfulness']['report']}` | `{row['metric_sources']['answer_relevancy']['report']}` |")
    lines+=['','As respostas completas, contextos recuperados, ferramentas, vereditos, fontes e hashes estão em `evidencias-avaliacoes.json`.',
        'O CSV contém os valores numéricos sem arredondar para exibição. Não houve treino, inferência adicional nem julgamento novo nesta consolidação.']
    (OUT/'resumo-tecnico-avaliacoes.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    with (OUT/'avaliacoes-g01-g15.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=['id','pergunta','categoria','faithfulness','answer_relevancy','deterministico','observacoes'])
        writer.writeheader()
        for row in rows:
            writer.writerow({'id':row['id'],'pergunta':row['question'],'categoria':row['category'],
                'faithfulness':row['metrics']['faithfulness']['score'],'answer_relevancy':row['metrics']['answer_relevancy']['score'],
                'deterministico':'; '.join(c['check']+':'+c['status'] for c in row['deterministic_current_duckdb']) or 'nao_aplicavel',
                'observacoes':row['observation']})


def main():
    evidence=collect();OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'imagens').mkdir(exist_ok=True)
    shutil.copyfile(ROOT/'reports/ml/confusion_matrix.png',OUT/'imagens/matriz-confusao-backorder.png')
    (OUT/'evidencias-avaliacoes.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    write_summary(evidence)
    meta=json.loads((ROOT/'models/backorder/metadata.json').read_text(encoding='utf-8'))
    if file_digest(ROOT/'models/backorder/model.joblib')!=meta['artifact_sha256']:
        raise ValueError('model_artifact_hash_mismatch')
    (OUT/'evidencias-ml.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    scan=security_scan()
    (OUT/'verificacao-seguranca.json').write_text(json.dumps(scan,ensure_ascii=False,indent=2),encoding='utf-8')
    for path,sha in evidence['historical_source_hashes'].items():
        if file_digest(ROOT/path)!=sha:raise ValueError('historical_source_modified')
    words=len(re.findall(r'\S+',(OUT/'relatorio-academico.md').read_text(encoding='utf-8')))
    if not 700<=words<=1500:raise ValueError('academic_word_count_out_of_range')
    check={'case_count':len(evidence['cases']),'evaluated_metric_count':30,'summary':evidence['summary'],
        'word_count':words,'word_count_method':'non-whitespace tokens, including headings/captions and Markdown tokens',
        'new_api_calls':0,'source_files_verified_unchanged':len(evidence['historical_source_hashes']),
        'missing_required_images':['imagens/langfuse-cinco-traces.png','imagens/langfuse-execucao-detalhada.png'],
        'security_scan_findings_count':len(scan['findings'])}
    (OUT/'validacao-entrega.json').write_text(json.dumps(check,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(check,ensure_ascii=True))


if __name__=='__main__':
    main()
