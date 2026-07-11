# HANDOFF

更新时间：2026-07-11
当前分支/worktree：`codex/docs/knowledge-compilation`；独立仓库 `/Users/jingtaiwei/Git/Public/xuan-migration/learn_system`
刚完成：复审并修订 `docs/superpowers/specs/2026-07-11-tag-style-system-design.md`，补齐 Capability Registry、坐标、Host Geometry、生命周期、信任边界、编辑器恢复、安全与 OpenSpec 拆分。
进行到一半的事（精确到文件和章节）：Tag Style 规格已完成第二轮自洽修订，等待用户书面确认；尚未建立 OpenSpec change 或实施计划。
下一步（第一件事）：请用户确认修订稿，再创建六项 OpenSpec capability 并用 writing-plans 编写实施计划。
已知的坑：Marketplace 权威状态不得信任用户 manifest；运行包必须 self-contained；大补丁按错误章节顺序匹配会整体失败，应按小节分批 apply_patch；工作区另有大量既有未跟踪文件，本次提交不得误纳入。
