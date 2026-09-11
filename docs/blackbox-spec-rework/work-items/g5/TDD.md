# TDD：G5 文档级状态翻转

`export LC_ALL=en_US.UTF-8`；`S=openspec/learn-system-blackbox-architecture.md`。

| 判据 | Red（改前） | Green（改后） |
|---|---|---|
| `sed -n '3p' $S \| grep -c 'R1_REWORK_CLOSED'` | 0 | 1 |
| `grep -c 'REVIEW_FAILED_R1' $S` | 1 | 0 |
| `grep -c '^状态：' $S` | 19 | 19 |
| `grep -c '^状态：最终规范' $S` | 0 | 0 |
| `git diff <base> --numstat -- $S \| cut -f1,2` | — | `5 4` |
| `git diff <base> --numstat -- docs/blackbox-spec-rework/README.md \| cut -f1,2` | — | `1 1` |
| `bash docs/blackbox-spec-rework/verify-T.sh \| tail -1` | FAIL 合计: 0 | FAIL 合计: 0 |
| `bash docs/blackbox-spec-rework/work-items/g3-r3/mutations.sh all \| tail -1` | 109/109 | 109/109 |
| `bash openspec/schemas/verify.sh >/dev/null; echo $?` | 0 | 0 |
