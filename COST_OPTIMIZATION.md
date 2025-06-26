# Claude API コスト最適化ガイド

## サブスクリプションでは API は使用不可

**重要**: Claude Pro サブスクリプション（$20/月）と Claude API は別サービスです。
- Claude Pro: Web版のみ利用可能
- Claude API: 従量課金制、Claude Code で必要

## 最小コストでの開発手法

### 1. 段階的開発アプローチ

```
フェーズ1: モックモード → UI/UX完成（無料）
フェーズ2: 最小APIテスト → $5クレジットで基本動作確認
フェーズ3: 本格開発 → 必要に応じてクレジット追加
```

### 2. API使用量最適化

#### a) 開発専用プロンプト最適化
```python
# 実装済み: _optimize_prompt_for_cost()
- 長いメッセージの要約
- 簡潔な応答要求
- 開発専用モード指定
```

#### b) 効率的なテストパターン
```
短いメッセージ: $0.01-0.02/回
- "Hello" → Claude Code動作確認
- "Create a simple Python file" → 基本機能テスト
- "List files in current directory" → ツール連携テスト
```

### 3. 代替統合案

#### A) ローカルLLM統合（完全無料）

**Ollama + CodeLlama**:
```yaml
# docker-compose.yml に追加
ollama:
  image: ollama/ollama
  volumes:
    - ollama_data:/root/.ollama
  ports:
    - "11434:11434"
```

**Python統合**:
```python
import requests

async def send_to_ollama(message: str):
    response = requests.post('http://ollama:11434/api/chat', json={
        'model': 'codellama',
        'messages': [{'role': 'user', 'content': message}],
        'stream': False
    })
    return response.json()['message']['content']
```

#### B) 混合モード（推奨）

```python
async def send_message(self, message: str):
    # 1. 重要な処理: Claude API
    if self._is_critical_task(message):
        return await self._use_claude_api(message)
    
    # 2. 簡単な処理: ローカルLLM
    elif self._is_simple_task(message):
        return await self._use_local_llm(message)
    
    # 3. UI開発: モックモード
    else:
        return await self._use_mock_response(message)
```

### 4. 開発段階別コスト

| 段階 | 方法 | コスト | 機能レベル |
|------|------|--------|------------|
| UI開発 | モックモード | 無料 | 70% |
| 基本テスト | Claude API ($5) | $5 | 95% |
| 本格開発 | Claude API ($10-20) | $10-20 | 100% |
| 代替案 | ローカルLLM | 無料 | 60-80% |

### 5. 現在の実装の活用

既に実装されている機能:
- ✅ 自動フォールバック（Claude → モック）
- ✅ コスト最適化プロンプト
- ✅ エラーハンドリング
- ✅ 高品質モック応答

### 6. 推奨フロー

1. **今すぐ**: モックモードでUI完成
2. **$5投資**: 基本動作確認・デモ
3. **必要時**: 追加クレジットで本格開発

## まとめ

Claude のサブスクリプションでは API 使用不可ですが:
- 最小$5で十分な開発・テストが可能
- モックモードで大部分の開発が無料で可能
- ローカルLLM統合で完全無料化も可能

現在の実装により、コスト効率的な開発環境が整っています。