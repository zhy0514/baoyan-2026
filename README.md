# 🎓 2026 985高校夏令营/预推免信息聚合

一站式查看全国 **39所985高校** 2026年数学、统计学、人工智能、计算机相关专业的夏令营和预推免信息。

🌐 **在线访问**: 部署后自动通过 GitHub Pages 提供

## 功能特点

- 📊 **三种视图**: 卡片 / 列表 / 时间线
- 🔍 **多维度筛选**: 学校、专业、类型、状态、关键词搜索
- 🟢 **状态标记**: 报名中 / 即将截止 / 已截止
- 📱 **响应式布局**: 桌面 / 平板 / 手机 自适应
- 🤖 **每日自动更新**: GitHub Actions 每天早上7点自动爬取
- 📡 **多渠道聚合**: 高校官网 + 第三方保研平台

## 项目结构

```
├── frontend/              # 静态前端页面
│   ├── index.html
│   ├── css/style.css
│   └── js/
│       ├── app.js         # 数据渲染、过滤、排序
│       └── utils.js       # 工具函数
├── data/                  # 爬虫产出的数据
│   ├── programs.json      # 核心数据
│   └── meta.json          # 统计摘要
├── crawler/               # Python爬虫
│   ├── main.py            # 调度入口
│   ├── base_scraper.py    # 爬虫基类
│   ├── normalizer.py      # 数据规范化
│   ├── dedup.py           # 去重引擎
│   ├── scrapers/          # 各高校爬虫
│   └── platforms/         # 第三方平台爬虫
└── .github/workflows/     # 自动更新
    └── daily-scrape.yml
```

## 本地运行

### 前端预览

```bash
cd frontend
python -m http.server 8080
# 打开 http://localhost:8080
```

### 运行爬虫

```bash
cd crawler
pip install -r requirements.txt
python main.py
```

## 覆盖高校 (首批5校)

- 🟢 北京大学 — 计算机学院、数学科学学院、信息工程学院等
- 🟢 清华大学 — 交叉信息研究院、计算机系等
- 🟢 复旦大学 — 计算机科学技术学院、大数据学院等
- 🟢 上海交通大学 — 电子信息与电气工程学院、AI研究院等
- 🟢 浙江大学 — 计算机科学与技术学院、数学科学学院等

更多985高校持续添加中...

## 数据来源

- 各高校研究生院/学院官方网站
- [CS-BAOYAN-2026](https://github.com/jsjby/CS-BAOYAN-2026) (GitHub 第三方汇总)
- 保研通、保研论坛等平台

## 免责声明

⚠️ 信息仅供参考，请以各高校官方通知为准。数据每日自动更新，可能存在延迟或错误，如有问题欢迎反馈。
