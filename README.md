# dev-settings

Linux 远程开发环境一键配置工具。运行一次 `setup.sh`，即可完成终端美化、环境变量、缓存路径等全部配置。**配置直接写入 shell rc 文件，运行后本项目可安全删除。**

## 功能概览

| 功能 | 说明 |
|------|------|
| Starship 提示符 | 自动安装 + 部署配置，显示 Git 状态、语言版本等 |
| 环境变量 | TMPDIR、HF_HOME、TORCH_HOME 等统一指向大容量磁盘 |
| 缓存目录 | 自动创建 uv / pixi / HuggingFace / PyTorch 缓存目录 |
| PATH 管理 | NVM、pnpm、pixi、uv、opencode 等工具路径去重追加 |
| Locale | 统一设置 `C.utf8`，避免编码问题 |
| API Keys | 从 `secrets.sh` 读取并内联写入 rc（不留外部依赖） |

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url> ~/dev-settings
cd ~/dev-settings

# 2. （可选）配置 API Keys
cp secrets.sh.example secrets.sh
chmod 600 secrets.sh
vim secrets.sh  # 填入你的 API Key

# 3. 一键安装
bash setup.sh

# 4. 开一个新终端，或手动生效
source ~/.zshrc   # zsh
source ~/.bashrc  # bash
```

安装完成后，项目目录可以安全删除，不影响终端配置。

## 前置依赖

以下工具需要在运行 `setup.sh` **之前**手动安装：

| 工具 | 用途 | 安装方式 |
|------|------|---------|
| zsh | Shell | `apt install zsh && chsh -s $(which zsh)` |
| Oh My Zsh | zsh 插件框架 | `sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"` |
| zsh-autosuggestions | 历史命令自动建议 | `git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM}/plugins/zsh-autosuggestions` |
| zsh-syntax-highlighting | 命令语法高亮 | `git clone https://github.com/zsh-users/zsh-syntax-highlighting ${ZSH_CUSTOM}/plugins/zsh-syntax-highlighting` |
| Nerd Font | Starship 图标字体 | 下载 [0xProto Nerd Font](https://github.com/ryanoasis/nerd-fonts/releases) 并安装到 `~/.local/share/fonts/` |

> `setup.sh` 会自动安装 **Starship**，无需手动处理。

## 项目结构

```
dev-settings/
├── README.md              # 本文件
├── setup.sh               # 一键安装脚本（核心）
├── starship.toml          # Starship 提示符配置
├── secrets.sh.example     # API Key 模板
├── secrets.sh             # 实际 API Key（已 gitignore）
└── .gitignore
```

## setup.sh 做了什么

脚本执行以下步骤：

1. **安装 Starship** — 检测是否已安装，未安装则自动安装
2. **部署 starship.toml** — 复制到 `~/.config/starship.toml`（非符号链接）
3. **读取 secrets.sh** — 提取 `export` 行，准备内联写入
4. **写入 ~/.zshrc 和 ~/.bashrc** — 在文件末尾追加配置块（用标记包裹）
5. **创建缓存目录** — 确保所有缓存路径存在

### 写入 rc 文件的配置块

脚本会在 `~/.zshrc`（和 `~/.bashrc`）末尾写入一个标记块：

```bash
# [dev-settings] START — 由 setup.sh 生成，请勿手动编辑此块
DEV_CACHE_BASE="/pyg-vepfs/public/lyh/tmp"
export TMPDIR="${DEV_CACHE_BASE}"
export UV_CACHE_DIR="${DEV_CACHE_BASE}/uv_cache"
# ... 其他环境变量、PATH、Starship init ...
# [dev-settings] END
```

- 重复运行 `setup.sh` 会**替换**旧的配置块（幂等）
- 标记块外的内容（Oh My Zsh 插件、conda、clashctl 等）不受影响

## 配置详情

### 缓存路径映射

所有缓存统一指向大容量磁盘，避免系统盘空间不足：

| 环境变量 | 路径 | 用途 |
|----------|------|------|
| `TMPDIR` / `TEMP` / `TMP` | `/pyg-vepfs/public/lyh/tmp` | 临时文件 |
| `UV_CACHE_DIR` | `.../tmp/uv_cache` | uv 包缓存 |
| `PIXI_CACHE_DIR` | `.../tmp/pixi_cache` | pixi 包缓存 |
| `HF_HOME` | `.../tmp/huggingface` | HuggingFace 模型缓存 |
| `TORCH_HOME` | `.../tmp/torch/hub/checkpoints` | PyTorch 预训练模型 |
| `VSCODE_AGENT_FOLDER` | `.../tmp/.vscode-server` | VS Code Remote Server |

### Starship 提示符

配置文件：`starship.toml`（安装后位于 `~/.config/starship.toml`）

显示的模块：

| 模块 | 图标 | 说明 |
|------|------|------|
| directory | — | 当前目录（截断显示最近 5 级） |
| git_branch |  | Git 分支名 |
| git_status | — | 修改、暂存、未跟踪等状态 |
| python |  | Python 版本 + 虚拟环境名 |
| nodejs |  | Node.js 版本 |
| rust |  | Rust 版本 |
| golang |  | Go 版本 |
| docker_context |  | Docker 上下文 |
| cmd_duration |  | 命令耗时（>3 秒才显示） |

提示符样式：`❯`（成功绿色）/ `✗`（失败红色）

### Secrets 管理

```bash
# 从模板创建
cp secrets.sh.example secrets.sh
chmod 600 secrets.sh
```

支持的 Key（按需填写）：

- `ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN`
- `GEMINI_API_KEY`
- `HF_TOKEN`
- `OPENAI_API_KEY`

> `secrets.sh` 已在 `.gitignore` 中，不会被提交到版本控制。
> 运行 `setup.sh` 后，Key 会内联写入 rc 文件，`secrets.sh` 也可删除。

## 自定义

如需修改缓存路径，编辑 `setup.sh` 中的变量后重新运行：

```bash
# setup.sh 第 35 行
DEV_CACHE_BASE="/your/custom/path"
```

如需修改 Starship 样式，编辑 `starship.toml` 后重新运行 `setup.sh`，或直接编辑 `~/.config/starship.toml`。

## 常见问题

**Q: 图标显示为方块/乱码？**
A: 终端需要使用 Nerd Font。在终端设置中将字体改为 `0xProto Nerd Font Mono` 或其他 Nerd Font。

**Q: 重复运行 setup.sh 会怎样？**
A: 安全。脚本会替换旧的配置块，已安装的工具会跳过，不会产生重复配置。

**Q: 运行后可以删除项目吗？**
A: 可以。所有配置已直接写入 rc 文件，不依赖项目目录中的任何文件。

**Q: 如何撤销所有配置？**
A: 删除 `~/.zshrc`（或 `~/.bashrc`）中 `[dev-settings] START` 到 `[dev-settings] END` 之间的内容即可。
