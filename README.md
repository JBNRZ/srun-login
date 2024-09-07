# srun-login 

杭州电子科技大学校园网 Wi-Fi 登录 / 深澜（srun）校园网模拟登录

重写互联网上现存的登陆脚本，适应2024年暑假后的网络变化，支持`生活区`和`教学区`的登录认证，同时支持`多用户账号`定时切换登录

## 开始使用

```bash
# 克隆项目
git clone git@github.com:JBNRZ/srun-login.git

# 安装依赖
cd srun-login && pip3 install -r requirements.txt

# 创建并编辑auth.json
cat<<EOF>auth.json
[
  {"username": "你的学号", "password": "你的密码"},
  {"username": "你的学号", "password": "你的密码"},
  {"username": "你的学号", "password": "你的密码"} 
]
EOF

# 运行
nohup python3 login.py &
```

## 配置开机自启

```yaml
[Unit]
Description=srun login

[Service]
Type=simple
User=root
ExecStart=python3 /path/to/your/file.py

[Install]
WantedBy=multi-user.target
```

## License

MIT License
