# NC-016b BDD：真实设备集成测试场景

## 场景 1：LAN 设备发现与配对

```gherkin
Feature: LAN 设备发现与配对
  作为用户
  我希望在同一局域网内发现其他设备并配对
  以便进行私人数据同步

  Background:
    Given 两台设备在同一局域网内
    And 两台设备都已安装 reading-notes
    And 用户已登录同一账号

  Scenario: 成功配对
    When 设备 A 进入配对模式
    And 设备 B 进入配对模式
    Then 设备 A 应发现设备 B
    And 设备 B 应发现设备 A
    When 用户确认配对
    Then 两台设备应显示配对成功
    And 设备列表应显示对端设备
```

## 场景 2：会话密钥交换

```gherkin
Feature: 会话密钥交换
  作为已配对设备
  我希望安全地交换会话密钥
  以便加密传输数据

  Background:
    Given 两台设备已完成配对
    And 两台设备都在线

  Scenario: 成功交换密钥
    When 设备 A 生成 X25519 会话密钥对
    And 设备 A 发送会话公钥（带 Ed25519 签名）
    Then 设备 B 应验证签名有效
    And 设备 B 应生成自己的会话密钥对
    And 设备 B 应发送会话公钥（带签名）
    And 两台设备应派生相同的共享密钥
```

## 场景 3：加密数据传输

```gherkin
Feature: 加密数据传输
  作为已建立会话的设备
  我希望加密传输数据
  以便保护隐私

  Background:
    Given 两台设备已建立安全会话
    And 共享密钥已派生

  Scenario: 成功传输加密数据
    When 设备 A 创建测试笔记
    And 设备 A 加密笔记数据（AES-GCM + AAD）
    And 设备 A 发送加密数据
    Then 设备 B 应接收加密数据
    And 设备 B 应解密数据成功
    And 设备 B 应显示笔记内容
```

## 场景 4：中转上传与信令

```gherkin
Feature: 中转上传与信令
  作为跨网络设备
  我希望通过中转服务器同步数据
  以便在不同网络环境下同步

  Background:
    Given 两台设备不在同一局域网
    And 中转服务器可用

  Scenario: 成功中转上传
    When 设备 A 上传加密数据到 Storage
    And 设备 A 发送信令到 Notifier
    Then 设备 B 应接收信令
    And 设备 B 应从中转下载数据
    And 设备 B 应解密并存储数据
```

## 场景 5：SyncRuntime 注册

```gherkin
Feature: SyncRuntime entityType 注册
  作为同步系统
  我希望正确注册实体类型
  以便支持不同类型的同步数据

  Background:
    Given 应用已启动
    And SyncRuntime 已初始化

  Scenario: 成功注册 entityType
    When SyncRuntime 初始化完成
    Then entityType "note" 应已注册
    And entityType "comment" 应已注册
    And entityType "attachment" 应已注册
```
