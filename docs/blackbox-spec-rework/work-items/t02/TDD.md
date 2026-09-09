# T-02 TDD／文档门禁

## Red baseline

执行前保存以下结果。当前应为：§8.1 标题可能存在，但冻结格式完整性检查失败。

```bash
bash docs/blackbox-spec-rework/verify-T.sh
```

不得因为全局脚本还有其他 T 项失败而扩大范围。

## Green checks

```bash
SPEC=openspec/learn-system-blackbox-architecture.md
for s in 'src_<work>_ed<NN>' 'ss_<work>_ed<NN>_p<NNNN>_s<NN>' 'ku_<technique>_<6位数字>' 'as_<technique>_<6位数字>' 'pr_<technique>_<6位数字>' 'co_shared_<domain>_NN' 'co_<technique>_<6位数字>' 'hg_<4位数字>'; do rg -Fq "$s" "$SPEC" || exit 1; done
for s in 'art_<32hex>' 'rev_<32hex>' 'prun_<32hex>' 'srun_<32hex>' 'pkg_<stage>_<32hex>' 'rel_<32hex>'; do rg -Fq "$s" "$SPEC" || exit 1; done
rg -q 'Schema.*[Vv]ersion.*Revision|Schema 版本.*Revision' "$SPEC"
rg -q '待用户确认|提案' "$SPEC"
rg -q 'uuid\.uuid4\(\)\.hex|UUIDv4' "$SPEC"
rg -q 'StagePackage.*逻辑身份|逻辑身份.*StagePackage' "$SPEC"
rg -q 'm1.*m8|m1`.*`m2`.*`m3`.*`m4`.*`m5`.*`m6`.*`m7`.*`m8' "$SPEC"
! rg -q 'pkg_<stage>_<32hex>.*物理修订|Content Revision.*pkg_<stage>_<32hex>' "$SPEC"
rg -q 'ArtifactRef.*pkg_<stage>_<32hex>.*rev_<32hex>|ArtifactRef.*stage_package_id.*artifact_revision_id' "$SPEC"
git diff --check
```

执行后再次运行全局脚本。T-02b 必须从 FAIL 变为 PASS；其余既有 FAIL 数只能持平或减少，不能增加。

## Manual semantic checks

- 八行冻结格式逐字符对照权威源。
- 每行标注沿用来源；不得伪称所有八行都来自同一个文件。
- `Artifact` 与 `Artifact Revision` 是两种 ID，不得合并。
- 六类新格式显著标为待确认，不进入冻结表。
- 文档明确拒绝 `pr_` 复用于 ProcessingRun。
- `pkg_...` 是 StagePackage 的逻辑身份；每个物理版本另用 `rev_...`。
- `<stage>` 冻结为 `m1` 至 `m8`，能直接生成确定性正则。
- 本任务未产生代码、Schema、fixture 或依赖变更。
