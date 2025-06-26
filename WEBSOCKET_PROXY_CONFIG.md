# WebSocket プロキシ設定ガイド

本アプリケーションのTerminal機能はWebSocketを使用しています。本番環境では、リバースプロキシでWebSocketアップグレードを適切に設定する必要があります。

## Nginx 設定例

```nginx
server {
    listen 443 ssl http2;
    server_name front.claude.code.pve.hidearea.net;
    
    # SSL設定
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    # フロントエンド用（静的ファイル）
    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }
    
    # API用（HTTP）
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # WebSocket用（重要）
    location /api/terminal/ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket タイムアウト設定
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_connect_timeout 86400;
    }
    
    # その他のWebSocket（必要に応じて）
    location /api/ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket タイムアウト設定
        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
        proxy_connect_timeout 86400;
    }
}
```

## Apache 設定例

```apache
<VirtualHost *:443>
    ServerName front.claude.code.pve.hidearea.net
    DocumentRoot /path/to/frontend/dist
    
    # SSL設定
    SSLEngine on
    SSLCertificateFile /path/to/certificate.crt
    SSLCertificateKeyFile /path/to/private.key
    
    # WebSocket サポート
    LoadModule proxy_wstunnel_module modules/mod_proxy_wstunnel.so
    
    # API プロキシ
    ProxyPreserveHost On
    ProxyRequests Off
    
    # WebSocket用
    ProxyPass /api/terminal/ws/ ws://backend:8000/api/terminal/ws/
    ProxyPassReverse /api/terminal/ws/ ws://backend:8000/api/terminal/ws/
    
    ProxyPass /api/ws/ ws://backend:8000/api/ws/
    ProxyPassReverse /api/ws/ ws://backend:8000/api/ws/
    
    # HTTP API用
    ProxyPass /api/ http://backend:8000/api/
    ProxyPassReverse /api/ http://backend:8000/api/
    
    # フロントエンド用
    <Directory /path/to/frontend/dist>
        AllowOverride All
        Require all granted
        FallbackResource /index.html
    </Directory>
</VirtualHost>
```

## Traefik 設定例

```yaml
# docker-compose.yml または traefik設定
version: '3.8'
services:
  traefik:
    image: traefik:v2.9
    command:
      - --api.dashboard=true
      - --providers.docker=true
      - --entrypoints.websecure.address=:443
      - --certificatesresolvers.myresolver.acme.email=your-email@domain.com
      - --certificatesresolvers.myresolver.acme.storage=/acme.json
      - --certificatesresolvers.myresolver.acme.httpchallenge.entrypoint=web
    labels:
      - "traefik.http.routers.frontend.rule=Host(`front.claude.code.pve.hidearea.net`)"
      - "traefik.http.routers.frontend.tls.certresolver=myresolver"
      - "traefik.http.services.frontend.loadbalancer.server.port=80"

  backend:
    # バックエンドサービス
    labels:
      - "traefik.http.routers.backend.rule=Host(`front.claude.code.pve.hidearea.net`) && PathPrefix(`/api/`)"
      - "traefik.http.routers.backend.tls.certresolver=myresolver"
      - "traefik.http.services.backend.loadbalancer.server.port=8000"
```

## 設定の確認方法

### 1. WebSocket 接続テスト
ブラウザの開発者ツールで以下を確認：
- Console に WebSocket URL が正しく表示されているか
- Network タブで WebSocket 接続が確立されているか

### 2. プロキシログの確認
```bash
# Nginx の場合
sudo tail -f /var/log/nginx/access.log | grep -E "(ws|upgrade)"

# Apache の場合
sudo tail -f /var/log/apache2/access.log | grep -E "(ws|upgrade)"
```

### 3. バックエンドログの確認
```bash
# Docker の場合
docker logs -f claude-code-client-backend-1 | grep -i websocket
```

## トラブルシューティング

### よくある問題と解決方法

1. **WebSocket アップグレードが失敗する**
   - プロキシ設定で `proxy_set_header Upgrade $http_upgrade;` と `proxy_set_header Connection "upgrade";` が設定されているか確認

2. **タイムアウトエラー**
   - プロキシのタイムアウト設定を延長（`proxy_read_timeout`, `proxy_send_timeout`）

3. **SSL証明書エラー**
   - WebSocket も HTTPS/WSS で適切に証明書が設定されているか確認

4. **CORS エラー**
   - プロキシでオリジンヘッダーが適切に転送されているか確認

### デバッグコマンド

```bash
# WebSocket 接続テスト
wscat -c wss://front.claude.code.pve.hidearea.net/api/terminal/ws/test-session?terminal_type=basic

# SSL証明書確認
openssl s_client -connect front.claude.code.pve.hidearea.net:443 -servername front.claude.code.pve.hidearea.net

# プロキシヘッダー確認
curl -H "Upgrade: websocket" -H "Connection: upgrade" -i https://front.claude.code.pve.hidearea.net/api/terminal/ws/test
```