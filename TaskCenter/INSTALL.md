# 安装指南
## 完整安装步骤（按顺序执行）

### 步骤 1: 创建项目根目录结构

```bash
cd E:\Projects\AiProject\AgentOS
mkdir -p TaskCenter/agent_os/task_center
cd TaskCenter
```

### 步骤 2: 初始化 Python 包

```bash
# 创建 agent_os 命名空间包标记
touch agent_os/__init__.py

# 或者如果已经有 agent_os 目录，确保它包含正确的 __init__.py
```

### 步骤 3: 安装依赖

```bash
# 方案 A: 如果有真实的 agent_os.common 包
pip install -e ../common  # 假设 common 在并行目录

# 方案 B: 临时使用 mock（仅用于开发测试）
# 无需额外操作，测试会使用 tests/utils/mock_common.py

# 安装 TaskCenter 本身（开发模式）
pip install -e ".[dev]"
```

### 步骤 4: 配置环境变量

创建 `.env` 文件：

```bash
cat > .env << 'EOF'
# Test Database
TEST_DB_HOST=localhost
TEST_DB_PORT=5432
TEST_DB_NAME=agent_test_db
TEST_DB_USER=agent_test_user
TEST_DB_PASSWORD=test_password

# Production Database (for future use)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agent_db
DB_USER=agent_user
DB_PASSWORD=your_production_password
EOF
```

加载环境变量：

```bash
# Linux/Mac
export $(cat .env | xargs)

# Windows PowerShell
Get-Content .env | ForEach-Object {
    $name, $value = $_.split('=')
    Set-Item -Path "env:$name" -Value $value
}
```

### 步骤 5: 设置 PostgreSQL 测试数据库

```bash
# 创建数据库
createdb agent_test_db

# 创建用户并授权
psql -c "CREATE USER agent_test_user WITH PASSWORD 'test_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE agent_test_db TO agent_test_user;"

# PostgreSQL 15+ 需要额外授权
psql agent_db -c "GRANT ALL ON SCHEMA public TO agent_user;"
psql agent_db -c "GRANT ALL ON ALL TABLES IN SCHEMA public TO agent_user;"
```

### 步骤 6: 验证安装

```bash
# 验证包可以导入
python -c "from agent_os.task_center import TaskCenter; print('✓ TaskCenter installed')"

# 运行测试
pytest tests/unit/ -v  # 先运行不依赖数据库的单元测试
```

### 步骤 7: 如果遇到导入错误

**错误**: `ModuleNotFoundError: No module named 'agent_os.common'`

**临时解决方案**（仅用于测试开发）:

修改 `conftest.py`，添加以下代码在导入语句之前：

```python
# tests/conftest.py 顶部添加
import sys
from pathlib import Path

# 如果 agent_os.common 不存在，使用 mock
try:
    from agent_os.common import Task, TaskStatus
except ModuleNotFoundError:
    # 将 mock_common 添加到 sys.modules
    import tests.utils.mock_common as mock_common
    sys.modules['agent_os.common'] = mock_common
    sys.modules['agent_os.common.interfaces'] = mock_common
    sys.modules['agent_os.common.events'] = mock_common
```

### 步骤 8: 运行完整测试套件

```bash
# 所有测试
pytest tests/ -v

# 仅单元测试（无需数据库）
pytest tests/unit/ -v

# 组件和集成测试（需要数据库）
pytest tests/component/ tests/integration/ -v

# 带覆盖率报告
pytest tests/ --cov=agent_os.task_center --cov-report=html
```

---

## 常见问题解决方案

### 问题 1: pytest 找不到模块

```bash
# 确保以可编辑模式安装
pip install -e .

# 验证 PYTHONPATH
python -c "import sys; print('\n'.join(sys.path))"
```

### 问题 2: asyncpg 安装失败

```bash
# Windows 需要 Visual C++ 构建工具
# 下载: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# 或使用预编译轮子
pip install asyncpg --only-binary=:all:
```

### 问题 3: PostgreSQL 连接被拒绝

```bash
# 检查 PostgreSQL 是否运行
pg_isready

# 检查 pg_hba.conf 允许本地连接
# 添加行: local all agent_test_user md5

# 重启 PostgreSQL
sudo systemctl restart postgresql  # Linux
brew services restart postgresql   # Mac
```

### 问题 4: 权限错误

```bash
# 授予所有必要权限
psql -U postgres agent_test_db << 'EOF'
GRANT ALL PRIVILEGES ON DATABASE agent_test_db TO agent_test_user;
GRANT ALL ON SCHEMA public TO agent_test_user;
GRANT ALL ON ALL TABLES IN SCHEMA public TO agent_test_user;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO agent_test_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO agent_test_user;
EOF
```

---

## 项目目录最终结构

```
E:\Projects\AiProject\AgentOS\TaskCenter\
├── agent_os/
│   ├── __init__.py                    # 命名空间包标记
│   └── task_center/
│       ├── __init__.py                # 已创建的所有模块
│       ├── task_center.py
│       ├── config.py
│       ├── state_machine.py
│       └── ... (所有其他模块)
├── tests/
│   ├── conftest.py                    # 已创建的所有测试
│   ├── unit/
│   ├── component/
│   ├── integration/
│   └── utils/
│       ├── test_db.py
│       ├── mock_event_bus.py
│       ├── task_builder.py
│       ├── async_helpers.py
│       └── mock_common.py             # 临时 mock（可选）
├── setup.py                           # ✓ 新创建
├── pyproject.toml                     # ✓ 新创建
├── requirements.txt                   # ✓ 新创建
├── requirements-dev.txt               # ✓ 新创建
├── INSTALL.md                         # ✓ 新创建
├── README.md                          # ✓ 新创建
└── .env                               # ✓ 需手动创建
```

现在可以运行：

```bash
pip install -e ".[dev]"
pytest tests/ -v
```


## 快速安装步骤

### 1. 安装包（开发模式）

```bash
cd E:\Projects\AiProject\AgentOS\TaskCenter

# 安装 TaskCenter
pip install -e .
```

### 2. 验证安装

```bash
python verify_install.py
```

### 3. 配置环境变量

```bash
# 复制示例文件
copy .env.example .env

# Windows PowerShell 加载环境变量
Get-Content .env | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)\s*=\s*(.+)\s*$') {
        $name = $matches[1].Trim()
        $value = $matches[2].Trim()
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}
```

### 4. 设置测试数据库（如果需要运行集成测试）

```bash
# 使用 psql 或 pgAdmin 执行
createdb agent_test_db

# 授权
psql -c "CREATE USER agent_test_user WITH PASSWORD 'test_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE agent_test_db TO agent_test_user;"
```

### 5. 运行测试

```bash
# 运行单元测试（不需要数据库）
pytest tests/unit/ -v

# 如果单元测试通过，再运行组件测试
pytest tests/component/ -v

# 最后运行集成测试
pytest tests/integration/ -v

# 或者一次运行所有测试
pytest tests/ -v
```

### 6. 如果仍然遇到导入错误

创建一个 `pytest.ini` 文件：

```ini
[pytest]
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
```
