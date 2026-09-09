/// AI 对话控制器 — 占位适配实现（ai_core 已剥离）
library;

import 'package:flutter/foundation.dart';
import 'settings_provider.dart';

/// 占位适配控制器。
///
/// 架构决议：工作台 AI 聊天直连旁路已剥离，模型能力经 M4 知识编译流水线接入。
/// 保留本控制器骨架供已有 UI（如 [AiRecognitionDialog]）安全编译与降级提示。
class AiChatController extends ChangeNotifier {
  bool get isInitialized => false;
  String? get error => null;
  int get refreshKey => 0;

  void onSettingsChanged(SettingsProvider settings) {
    // 旁路已剥离，无需处理设置变更
  }

  Future<String?> recognizeCondition({
    required String naturalLanguage,
    String? currentJson,
  }) async {
    // AI 识别直连旁路已剥离，返回 null
    return null;
  }
}
