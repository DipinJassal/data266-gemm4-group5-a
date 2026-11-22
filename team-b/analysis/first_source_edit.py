"""Tool calls and minutes before the first source edit (not tests, not scratch scripts) in the smoke traces.
Run from the repo root: python team-b/analysis/first_source_edit.py
"""
import json,glob,re,os,statistics as S,sys
fn_re=re.compile(r"'function_name': '(\w+)'")
path_re=re.compile(r"'(?:filepath|path|file_path)': '([^']*)'")
el_re=re.compile(r"'elapsed_s': ([0-9.]+)")
scratch=re.compile(r'(^|/)(repro|reproduce|test_|debug|scratch|tmp|check|verify)[^/]*\.py$|^/tmp/|(^|/)tests?/|conftest')
runs={'graph-localize':'20261121T074543Z','graph-expand-2':'20261121T084309Z'}
summary={}
for v,ts in runs.items():
    hr={json.loads(l)['instance_id']:json.loads(l) for l in open(glob.glob(f'harness/runs/team-b-variants-{v}/smoke/{ts}/results/*/smoke/harness_results.jsonl')[0],encoding='utf-8')}
    rows=[]
    for f in sorted(glob.glob(f'harness/runs/team-b-variants-{v}/smoke/{ts}/**/trace_*.json',recursive=True)):
        iid=os.path.basename(f)[6:-5]
        n=0; fsrc=None; tsrc=None; feds=[]
        for st in json.load(open(f,encoding='utf-8'))['steps']:
            s=str(st.get('tool_calls') or '')
            ms=list(fn_re.finditer(s))
            for i,m in enumerate(ms):
                seg=s[m.end(): ms[i+1].start() if i+1<len(ms) else len(s)]
                if m.group(1) in('edit_file','write_file'):
                    pm=path_re.search(seg); p=re.sub(r'^/?workspace/','',(pm.group(1) if pm else '?')).strip('./ `「」"')
                    feds.append(p)
                    if fsrc is None and not scratch.search(p):
                        fsrc=n; e=el_re.search(seg); tsrc=float(e.group(1))/60 if e else None
                n+=1
        rows.append((iid,hr[iid]['tool_calls'],fsrc,None if tsrc is None else round(tsrc,1),sorted(set(feds))))
    print(v)
    for r in rows: print('  ',r)
    src=[r[2] for r in rows if r[2] is not None]; t=[r[3] for r in rows if r[3] is not None]
    print(f'  -> source edit in {len(src)}/{len(rows)}; median calls before {S.median(src)}; median min {round(S.median(t),1)}; median calls total {S.median([r[1] for r in rows])}')
