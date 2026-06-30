# srun-login 

杭州电子科技大学校园网 Wi-Fi 登录 / 深澜（srun）校园网模拟登录

重写互联网上现存的登陆脚本，适应2024年暑假后的网络变化，支持`生活区`和`教学区`的登录认证，同时支持`多用户账号`定时切换登录

## 开始使用

### 直接运行

```bash
# 克隆项目
git clone git@github.com:JBNRZ/srun-login.git

# 安装依赖
cd srun-login && pip3 install -r requirements.txt

# 创建并编辑auth.json
cat<<EOF>auth.json
[
  {"username": "username1", "password": "password1"},
  {"username": "username2", "password": "password2"},
  {"username": "username3", "password": "password3"} 
]
EOF

# 运行
nohup python3 login.py &
```

### Docker 运行

```bash
# 创建并编辑 auth.json
cat<<EOF>auth.json
[
  {"username": "username1", "password": "password1"},
  {"username": "username2", "password": "password2"},
  {"username": "username3", "password": "password3"}
]
EOF

# 使用 GHCR 镜像运行
docker run -d \
  --name srun-login \
  --restart unless-stopped \
  --network host \
  -v "$(pwd)/auth.json:/app/auth.json:ro" \
  ghcr.io/jbnrz/srun-login:latest
```

如果需要查看日志：

```bash
docker logs -f srun-login
```

如果需要使用日期版本镜像，将 `latest` 替换为对应日期 tag，例如：

```bash
docker pull ghcr.io/jbnrz/srun-login:20260630
```

## 配置开机自启

```yaml
[Unit]
Description=srun login

[Service]
Type=simple
User=root
ExecStart=python3 /path/to/your/file.py
WorkingDirectory=/path/to/your/dir

[Install]
WantedBy=multi-user.target
```

## License

MIT License
