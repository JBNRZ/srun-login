# srun-login 

杭州电子科技大学校园网 Wi-Fi 登录 / 深澜（srun）校园网模拟登录

重写互联网上现存的登陆脚本，适应2024年暑假后的网络变化，支持`生活区`、`教学区`和`绍兴校区`的登录认证，同时支持`多用户账号`定时切换登录

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

### 自动识别校区

运行方式保持不变，无需指定校区参数。程序优先通过普通 HTTP 连通性请求的认证跳转，
识别当前网络使用的门户；绍兴校区使用 `https://yue.hdu.edu.cn`，初始 `ac_id` 为 `1`。
已认证或未发现跳转时，程序查询已知门户的在线状态，优先选择报告在线的门户；
若没有门户报告在线，则选择可用门户。同等条件下，下沙优先于绍兴，
下沙门户保留原有尝试顺序。实际认证跳转指向绍兴时，仍直接选择绍兴门户。

下沙校区的认证算法、控制器重试策略和定时任务保持不变；开机自启及 Docker 启动命令无需增加参数。

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
