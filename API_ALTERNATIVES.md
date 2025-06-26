# Claude Code API 課金回避の代替案

## 現状の確認

**Claude Code SDK/CLI は Anthropic Claude API の有料サービスを使用します。**
- SDK: 内部的にAnthropic APIを呼び出し
- CLI: 同様にAnthropic APIを使用
- 両方とも課金が発生

## 代替案

### 1. 高品質モックモード（推奨）

現在実装済みの詳細なモック応答を使用：

**メリット**:
- 無料で使用可能
- UI/UX開発に最適
- 基本機能のテスト可能

**制限**:
- 実際のコード生成不可
- ファイル操作不可

### 2. ローカルLLMとの統合

Ollama、LocalAI等のローカルLLMを使用：

```python
# 例: Ollama統合
async def send_to_local_llm(message: str):
    response = await ollama_client.chat(
        model='codellama',
        messages=[{'role': 'user', 'content': message}]
    )
    return response['message']['content']
```

**メリット**:
- 完全無料
- プライバシー保護
- カスタマイズ可能

**デメリット**:
- 品質が Claude より劣る
- ローカルリソース消費
- セットアップ複雑

### 3. OpenAI API代替

より安価なOpenAI GPT-4を使用：

```python
import openai

async def send_to_openai(message: str):
    response = await openai.ChatCompletion.acreate(
        model="gpt-4",
        messages=[{"role": "user", "content": message}]
    )
    return response.choices[0].message.content
```

**メリット**:
- Claude より安価
- 高品質な応答
- 豊富なツール

**デメリット**:
- 依然として有料
- Claude Code特有の機能なし

### 4. 混合モード（推奨）

API クレジット有無で自動切り替え：

1. **Claude Code**: クレジット十分時
2. **モックモード**: クレジット不足時
3. **ローカルLLM**: 高度な処理が必要時

## 現在の実装状況

✅ **Claude Code SDK/CLI統合**: 完了（要クレジット）
✅ **高品質モックモード**: 実装済み
✅ **エラーハンドリング**: クレジット不足対応
✅ **自動切り替え**: SDK→CLI→モック

## 推奨アプローチ

**開発・テスト段階**:
```
モックモード → UI/UX完成 → 最小限のクレジットでテスト
```

**本格運用時**:
```
Claude Code API（$5-10でスタート）
```

## 実装例

現在の claude-integration.py では以下の優先順位で動作：

1. Claude Code SDK（利用可能時）
2. Claude Code CLI（SDKが使用不可時）
3. 高品質モックモード（両方とも使用不可時）

これにより、クレジット状況に関係なく開発を継続できます。