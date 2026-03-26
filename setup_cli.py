#!/usr/bin/env python3
"""开发环境一站式交互式配置工具 — 替代 setup.sh，提供 Clack 风格的交互式 CLI"""

import asyncio
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from pyclack.core import Spinner, Option, ConfirmPrompt, is_cancel
from pyclack.prompts import intro, outro, text, multiselect, note
from pyclack.utils.styling import (
    Color,
    symbol,
    S_BAR,
    S_BAR_END,
    S_RADIO_ACTIVE,
    S_RADIO_INACTIVE,
)


async def confirm(
    message: str, active: str = "Yes", inactive: str = "No", initial_value: bool = True,
):
    """confirm() wrapper — fixes upstream bug where bool is printed instead of label."""

    def render(prompt: ConfirmPrompt) -> str:
        title = f"{Color.gray(S_BAR)}\n{symbol(prompt.state)} {message}\n"
        value_label = active if prompt.value else inactive
        if prompt.state == "submit":
            return title
        if prompt.state == "cancel":
            return (
                f"{title}{Color.gray(S_BAR)} "
                f"{Color.strikethrough(Color.dim(value_label))}\n"
                f"{Color.gray(S_BAR)}"
            )
        active_style = (
            f"{Color.green(S_RADIO_ACTIVE)} {active}"
            if prompt.value
            else f"{Color.dim(S_RADIO_INACTIVE)} {Color.dim(active)}"
        )
        inactive_style = (
            f"{Color.green(S_RADIO_ACTIVE)} {inactive}"
            if not prompt.value
            else f"{Color.dim(S_RADIO_INACTIVE)} {Color.dim(inactive)}"
        )
        return (
            f"{title}{Color.cyan(S_BAR)} "
            f"{active_style} {Color.dim('/')} {inactive_style}\n"
            f"{Color.cyan(S_BAR_END)}\n"
        )

    prompt = ConfirmPrompt(
        render=render, active=active, inactive=inactive, initial_value=initial_value,
    )
    result = await prompt.prompt()
    if is_cancel(result):
        return result
    label = active if result else inactive
    print(f"{Color.gray(S_BAR)} {Color.dim(label)}")
    return result

SCRIPT_DIR = Path(__file__).parent.resolve()

DEFAULTS = {
    "cache_base": "/pyg-vepfs/public/lyh/tmp",
    "secrets_file": str(SCRIPT_DIR / "secrets.sh"),
    "starship_src": str(SCRIPT_DIR / "starship.toml"),
    "starship_dst": str(Path.home() / ".config" / "starship.toml"),
}

MARKER_START = "# [dev-settings] START — 由 setup.sh 生成，请勿手动编辑此块"
MARKER_END = "# [dev-settings] END"

CACHE_DIR_DEFS = {
    "tmpdir": ("TMPDIR", ""),
    "uv": ("UV_CACHE_DIR", "uv_cache"),
    "pixi": ("PIXI_CACHE_DIR", "pixi_cache"),
    "hf": ("HF_HOME", "huggingface"),
    "torch": ("TORCH_HOME", "torch/hub/checkpoints"),
    "vscode": ("VSCODE_AGENT_FOLDER", ".vscode-server"),
}


def log_step(icon: str, msg: str):
    print(f"{Color.gray(S_BAR)}  {icon} {msg}")


def log_info(msg: str):
    log_step(Color.green("✓"), msg)


def log_warn(msg: str):
    log_step(Color.yellow("!"), msg)


def log_skip(msg: str):
    log_step(Color.dim("·"), Color.dim(msg))


# ---------------------------------------------------------------------------
# 执行操作
# ---------------------------------------------------------------------------

def do_install_starship() -> tuple[bool, bool, str]:
    """Returns (success, changed, message)."""
    if shutil.which("starship"):
        ver = subprocess.run(
            ["starship", "--version"], capture_output=True, text=True
        ).stdout.strip().split("\n")[0]
        return True, False, f"已安装 ({ver})，跳过"

    ret = subprocess.run(
        ["sh", "-c", "curl -sS https://starship.rs/install.sh | sh -s -- -y"],
        capture_output=True,
        text=True,
    )
    if ret.returncode == 0:
        return True, True, "安装成功"
    return False, False, f"安装失败: {ret.stderr.strip()}"


def do_deploy_starship_config(src: str, dst: str) -> tuple[bool, bool, str]:
    """Returns (success, changed, message)."""
    src_path, dst_path = Path(src), Path(dst)

    if not src_path.exists():
        return False, False, f"源文件 {src} 不存在"

    dst_path.parent.mkdir(parents=True, exist_ok=True)

    if dst_path.exists():
        if src_path.read_text() == dst_path.read_text():
            return True, False, "配置已是最新，跳过"
        backup = f"{dst}.bak.{datetime.now():%Y%m%d%H%M%S}"
        shutil.copy2(dst_path, backup)

    shutil.copy2(src_path, dst_path)
    return True, True, f"已部署 → {dst}"


def read_secrets(path_str: str) -> str:
    p = Path(path_str)
    if not p.exists():
        return ""
    return "\n".join(
        line for line in p.read_text().splitlines() if re.match(r"^\s*export\s+", line)
    )


def generate_config_block(cache_base: str, shell_type: str, secrets_block: str) -> str:
    init_shell = "zsh" if shell_type == "zsh" else "bash"
    block = f"""\
{MARKER_START}

# --- 缓存基础路径 ---
DEV_CACHE_BASE="{cache_base}"

# --- 临时目录 ---
export TMPDIR="${{DEV_CACHE_BASE}}"
export TEMP="${{TMPDIR}}"
export TMP="${{TMPDIR}}"

# --- Python 工具链 ---
export UV_CACHE_DIR="${{DEV_CACHE_BASE}}/uv_cache"
export PIXI_CACHE_DIR="${{DEV_CACHE_BASE}}/pixi_cache"

# --- AI / ML ---
export HF_HOME="${{DEV_CACHE_BASE}}/huggingface"
export TORCH_HOME="${{DEV_CACHE_BASE}}/torch/hub/checkpoints"

# --- 编辑器 / IDE ---
export VSCODE_AGENT_FOLDER="${{DEV_CACHE_BASE}}/.vscode-server"

# --- NVM ---
export NVM_DIR="$HOME/.nvm"
[ -s "${{NVM_DIR}}/nvm.sh" ] && \\. "${{NVM_DIR}}/nvm.sh"
[ -s "${{NVM_DIR}}/bash_completion" ] && \\. "${{NVM_DIR}}/bash_completion"

# --- pnpm ---
export PNPM_HOME="$HOME/.local/share/pnpm"
case ":${{PATH}}:" in
    *":${{PNPM_HOME}}:"*) ;;
    *) export PATH="${{PNPM_HOME}}:${{PATH}}" ;;
esac

# --- pixi ---
case ":${{PATH}}:" in
    *":$HOME/.pixi/bin:"*) ;;
    *) export PATH="$HOME/.pixi/bin:${{PATH}}" ;;
esac

# --- uv/uvx ---
[ -f "$HOME/.local/bin/env" ] && . "$HOME/.local/bin/env"

# --- opencode ---
[ -d "$HOME/.opencode/bin" ] && case ":${{PATH}}:" in
    *":$HOME/.opencode/bin:"*) ;;
    *) export PATH="$HOME/.opencode/bin:${{PATH}}" ;;
esac

# --- 系统 Locale ---
export LANG="C.utf8"
export LC_ALL="C.utf8"
"""

    if secrets_block:
        block += f"\n# --- API Keys ---\n{secrets_block}\n"

    block += f"""
# --- Starship 提示符 ---
command -v starship &>/dev/null && eval "$(starship init {init_shell})"

{MARKER_END}"""
    return block


def write_config_to_rc(
    rc_file: str, shell_type: str, cache_base: str, secrets_block: str
) -> tuple[bool, bool, str]:
    """Returns (success, changed, message)."""
    rc_path = Path(rc_file)
    if not rc_path.exists():
        return False, False, f"{rc_file} 不存在，跳过"

    original = rc_path.read_text()
    content = original

    if "[dev-settings] START" in content:
        content = re.sub(
            r"# \[dev-settings\] START.*?# \[dev-settings\] END\n?",
            "",
            content,
            flags=re.DOTALL,
        )

    content = re.sub(
        r'source "/pyg-vepfs/public/lyh/dev-settings/setup\.sh"\n?', "", content
    )
    content = re.sub(r"# \[dev-settings\] 开发环境配置\n?", "", content)

    new_block = generate_config_block(cache_base, shell_type, secrets_block)
    content = content.rstrip() + "\n\n" + new_block + "\n"

    if content == original:
        return True, False, f"{rc_file} 已是最新，跳过"

    rc_path.write_text(content)
    return True, True, f"已写入 {rc_file}"


def create_cache_dirs(cache_base: str, dir_keys: list[str]) -> list[tuple[str, str, bool]]:
    results = []
    for key in dir_keys:
        if key not in CACHE_DIR_DEFS:
            continue
        name, suffix = CACHE_DIR_DEFS[key]
        path = cache_base if not suffix else f"{cache_base}/{suffix}"
        existed = Path(path).exists()
        Path(path).mkdir(parents=True, exist_ok=True)
        results.append((name, path, existed))
    return results


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def cancel_and_exit():
    outro(Color.red("已取消配置"))
    sys.exit(0)


async def main():
    intro("开发环境一站式配置")

    # ── 1. 缓存基础路径 ──
    cache_base = await text(
        message="缓存基础路径（所有缓存 / 临时目录的根）",
        placeholder=DEFAULTS["cache_base"],
        initial_value=DEFAULTS["cache_base"],
    )
    if is_cancel(cache_base):
        cancel_and_exit()

    # ── 2. Starship ──
    should_install = await confirm(
        message="安装 Starship 提示符？",
        active="是",
        inactive="否",
        initial_value=True,
    )
    if is_cancel(should_install):
        cancel_and_exit()

    should_deploy = False
    if should_install:
        should_deploy = await confirm(
            message="部署 Starship 配置文件 (starship.toml)？",
            active="是",
            inactive="否",
            initial_value=True,
        )
        if is_cancel(should_deploy):
            cancel_and_exit()

    # ── 3. Secrets ──
    secrets_file = await text(
        message="Secrets 文件路径（不存在则跳过）",
        placeholder=DEFAULTS["secrets_file"],
        initial_value=DEFAULTS["secrets_file"],
    )
    if is_cancel(secrets_file):
        cancel_and_exit()

    # ── 4. Shell 配置 ──
    shells = await multiselect(
        message="写入哪些 Shell 的 rc 文件？",
        options=[
            Option("zsh", "Zsh  (~/.zshrc)"),
            Option("bash", "Bash (~/.bashrc)"),
        ],
        initial_values=["zsh", "bash"],
        required=True,
    )
    if is_cancel(shells):
        cancel_and_exit()

    # ── 5. 缓存目录 ──
    all_dir_keys = list(CACHE_DIR_DEFS.keys())
    cache_options = [
        Option(
            key,
            f"{name:22s} ({cache_base}/{suffix})" if suffix else f"{name:22s} ({cache_base})",
        )
        for key, (name, suffix) in CACHE_DIR_DEFS.items()
    ]
    cache_dirs = await multiselect(
        message="创建哪些缓存目录？",
        options=cache_options,
        initial_values=all_dir_keys,
        required=False,
    )
    if is_cancel(cache_dirs):
        cancel_and_exit()

    # ── 执行 ──
    print(f"{Color.gray(S_BAR)}")
    changes = 0

    # Starship 安装
    if should_install:
        s = Spinner()
        s.start("检查 / 安装 Starship")
        ok, changed, msg = do_install_starship()
        s.stop(f"Starship — {msg}", code=0 if ok else 2)
        if changed:
            changes += 1

    # Starship 配置
    if should_deploy:
        s = Spinner()
        s.start("部署 Starship 配置")
        ok, changed, msg = do_deploy_starship_config(
            DEFAULTS["starship_src"], DEFAULTS["starship_dst"]
        )
        s.stop(f"Starship 配置 — {msg}", code=0 if ok else 2)
        if changed:
            changes += 1

    # Secrets
    secrets_block = read_secrets(secrets_file) if secrets_file else ""

    # Shell rc 文件
    shell_map = {
        "zsh": (str(Path.home() / ".zshrc"), "~/.zshrc"),
        "bash": (str(Path.home() / ".bashrc"), "~/.bashrc"),
    }
    for key in shells:
        rc_file, rc_name = shell_map[key]
        s = Spinner()
        s.start(f"配置 {rc_name}")
        ok, changed, msg = write_config_to_rc(rc_file, key, cache_base, secrets_block)
        s.stop(f"{rc_name} — {msg}", code=0 if ok else 1)
        if changed:
            changes += 1

    # 缓存目录
    if cache_dirs:
        s = Spinner()
        s.start("创建缓存目录")
        results = create_cache_dirs(cache_base, cache_dirs)
        s.stop("缓存目录处理完成")
        for name, path, existed in results:
            if existed:
                log_skip(f"{name:22s} {path}")
            else:
                log_info(f"{name:22s} {path} (已创建)")
                changes += 1

    # ── 完成 ──
    if changes == 0:
        outro("环境已是最新，无需变更 ✓")
    else:
        note(
            title="完成",
            message="\n".join([
                f"共执行 {changes} 项变更",
                "",
                "所有配置已直接写入 rc 文件（非 source 引用）",
                "本项目可安全删除，不影响终端配置",
                "",
                "打开新终端即可生效，或手动执行:",
                "  source ~/.zshrc   (zsh)",
                "  source ~/.bashrc  (bash)",
            ]),
        )
        outro(f"配置完成，共 {changes} 项变更 ✓")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Color.gray(S_BAR)}")
        outro(Color.red("已取消"))
