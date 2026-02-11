#!/usr/bin/env bash
# =============================================================================
# setup.sh - 开发环境一站式配置（一次性安装脚本）
# =============================================================================
#
# 用法:
#   bash setup.sh    → 安装工具 + 将配置直接写入 ~/.zshrc 和 ~/.bashrc
#
# 特性:
#   - 一次性：运行后所有配置写入 rc 文件，项目可安全删除
#   - 幂等：用标记块包裹，重复运行会替换旧配置
#   - 增量：已安装的工具自动跳过
#
# =============================================================================

set -uo pipefail

SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---- 颜色输出 ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
GRAY='\033[0;90m'
NC='\033[0m'

info()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }
skip()  { echo -e "${GRAY}[·]${NC} $*"; }
step()  { echo -e "\n${BLUE}==>${NC} $*"; }

# ---- 配置变量（按需修改）----
DEV_CACHE_BASE="/pyg-vepfs/public/lyh/tmp"

SECRETS_FILE="${SETUP_DIR}/secrets.sh"
STARSHIP_SRC="${SETUP_DIR}/starship.toml"
STARSHIP_DST="${HOME}/.config/starship.toml"

MARKER_START="# [dev-settings] START — 由 setup.sh 生成，请勿手动编辑此块"
MARKER_END="# [dev-settings] END"

CHANGES=0

echo ""
echo "========================================================"
echo "       开发环境一站式配置（一次性安装模式）"
echo "========================================================"

# =============================================================================
# Step 1: 安装 Starship
# =============================================================================
step "检查 Starship 提示符..."
if command -v starship &>/dev/null; then
    skip "Starship 已安装 ($(starship --version 2>/dev/null | head -1))，跳过"
else
    warn "Starship 未安装，正在安装..."
    if curl -sS https://starship.rs/install.sh | sh -s -- -y; then
        info "Starship 安装成功"
        CHANGES=$((CHANGES + 1))
    else
        error "Starship 安装失败，请手动安装: curl -sS https://starship.rs/install.sh | sh"
    fi
fi

# =============================================================================
# Step 2: 部署 Starship 配置（复制，非符号链接）
# =============================================================================
step "部署 Starship 配置..."
if [ ! -f "${STARSHIP_SRC}" ]; then
    warn "未找到 starship.toml 源文件，跳过"
else
    mkdir -p "$(dirname "${STARSHIP_DST}")"
    if [ -f "${STARSHIP_DST}" ] && diff -q "${STARSHIP_SRC}" "${STARSHIP_DST}" &>/dev/null; then
        skip "starship.toml 已是最新，跳过"
    else
        # 备份已有配置
        if [ -f "${STARSHIP_DST}" ]; then
            BACKUP="${STARSHIP_DST}.bak.$(date +%Y%m%d%H%M%S)"
            cp "${STARSHIP_DST}" "${BACKUP}"
            warn "已备份原有配置到 ${BACKUP}"
        fi
        cp "${STARSHIP_SRC}" "${STARSHIP_DST}"
        info "已复制 starship.toml → ${STARSHIP_DST}"
        CHANGES=$((CHANGES + 1))
    fi
fi

# =============================================================================
# Step 3: 读取 secrets（如果有的话，内联写入 rc）
# =============================================================================
SECRETS_BLOCK=""
if [ -f "${SECRETS_FILE}" ]; then
    # 提取 secrets.sh 中实际的 export 行（去掉注释和空行）
    SECRETS_BLOCK=$(grep -E '^\s*export\s+' "${SECRETS_FILE}" 2>/dev/null || true)
fi

# =============================================================================
# Step 4: 生成配置块内容
# =============================================================================
# 生成要写入 rc 文件的配置块
_generate_config_block() {
    local shell_type="$1"  # "zsh" 或 "bash"

    cat << 'BLOCK_EOF'
# [dev-settings] START — 由 setup.sh 生成，请勿手动编辑此块

# --- 缓存基础路径 ---
DEV_CACHE_BASE="/pyg-vepfs/public/lyh/tmp"

# --- 临时目录 ---
export TMPDIR="${DEV_CACHE_BASE}"
export TEMP="${TMPDIR}"
export TMP="${TMPDIR}"

# --- Python 工具链 ---
export UV_CACHE_DIR="${DEV_CACHE_BASE}/uv_cache"
export PIXI_CACHE_DIR="${DEV_CACHE_BASE}/pixi_cache"

# --- AI / ML ---
export HF_HOME="${DEV_CACHE_BASE}/huggingface"
export TORCH_HOME="${DEV_CACHE_BASE}/torch/hub/checkpoints"

# --- 编辑器 / IDE ---
export VSCODE_AGENT_FOLDER="${DEV_CACHE_BASE}/.vscode-server"

# --- NVM ---
export NVM_DIR="$HOME/.nvm"
[ -s "${NVM_DIR}/nvm.sh" ] && \. "${NVM_DIR}/nvm.sh"
[ -s "${NVM_DIR}/bash_completion" ] && \. "${NVM_DIR}/bash_completion"

# --- pnpm ---
export PNPM_HOME="$HOME/.local/share/pnpm"
case ":${PATH}:" in
    *":${PNPM_HOME}:"*) ;;
    *) export PATH="${PNPM_HOME}:${PATH}" ;;
esac

# --- pixi ---
case ":${PATH}:" in
    *":$HOME/.pixi/bin:"*) ;;
    *) export PATH="$HOME/.pixi/bin:${PATH}" ;;
esac

# --- uv/uvx ---
[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"

# --- opencode ---
[ -d "$HOME/.opencode/bin" ] && case ":${PATH}:" in
    *":$HOME/.opencode/bin:"*) ;;
    *) export PATH="$HOME/.opencode/bin:${PATH}" ;;
esac

# --- 系统 Locale ---
export LANG="C.utf8"
export LC_ALL="C.utf8"

BLOCK_EOF

    # 写入 secrets（如果有）
    if [ -n "${SECRETS_BLOCK}" ]; then
        echo "# --- API Keys ---"
        echo "${SECRETS_BLOCK}"
        echo ""
    fi

    # Starship 初始化（根据 shell 类型）
    if [ "${shell_type}" = "zsh" ]; then
        echo '# --- Starship 提示符 ---'
        echo 'command -v starship &>/dev/null && eval "$(starship init zsh)"'
    else
        echo '# --- Starship 提示符 ---'
        echo 'command -v starship &>/dev/null && eval "$(starship init bash)"'
    fi

    echo ""
    echo "${MARKER_END}"
}

# =============================================================================
# Step 5: 将配置块写入 rc 文件
# =============================================================================
_write_config_to_rc() {
    local rc_file="$1" rc_name="$2" shell_type="$3"

    step "配置 ${rc_name}..."

    if [ ! -f "${rc_file}" ]; then
        warn "${rc_name} 不存在，跳过"
        return
    fi

    # 生成新的配置块
    local new_block
    new_block=$(_generate_config_block "${shell_type}")

    # 如果已有旧的标记块，删除它
    if grep -qF "[dev-settings] START" "${rc_file}" 2>/dev/null; then
        # 用 sed 删除旧块（从 START 到 END）
        sed -i '/\[dev-settings\] START/,/\[dev-settings\] END/d' "${rc_file}"
        info "已移除旧的 dev-settings 配置块"
    fi

    # 同时清理旧的 source setup.sh 行
    if grep -qF 'source "/pyg-vepfs/public/lyh/dev-settings/setup.sh"' "${rc_file}" 2>/dev/null; then
        sed -i '\|source "/pyg-vepfs/public/lyh/dev-settings/setup.sh"|d' "${rc_file}"
        # 也清理对应的注释行
        sed -i '/# \[dev-settings\] 开发环境配置/d' "${rc_file}"
        info "已移除旧的 source setup.sh 引用"
    fi

    # 追加新配置块到末尾
    echo "" >> "${rc_file}"
    echo "${new_block}" >> "${rc_file}"
    info "已将配置直接写入 ${rc_name}"
    (( CHANGES++ ))
}

_write_config_to_rc "${HOME}/.zshrc"  "~/.zshrc"  "zsh"
_write_config_to_rc "${HOME}/.bashrc" "~/.bashrc" "bash"

# =============================================================================
# Step 6: 创建缓存目录
# =============================================================================
step "创建缓存目录..."
_check_dir() {
    local name="$1" dir="$2"
    if [ -d "${dir}" ]; then
        skip "$(printf '%-22s' "${name}") ${dir}"
    else
        mkdir -p "${dir}" 2>/dev/null
        info "$(printf '%-22s' "${name}") ${dir} (已创建)"
        CHANGES=$((CHANGES + 1))
    fi
}
_check_dir "TMPDIR"              "${DEV_CACHE_BASE}"
_check_dir "UV_CACHE_DIR"        "${DEV_CACHE_BASE}/uv_cache"
_check_dir "PIXI_CACHE_DIR"      "${DEV_CACHE_BASE}/pixi_cache"
_check_dir "HF_HOME"             "${DEV_CACHE_BASE}/huggingface"
_check_dir "TORCH_HOME"          "${DEV_CACHE_BASE}/torch/hub/checkpoints"
_check_dir "VSCODE_AGENT_FOLDER" "${DEV_CACHE_BASE}/.vscode-server"

# =============================================================================
# 完成汇总
# =============================================================================
echo ""
echo "========================================================"
if [ "${CHANGES}" -eq 0 ]; then
    info "环境已是最新，无需变更"
else
    info "配置完成，共执行 ${CHANGES} 项变更"
fi
echo "========================================================"
echo ""
echo "  所有配置已直接写入 rc 文件（非 source 引用）。"
echo "  本项目可安全删除，不影响终端配置。"
echo ""
echo "  打开新终端即可生效，或手动执行:"
echo "    source ~/.zshrc   (zsh)"
echo "    source ~/.bashrc  (bash)"
echo ""
