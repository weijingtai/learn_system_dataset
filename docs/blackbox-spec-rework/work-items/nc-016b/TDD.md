# NC-016b TDD：真实设备集成测试用例

## 测试用例 1：设备发现

```dart
test('should discover peer device on LAN', () async {
  // Arrange
  final deviceA = await connectDevice('JCP6R21628000116');
  final deviceB = await connectDevice('emulator-5554');
  
  // Act
  await deviceA.startDiscovery();
  await deviceB.startDiscovery();
  
  // Assert
  expect(deviceA.discoveredDevices, contains(deviceB.deviceId));
  expect(deviceB.discoveredDevices, contains(deviceA.deviceId));
});
```

## 测试用例 2：配对验证

```dart
test('should complete pairing with fingerprint verification', () async {
  // Arrange
  final deviceA = await connectDevice('JCP6R21628000116');
  final deviceB = await connectDevice('emulator-5554');
  
  // Act
  final resultA = await deviceA.initiatePairing(deviceB.deviceId);
  final resultB = await deviceB.acceptPairing(deviceA.deviceId);
  
  // Assert
  expect(resultA.outOfBandFingerprint, equals(resultB.outOfBandFingerprint));
  expect(resultA.status, equals(PairingStatus.success));
  expect(resultB.status, equals(PairingStatus.success));
});
```

## 测试用例 3：会话密钥交换

```dart
test('should exchange session keys with Ed25519 signature', () async {
  // Arrange
  final session = await establishSession(deviceA, deviceB);
  
  // Act
  final keyA = await session.generateSessionKeyPair();
  final signedKeyA = await session.signSessionPublicKey(keyA.publicKey);
  final keyB = await session.receiveSignedPublicKey(signedKeyA);
  
  // Assert
  expect(session.verifySignature(signedKeyA.signature, keyA.publicKey), isTrue);
  expect(session.sharedSecret, isNotNull);
  expect(session.sharedSecret.length, equals(32));
});
```

## 测试用例 4：加密数据传输

```dart
test('should encrypt and decrypt data with AAD', () async {
  // Arrange
  final testData = 'Test note content';
  final aad = 'app_user_id|device_id|sequence_number';
  
  // Act
  final encrypted = await encryptData(testData, sharedKey, aad);
  final decrypted = await decryptData(encrypted, sharedKey, aad);
  
  // Assert
  expect(encrypted, isNot(equals(testData)));
  expect(decrypted, equals(testData));
});
```

## 测试用例 5：中转上传

```dart
test('should upload to relay and receive signal', () async {
  // Arrange
  final relayUrl = 'https://relay.example.com';
  final encryptedData = await encryptData(testData, sharedKey, aad);
  
  // Act
  final uploadResult = await uploadToRelay(relayUrl, encryptedData);
  final signal = await receiveSignal(deviceB, uploadResult.signalId);
  
  // Assert
  expect(uploadResult.success, isTrue);
  expect(signal.dataId, equals(uploadResult.dataId));
});
```

## 测试用例 6：SyncRuntime 注册

```dart
test('should register entityType in SyncRuntime', () async {
  // Arrange
  final runtime = SyncRuntime();
  
  // Act
  await runtime.registerEntityType('note', NoteSyncAdapter());
  await runtime.registerEntityType('comment', CommentSyncAdapter());
  
  // Assert
  expect(runtime.registeredTypes, contains('note'));
  expect(runtime.registeredTypes, contains('comment'));
  expect(runtime.getAdapter('note'), isA<NoteSyncAdapter>());
});
```

## 测试用例 7：完整同步流程

```dart
test('should complete full sync flow between devices', () async {
  // Arrange
  final deviceA = await connectDevice('JCP6R21628000116');
  final deviceB = await connectDevice('emulator-5554');
  await completePairing(deviceA, deviceB);
  
  // Act
  final note = await deviceA.createNote('Test note');
  await deviceA.syncNote(note);
  await deviceB.waitForSync();
  
  // Assert
  final syncedNote = await deviceB.getNote(note.id);
  expect(syncedNote.content, equals(note.content));
  expect(syncedNote.timestamp, equals(note.timestamp));
});
```
