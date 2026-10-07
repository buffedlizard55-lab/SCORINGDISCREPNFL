"""Validate source-backed data and generate a fully static, accessible Pages site."""
import html
import json
from pathlib import Path
from datetime import date
ROOT = Path(__file__).resolve().parents[1]


def validate(data, sources):
    seen = set()
    for e in data['events']:
        assert e['id'] not in seen
        seen.add(e['id'])
        assert date.fromisoformat(e['correction_date']) >= date.fromisoformat(e['date'])
        assert e['sources'] and all(s in sources for s in e['sources'])
        for c in e['changes']:
            assert c['after'] - c['before'] == c['delta']
            assert c['scope'] and c['evidence']
            assert set(c['evidence']) <= set(e['sources'])
    for s in sources.values():
        assert s['url'].startswith('https://') and s['excerpt']


def build():
    data = json.loads((ROOT/'data/events.json').read_text())
    sources = json.loads((ROOT/'data/sources.json').read_text())
    validate(data, sources)
    esc = html.escape
    cards = []
    for e in sorted(data['events'], key=lambda e:e['date'], reverse=True):
        rows = ''.join(f'<tr><td>{esc(c["subject"])}<br><small>{esc(c["scope"])}</small></td><td>{esc(c["stat"])}</td><td>{c["before"]}</td><td>{c["after"]}</td><td>{c["delta"]:+g}</td></tr>' for c in e['changes'])
        links = ''.join(f'<li><a href="{esc(sources[s]["url"],quote=True)}">{esc(sources[s]["publisher"])}</a> <small>· {esc(sources[s]["tier"])}</small><blockquote>{esc(sources[s]["excerpt"])}</blockquote></li>' for s in e['sources'])
        flags = ''.join(f'<p class="flag">Review note: {esc(f)}</p>' for f in e['flags'])
        cards.append(f'''<article data-kind="{esc(e['kind'])}" id="{e['id']}"><div class="meta">{e['date']} <span>{esc(e['kind'])}</span></div><h3>{esc(e['game'])}</h3><p class="players">{esc(' · '.join(e['players']))}</p><div class="table-wrap"><table><caption>Original → corrected / retained record</caption><thead><tr><th>Subject / scope</th><th>Statistic</th><th>Before</th><th>After</th><th>Δ</th></tr></thead><tbody>{rows}</tbody></table></div><p>{esc(e['impact'])}</p><details><summary>Evidence, timing & review notes</summary><p><b>Reported correction / decision date:</b> {e['correction_date']} — {esc(e['timing_precision'])}.</p><p><b>Reason:</b> {esc(e['reason'])}</p><p>{esc(e['settlement'])}.</p>{flags}<ul class="sources">{links}</ul><p><small>Evidence reviewed {e['reviewed']}. Numerical evidence mappings and derivations are in the JSON download.</small></p></details></article>''')
    dest = ROOT/'research-seed'
    template = (dest/'template.html').read_text()
    rendered = template.replace('<!-- CASES -->','\n'.join(cards))
    # Seed preview is supplemental. Never overwrite the concurrent main site.
    rendered = rendered.replace('href="data/', 'href="../data/').replace('href="docs/', 'href="../docs/').replace('href="README.md"', 'href="../README.md"')
    (dest/'index.html').write_text(rendered)



if __name__ == '__main__':
    build()
