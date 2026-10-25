#!/usr/bin/env python3
"""Copy the AI prompt into app.js.

tools/ai_prompt.md is the prompt Norbert keeps in his Claude project (document claude/nutrilog-ai-pontosito-prompt.md, "Nutrilog tételpontosító",
since version 16 v3.1). The app has it as one constant, AI_PROMPT, so "Copy AI prompt" works offline. This script rewrites the block between the
two marker comments in app.js:

    python3 -I tools/embed_ai_prompt.py            # from the repo root

The text is copied as it is, including its own list of nutrient keys (section 7). The list deliberately has 63 keys: protein_crude_n_x_6_25 is left out.
tests/test_ai_import.py checks that the constant is the file, that the keys and units of section 7 are those of the app (all but that one key),
that the CIQUAL codes of section 6 exist in ciqual.json, that the JSON example is accepted by the importer and that the confidence words are understood.
When the prompt changes: replace tools/ai_prompt.md, run this script, and run tests/test_ai_import.py. The answer shape is the foods file of
"Import foods (JSON)"; if the shape changes, teach parseFoodsFile / parseAiImport first."""
import pathlib, re, sys

root = pathlib.Path(__file__).resolve().parent.parent
md = (root / 'tools' / 'ai_prompt.md').read_text(encoding='utf-8').replace('\r\n', '\n').rstrip() + '\n'
app_path = root / 'app.js'
app = app_path.read_text(encoding='utf-8')

title = md.splitlines()[0]
if not re.match(r'# Nutrilog tételpontosító \(v\d+(\.\d+)?, végleges\)$', title):
    sys.exit('The first line of tools/ai_prompt.md should be "# Nutrilog tételpontosító (v3.1, végleges)" or a later version: ' + title)
for h in ('## 0. Előfeltétel', '## 6. Referencialista', '## 7. Tápanyagkulcsok', '## 9. Kimenet', '## 10. Ellenőrzés a válasz előtt'):
    if h not in md:
        sys.exit(f'The heading "{h}" is missing in tools/ai_prompt.md: check this script and the test.')


def js(s):
    return s.replace('\\', '\\\\').replace('`', '\\`').replace('${', '\\${')


block = ('/* >>> AI prompt: written by tools/embed_ai_prompt.py from tools/ai_prompt.md. Do not edit by hand. */\n'
         f'const AI_PROMPT = `{js(md)}`;\n'
         '/* <<< AI prompt */')
new, n = re.subn(r'/\* >>> AI prompt.*?/\* <<< AI prompt \*/', lambda _: block, app, count=1, flags=re.S)
if n != 1:
    sys.exit('The marker comments "/* >>> AI prompt" and "/* <<< AI prompt */" were not found in app.js')
app_path.write_text(new, encoding='utf-8')
print('app.js updated:', len(md), 'characters of prompt,', title)
