# R0 依赖解锁 TDD 门禁与验证

## 1. Red Baseline（执行前保存）

执行前必须运行并保存以下基线：

```bash
# 1. 记录内网依赖当前存在
grep -c '192.168' pattern_knowledge_workbench/pubspec.yaml
# 期望当前为 3（enumeration 1 处，ai_core 2 处）

# 2. 记录 ai_core 当前导入存在
grep -rc 'package:ai_core' pattern_knowledge_workbench/lib/ | grep -v ':0' | wc -l
# 期望当前为 3（chat_page, ai_chat_controller, rule_list_page）

# 3. 记录当前 pub get 失败
cd pattern_knowledge_workbench && flutter pub get
# 期望当前以退出码 1 失败（version solving failed）
```

## 2. ACT 01 门禁检查（enumeration 删除后）

```bash
# 1. 确认全仓 *.dart 零引用
test $(grep -rn 'enumeration' --include='*.dart' pattern_knowledge_workbench/ | grep -v '^pattern_knowledge_workbench/build/' | wc -l) -eq 0

# 2. 确认 pubspec 已无 enumeration
test $(grep -c 'enumeration.git' pattern_knowledge_workbench/pubspec.yaml) -eq 0

# 3. 确认 192.168 仅剩 ai_core 两处
test $(grep -c '192.168' pattern_knowledge_workbench/pubspec.yaml) -eq 2

# 4. 代码格式合规
git diff --check
```

## 3. ACT 02 门禁检查（ai_core 剥离后）

```bash
# 1. 确认 192.168 彻底归零
test $(grep -c '192.168' pattern_knowledge_workbench/pubspec.yaml) -eq 0

# 2. 确认源码中无任何 package:ai_core 引用
test $(grep -rc 'package:ai_core' pattern_knowledge_workbench/lib/ | grep -v ':0' | wc -l) -eq 0

# 3. 运行依赖更新，必须退出 0
cd pattern_knowledge_workbench && flutter pub get

# 4. 运行静态代码分析，必须退出 0
cd pattern_knowledge_workbench && flutter analyze --no-fatal-infos

# 5. 运行测试，必须退出 0
cd pattern_knowledge_workbench && flutter test

# 6. 代码格式合规
git diff --check
```

## 4. 全局回归门禁

```bash
bash docs/blackbox-spec-rework/verify-T.sh
# 退出码保持 17，无任何既有项退化
```

## 5. 防假绿审查

- 严禁通过把 `192.168.0.165` 替换为其他私有 IP 或本地 path 绕过 `grep` 检查；
- 严禁引入虚构的 mock 包到 pubspec.yaml；
- 必须通过真实的 `flutter pub get` 与 `flutter analyze` 验证代码完整性。
