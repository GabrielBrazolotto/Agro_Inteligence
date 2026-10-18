"""Response completeness from retrieved monthly evidence, independent of LLM grades."""
import re
from decimal import Decimal
from agro_ai.evaluation.reference import answer_numbers


def response_completeness(case, answer, evidence):
    # Explicit golden contract, not a keyword guess about an arbitrary response.
    if 'monthly' not in case.get('checks', []):
        return {'status': 'not_applicable'}
    tables=[]
    def visit(value):
        if isinstance(value, dict):
            if 'mensal' in value:
                tables.append(value['mensal'])
            for key,item in value.items():
                if key!='mensal':
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    for row in evidence:
        visit(row.get('content'))
    if len(tables)!=1 or not isinstance(tables[0],list) or not tables[0]:
        return {'status':'failed','reason':'monthly_evidence_missing_or_ambiguous'}
    rows=tables[0]
    periods=[row.get('mes') for row in rows]
    if (any(not isinstance(p,str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',p) for p in periods)
            or len(set(periods))!=len(periods)
            or any('receita_faturada' not in row for row in rows)):
        return {'status':'failed','reason':'invalid_monthly_evidence'}
    # G04 explicitly asks for the 12 available months. Truncated evidence is not enough.
    if case.get('id')=='G04' and len(periods)!=12:
        return {'status':'failed','reason':'incomplete_monthly_evidence','periods':periods}
    missing=[]
    for row in rows:
        period=row['mes']
        lines=[line for line in answer.splitlines()
               if re.search(r'(?<!\d)'+re.escape(period)+r'(?![-\d])',line)]
        # Exactly one period per result line, with a monetary marker and exact cents.
        valid=[line for line in lines if re.findall(r'\d{4}-(?:0[1-9]|1[0-2])',line)==[period]
               and 'R$' in line and any(abs(n-Decimal(str(row['receita_faturada'])))<Decimal('.005')
                                       for n in answer_numbers(line))]
        if len(lines)!=1 or len(valid)!=1:
            missing.append(period)
    return {'status':'failed' if missing else 'passed',
            'reason':'missing_duplicate_or_inaccurate_monthly_lines' if missing else 'complete_monthly_lines',
            'expected_periods':periods,'missing_or_invalid_periods':missing}
