from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Optional
import sys
import threading
import time

import click

from .config import ConfigManager
from .llm import LLMConfig
from .gemini_client import GeminiClient


DEFAULT_MODEL = "gemini-2.5-pro"
DEFAULT_SYSTEM = (
    "너는 도시 연구를 지원하는 AI 조교야. 사용자의 자연어 요청을 명확히 이해하고, "
    "필요시 다음 액션을 제안하거나 후속 질문을 통해 문제를 구체화해. 답변은 간결하고 실행 가능하게 작성해."
)


def _resolve_gemini_key(cm: ConfigManager):
    # 우선순위: ENV(UR_GEMINI_API_KEY, GOOGLE_API_KEY) → config(gemini-api-key, google-api-key)
    import os

    for env in ("UR_GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if env in os.environ and os.environ[env].strip():
            return os.environ[env].strip(), "env"
    for key in ("gemini-api-key", "google-api-key"):
        v = cm.get(key)
        if v and str(v).strip():
            return str(v).strip(), "config"
    return None, "none"


def _open_log(project_root: Optional[Path]) -> Path:
    root = Path(project_root) if project_root else Path.cwd()
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return logs / f"chat_{ts}.md"


def run_chat_repl(model: str = DEFAULT_MODEL, system: str = DEFAULT_SYSTEM, temperature: float = 0.7, project_root: Optional[Path] = None) -> None:
    cm = ConfigManager()
    api_key, source = _resolve_gemini_key(cm)
    if not api_key:
        raise click.ClickException(
            "Gemini API 키가 필요합니다. 다음 중 하나를 설정하세요:\n"
            " - 환경변수: UR_GEMINI_API_KEY 또는 GOOGLE_API_KEY\n"
            " - 설정파일: python cli.py config set --key gemini-api-key --value YOUR_KEY"
        )

    cfg = LLMConfig(model=model, temperature=float(temperature))
    client = GeminiClient(api_key=api_key, config=cfg, system_prompt=system)

    log_path = _open_log(project_root)
    click.echo(f"대화 로그 파일: {log_path}")
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"# Chat Session — {model}\n\n")
        log.write(f"System: {system}\n\n")

        click.echo("/exit 로 종료, /help 로 명령 보기")
        click.echo("/logout 으로 저장된 API 키 자동 사용 해제")

        # 성공 시 자동 저장 조건: 설정파일에 키가 없고, ENV에서 가져온 경우
        has_config_key = bool(cm.get("gemini-api-key") or cm.get("google-api-key"))
        persist_on_success = (source == "env") and (not has_config_key)
        while True:
            try:
                user = click.prompt(click.style("You", fg="cyan"), prompt_suffix=click.style(" > ", fg="cyan"))
            except (KeyboardInterrupt, EOFError):
                click.echo("\n세션 종료")
                break

            if not user.strip():
                continue
            if user.strip() in {"/exit", "/quit"}:
                click.echo("종료합니다.")
                break
            if user.strip() == "/help":
                click.echo("명령: /exit, /quit, /help, /logout")
                continue
            if user.strip() == "/logout":
                import os
                try:
                    removed = []
                    if cm.unset("gemini-api-key"):
                        removed.append("gemini-api-key")
                    if cm.unset("google-api-key"):
                        removed.append("google-api-key")
                except Exception:
                    removed = []
                for env in ("UR_GEMINI_API_KEY", "GOOGLE_API_KEY"):
                    if env in os.environ:
                        try:
                            del os.environ[env]
                        except Exception:
                            pass
                click.echo("API 키 자동 사용이 해제되었습니다. 세션을 종료합니다.")
                break

            log.write(f"## You\n{user}\n\n")
            try:
                # Spinner 표시
                stop = threading.Event()
                def _spin():
                    if not sys.stdout.isatty():
                        return
                    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
                    base = " 생각 중"
                    i = 0
                    last_len = 0
                    while not stop.is_set():
                        frame = frames[i % len(frames)]
                        dots = (i % 3) + 1  # 1,2,3 반복
                        text = frame + base + ("." * dots)
                        pad = " " * max(0, last_len - len(text))
                        sys.stdout.write("\r" + text + pad)
                        sys.stdout.flush()
                        last_len = len(text)
                        time.sleep(0.08)
                        i += 1
                    sys.stdout.write("\r" + " " * last_len + "\r")
                    sys.stdout.flush()

                t = threading.Thread(target=_spin, daemon=True)
                t.start()
                try:
                    reply = client.send(user)
                finally:
                    stop.set()
                    t.join(timeout=0.5)
            except Exception as e:
                raise click.ClickException(f"Gemini 호출 중 오류: {e}")

            log.write(f"## AI\n{reply}\n\n")
            click.echo(click.style("AI", fg="green") + click.style(" > ", fg="green") + reply)

            # 첫 성공 시 키 영구 저장
            if persist_on_success:
                try:
                    cm.set("gemini-api-key", api_key)
                    persist_on_success = False
                    click.echo(click.style("[info] API 키가 검증되어 저장되었습니다.", fg="yellow"))
                except Exception:
                    pass
