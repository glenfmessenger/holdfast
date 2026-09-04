# Reproducing Holdfast from scratch

```sh
uv venv .venv --python 3.13 && uv pip install -e ".[dev]" --python .venv/bin/python
git clone https://github.com/django/django.git .targets/django            # targets are gitignored, never vendored
git clone https://github.com/openssh/openssh-portable.git .targets/openssh-portable
uv python install 3.9 3.11                                                 # old Django does not import on 3.13
uv venv .targets/venv39 --python 3.9  && uv pip install --python .targets/venv39/bin/python asgiref pytz sqlparse
uv venv .targets/venv311 --python 3.11 && uv pip install --python .targets/venv311/bin/python asgiref sqlparse

export ANTHROPIC_API_KEY=sk-ant-...        # tier 4. Without it: tier 4 is recorded as "not attempted: no-api-key",
                                            # properties are templates, and inconclusive walks end UNVERIFIABLE.
.venv/bin/holdfast create --repo .targets/django --fix d4d800ca1a --advisory CVE-2021-28658
.venv/bin/holdfast walk   --contract CVE-2021-28658 --repo .targets/django --range d4d800ca1a..8d9901c961
.venv/bin/holdfast report                   # -> results/report.md
.venv/bin/holdfast eval --labels results/labels.json   # -> results/eval.md
./scripts/create_all.sh && ./scripts/walk_all.sh       # everything in contracts/targets.json
```

`--model` overrides `claude-sonnet-5`; tier 4 is capped at 150 logged calls per run, then UNVERIFIABLE ("budget").
