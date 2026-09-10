import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:drift/drift.dart' hide isNull, isNotNull;
import 'package:drift/native.dart';
import 'package:companion_system/database/drift_database.dart';
import 'package:companion_system/providers/rule_provider.dart';
import 'package:companion_system/providers/settings_provider.dart';
import 'package:companion_system/providers/ai_chat_controller.dart';
import 'package:companion_system/pages/rule_list_page.dart';

class FakeAiChatController extends AiChatController {
  @override
  bool get isInitialized => true;

  @override
  Future<String?> recognizeCondition({
    required String naturalLanguage,
    String? currentJson,
  }) async {
    return '{"type":"ai_condition"}';
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
  });

  Widget createTestWidget({
    required AppDatabase db,
    required RuleProvider ruleProvider,
    required SettingsProvider settingsProvider,
    required AiChatController aiChatController,
  }) {
    return MultiProvider(
      providers: [
        Provider<AppDatabase>.value(value: db),
        ChangeNotifierProvider<RuleProvider>.value(value: ruleProvider),
        ChangeNotifierProvider<SettingsProvider>.value(value: settingsProvider),
        ChangeNotifierProvider<AiChatController>.value(value: aiChatController),
      ],
      child: const MaterialApp(
        home: RuleListPage(),
      ),
    );
  }

  testWidgets('用例 1：未核验规则经人工编辑保存后，isVerified 依然保持 false (B1)',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(2600, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    final db = AppDatabase(NativeDatabase.memory());
    addTearDown(() => db.close());

    await db.delete(db.geJuRules).go();
    await db.delete(db.geJuPatterns).go();
    await db.delete(db.geJuSchools).go();

    await db.into(db.geJuSchools).insert(
      GeJuSchoolsCompanion.insert(
        id: 's1',
        name: '测试流派',
        type: 'school',
        createdAt: DateTime.now(),
      ),
    );
    await db.into(db.geJuPatterns).insert(
      GeJuPatternsCompanion.insert(
        id: 'p1',
        name: '测试格局',
        categoryId: 'c1',
        createdAt: DateTime.now(),
      ),
    );

    final ruleId = await db.into(db.geJuRules).insert(
      GeJuRulesCompanion.insert(
        patternId: 'p1',
        schoolId: 's1',
        jixiong: '吉',
        geJuType: '贵',
        scope: 'natal',
        version: 'v1',
        isVerified: const Value(false),
        chapter: const Value('初始章节'),
        conditions: const Value('{"type":"initial"}'),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      ),
    );

    final ruleProvider = RuleProvider(db);
    final settingsProvider = SettingsProvider();
    final aiChatController = FakeAiChatController();

    await tester.pumpWidget(createTestWidget(
      db: db,
      ruleProvider: ruleProvider,
      settingsProvider: settingsProvider,
      aiChatController: aiChatController,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('初始章节'), findsOneWidget);

    // 修改吉凶（下拉选择）：将「吉」改为「凶」以触发脏状态
    await tester.tap(find.text('吉').first);
    await tester.pump(const Duration(milliseconds: 200));

    await tester.tap(find.text('凶').last);
    await tester.pump(const Duration(milliseconds: 200));

    // 点击保存按钮
    final saveButton = find.widgetWithText(FilledButton, '保存');
    expect(saveButton, findsOneWidget);
    await tester.tap(saveButton);
    await tester.pump(const Duration(milliseconds: 200));

    // 检查数据库：isVerified 必须依然为 false
    final ruleInDb = await (db.select(db.geJuRules)
          ..where((t) => t.id.equals(ruleId)))
        .getSingle();

    expect(ruleInDb.jixiong, equals('凶'));
    expect(ruleInDb.isVerified, isFalse,
        reason: '人工保存不得自动置 verified 为 true');
  });

  testWidgets('用例 2：已核验规则经 AI 条件保存后，isVerified 必须回落为 false (B2)',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(2600, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    final db = AppDatabase(NativeDatabase.memory());
    addTearDown(() => db.close());

    await db.delete(db.geJuRules).go();
    await db.delete(db.geJuPatterns).go();
    await db.delete(db.geJuSchools).go();

    await db.into(db.geJuSchools).insert(
      GeJuSchoolsCompanion.insert(
        id: 's1',
        name: '测试流派',
        type: 'school',
        createdAt: DateTime.now(),
      ),
    );
    await db.into(db.geJuPatterns).insert(
      GeJuPatternsCompanion.insert(
        id: 'p1',
        name: '测试格局',
        categoryId: 'c1',
        createdAt: DateTime.now(),
      ),
    );

    final ruleId = await db.into(db.geJuRules).insert(
      GeJuRulesCompanion.insert(
        patternId: 'p1',
        schoolId: 's1',
        jixiong: '吉',
        geJuType: '贵',
        scope: 'natal',
        version: 'v1',
        isVerified: const Value(true), // 初始为已核验状态
        chapter: const Value('初始章节'),
        conditions: const Value('{"type":"initial"}'),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      ),
    );

    final ruleProvider = RuleProvider(db);
    final settingsProvider = SettingsProvider();
    final aiChatController = FakeAiChatController();

    await tester.pumpWidget(createTestWidget(
      db: db,
      ruleProvider: ruleProvider,
      settingsProvider: settingsProvider,
      aiChatController: aiChatController,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    // 点击 AI 识别按钮打开弹窗
    final aiButton = find.byIcon(Icons.psychology_outlined);
    expect(aiButton, findsOneWidget);
    await tester.tap(aiButton);
    await tester.pump(const Duration(milliseconds: 300));

    // 输入描述并发送给 FakeAiChatController
    final dialogInput = find.byType(TextField).last;
    await tester.enterText(dialogInput, 'AI 识别描述');
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pump(const Duration(milliseconds: 100));

    final sendButton = find.widgetWithText(FilledButton, '发送');
    await tester.tap(sendButton);
    await tester.pump(const Duration(milliseconds: 300));

    // 点击保存
    final dialogSaveButton = find.widgetWithText(FilledButton, '保存 ✓');
    expect(dialogSaveButton, findsOneWidget);
    await tester.tap(dialogSaveButton);
    await tester.pump(const Duration(milliseconds: 300));

    // 检查数据库：经过 AI 保存后，isVerified 必须回落为 false
    final ruleInDb = await (db.select(db.geJuRules)
          ..where((t) => t.id.equals(ruleId)))
        .getSingle();

    expect(ruleInDb.conditions, equals('{"type":"ai_condition"}'));
    expect(ruleInDb.isVerified, isFalse,
        reason: 'AI 条件保存后必须回落为 candidate/false');
  });

  testWidgets('用例 3：显式人工勾选通道依然能够将规则置为 verified (B3)',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(2600, 1200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(() => tester.view.resetPhysicalSize());

    final db = AppDatabase(NativeDatabase.memory());
    addTearDown(() => db.close());

    await db.delete(db.geJuRules).go();
    await db.delete(db.geJuPatterns).go();
    await db.delete(db.geJuSchools).go();

    await db.into(db.geJuSchools).insert(
      GeJuSchoolsCompanion.insert(
        id: 's1',
        name: '测试流派',
        type: 'school',
        createdAt: DateTime.now(),
      ),
    );
    await db.into(db.geJuPatterns).insert(
      GeJuPatternsCompanion.insert(
        id: 'p1',
        name: '测试格局',
        categoryId: 'c1',
        createdAt: DateTime.now(),
      ),
    );

    final ruleId = await db.into(db.geJuRules).insert(
      GeJuRulesCompanion.insert(
        patternId: 'p1',
        schoolId: 's1',
        jixiong: '吉',
        geJuType: '贵',
        scope: 'natal',
        version: 'v1',
        isVerified: const Value(false),
        chapter: const Value('初始章节'),
        conditions: const Value('{"type":"initial"}'),
        createdAt: DateTime.now(),
        updatedAt: DateTime.now(),
      ),
    );

    final ruleProvider = RuleProvider(db);
    final settingsProvider = SettingsProvider();
    final aiChatController = FakeAiChatController();

    await tester.pumpWidget(createTestWidget(
      db: db,
      ruleProvider: ruleProvider,
      settingsProvider: settingsProvider,
      aiChatController: aiChatController,
    ));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 200));

    // 点击手动校验 Checkbox
    final checkboxFinder = find.byType(Checkbox);
    expect(checkboxFinder, findsOneWidget);
    await tester.tap(checkboxFinder);
    await tester.pump(const Duration(milliseconds: 200));

    // 检查数据库：手动校验通道必须正常置 true
    final ruleInDb = await (db.select(db.geJuRules)
          ..where((t) => t.id.equals(ruleId)))
        .getSingle();

    expect(ruleInDb.isVerified, isTrue,
        reason: '显式勾选通道必须能将 isVerified 置为 true');
  });
}
