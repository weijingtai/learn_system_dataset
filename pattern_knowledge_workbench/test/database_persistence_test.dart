import 'dart:io';
import 'package:drift/drift.dart' hide isNull, isNotNull;
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:companion_system/database/drift_database.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  driftRuntimeOptions.dontWarnAboutMultipleDatabases = true;

  const channel = MethodChannel('plugins.flutter.io/path_provider');
  late Directory tempDir;
  late Directory docDir;
  late Directory tmpDir;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('workbench_db_test_');
    docDir = Directory(p.join(tempDir.path, 'docs'))..createSync(recursive: true);
    tmpDir = Directory(p.join(tempDir.path, 'tmp'))..createSync(recursive: true);

    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (MethodCall methodCall) async {
      switch (methodCall.method) {
        case 'getApplicationDocumentsDirectory':
          return docDir.path;
        case 'getTemporaryDirectory':
          return tmpDir.path;
        default:
          return null;
      }
    });
  });

  tearDown(() async {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null);
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('目标文件缺失时自动从 assets 播种 (B1)', () async {
    final docsDir = await getApplicationDocumentsDirectory();
    final dbFile = File(p.join(docsDir.path, 'ge_ju_database.sqlite'));
    expect(await dbFile.exists(), isFalse);

    final db = AppDatabase();
    final schools = await db.select(db.geJuSchools).get();
    expect(schools, isNotEmpty);
    expect(await dbFile.exists(), isTrue);

    await db.close();
  });

  test('目标文件已存在时不得被 assets 覆盖，保留本地新增/修改数据 (B2, B3)', () async {
    final docsDir = await getApplicationDocumentsDirectory();
    final dbFile = File(p.join(docsDir.path, 'ge_ju_database.sqlite'));
    expect(await dbFile.exists(), isFalse);

    // 第一次启动：自动播种并写入自定义记录
    final db1 = AppDatabase();
    const customSchoolId = 'test_custom_school_persistence';
    await db1.into(db1.geJuSchools).insert(
      GeJuSchoolsCompanion.insert(
        id: customSchoolId,
        name: '测试自定义持久化流派',
        type: 'school',
        isActive: const Value(true),
        ruleCount: const Value(0),
        createdAt: DateTime.now(),
      ),
    );

    final inserted = await (db1.select(db1.geJuSchools)
          ..where((tbl) => tbl.id.equals(customSchoolId)))
        .getSingleOrNull();
    expect(inserted, isNotNull);
    await db1.close();

    expect(await dbFile.exists(), isTrue);
    final fileBytesBefore = await dbFile.readAsBytes();

    // 第二次启动（模拟工作台重启）：重新初始化 AppDatabase
    final db2 = AppDatabase();
    final schoolAfterRestart = await (db2.select(db2.geJuSchools)
          ..where((tbl) => tbl.id.equals(customSchoolId)))
        .getSingleOrNull();

    // 断言：本地库已存在时不得被 assets 覆盖，新增数据必须保留
    expect(
      schoolAfterRestart,
      isNotNull,
      reason: '本地数据库中的自定义数据在重启初始化后不得被 assets 覆盖丢失',
    );

    final fileBytesAfter = await dbFile.readAsBytes();
    expect(
      fileBytesAfter,
      equals(fileBytesBefore),
      reason: '本地数据库文件内容在重启初始化后不得被重新覆盖写入',
    );

    await db2.close();
  });
}
