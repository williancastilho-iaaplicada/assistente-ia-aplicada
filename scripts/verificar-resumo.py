#!/usr/bin/env python3
# 🇧🇷 Confere se o corpo do PR (stdin) tem o resumo de negócio bilíngue e a confirmação toda marcada.
# 🇺🇸 Checks that the PR body (stdin) has the bilingual business summary and a fully checked confirmation.
import re, sys
body = sys.stdin.read()
errors = []
required = [
    "Resumo para o negócio / Business summary",
    "O que este PR aborda", "O que foi feito", "Impacto no projeto",
    "What this PR addresses", "What was done", "Impact on the project",
    "Confirmação antes do merge",
]
for h in required:
    if h not in body:
        errors.append(f"Faltando / Missing: '{h}'")
clean = re.sub(r"<!--.*?-->", "", body, flags=re.S)
for label in ["O que este PR aborda:", "O que foi feito:", "Impacto no projeto:",
              "What this PR addresses:", "What was done:", "Impact on the project:"]:
    m = re.search(re.escape(label) + r"\*{0,2}(.*?)(?=\n\*\*|\n###|\Z)", clean, re.S)
    if not m or len(m.group(1).strip()) < 15:
        errors.append(f"Vazio / Empty: '{label}'")
conf = clean.split("Confirmação antes do merge", 1)
if len(conf) == 2 and re.search(r"- \[ \]", conf[1]):
    errors.append("Há itens de confirmação não marcados / Unchecked confirmation items")
if errors:
    print("\n".join("❌ " + e for e in errors))
    sys.exit(1)
print("✅ Resumo de negócio OK / Business summary OK")
