// AI 对话页面 — 占位说明页面（ai_core 已剥离）

import 'package:flutter/material.dart';

/// AI 对话页面（占位说明）。
///
/// 架构决议：工作台 AI 聊天直连旁路已剥离，模型能力经 M4 知识编译流水线接入。
class ChatPage extends StatelessWidget {
  const ChatPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI 对话'),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.info_outline,
                color: Colors.deepPurple,
                size: 48,
              ),
              const SizedBox(height: 16),
              Text(
                'AI 对话功能已剥离',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 12),
              const Text(
                '工作台前端直连大模型旁路已移除。\n相关模型能力已收敛至 M4 知识编译流水线。',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey, fontSize: 14, height: 1.5),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
