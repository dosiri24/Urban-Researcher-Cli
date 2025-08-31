import sys
import logging
from pathlib import Path

import click

from urban_cli.version import __version__
from urban_cli.logutil import setup_logging
from urban_cli.config import ConfigManager
from urban_cli.project import ProjectManager
from urban_cli.chat import run_chat_repl


class FriendlyException(click.ClickException):
    pass


@click.group(context_settings={"help_option_names": ["-h", "--help"]}, invoke_without_command=True)
@click.option("--verbose", "verbose", is_flag=True, help="Enable verbose logging (DEBUG)")
@click.version_option(version=__version__, prog_name="Urban Researcher CLI")
@click.pass_context
def cli(ctx: click.Context, verbose: bool):
    """Urban Researcher: AI 기반 연구 자동화 CLI."""
    setup_logging(debug=verbose)
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    _maybe_prompt_gemini_key()

    # 기본 동작: 서브커맨드가 없고 TTY인 경우 chat REPL로 진입
    try:
        import sys as _sys
        if ctx.invoked_subcommand is None and _sys.stdin.isatty() and _sys.stdout.isatty():
            # 도움말/버전 요청은 Click이 자체 처리하므로 여기선 REPL 진입
            ctx.invoke(chat, system=None, temperature=0.7, project_root=None)
            # chat 종료 후 즉시 반환
            raise click.exceptions.Exit(0)
    except Exception:
        # 문제 시에는 기본 도움말로 폴백 (조용히 무시)
        pass


def _maybe_prompt_gemini_key() -> None:
    """프로그램 시작 시 Gemini API 키가 없으면 한 번 입력받아 저장.

    - 우선순위: ENV(UR_GEMINI_API_KEY/GOOGLE_API_KEY) 또는 config(gemini-api-key/google-api-key)
    - 도움말/버전 조회 시에는 프롬프트 생략
    - TTY가 아닐 경우 생략
    """
    import os
    import sys as _sys
    from urban_cli.config import ConfigManager

    # 도움말/버전만 보는 경우 스킵
    argv = set(_sys.argv[1:])
    if {"--help", "-h", "--version"} & argv:
        return
    # 비대화형 스킵
    try:
        if not _sys.stdin.isatty() or not _sys.stdout.isatty():
            return
    except Exception:
        return

    # 이미 설정되어 있으면 스킵
    for env in ("UR_GEMINI_API_KEY", "GOOGLE_API_KEY"):
        if os.environ.get(env, "").strip():
            return
    cm = ConfigManager()
    for key in ("gemini-api-key", "google-api-key"):
        v = cm.get(key)
        if v and str(v).strip():
            return

    # 입력 받기
    try:
        api_key = click.prompt(
            "Gemini API 키가 설정되어 있지 않습니다. 입력해 주세요 (엔터로 건너뜀)",
            hide_input=True,
            default="",
            show_default=False,
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return

    if api_key:
        # 우선 세션(ENV)에만 적용. 첫 정상 응답 시 자동 영구 저장.
        os.environ["UR_GEMINI_API_KEY"] = api_key
        click.echo("Gemini API 키가 세션에 적용되었습니다. 첫 정상 응답 후 자동 저장됩니다.")


# -----------------
# Config commands
# -----------------


@cli.group()
@click.pass_context
def config(ctx: click.Context):
    """설정 관리 (API 키 등)."""
    pass


@config.command("set")
@click.option("--key", "key", required=True, help="설정 키 이름 (예: api-key)")
@click.option("--value", "value", required=True, help="설정 값")
def config_set(key: str, value: str):
    """설정 값을 저장합니다."""
    try:
        if not key or not key.strip():
            raise FriendlyException("키가 비어 있습니다.")
        if value is None or not str(value).strip():
            raise FriendlyException("값이 비어 있습니다.")
        cm = ConfigManager()
        cm.set(key, value)
        click.echo(f"Saved: {key}")
    except Exception as e:
        raise FriendlyException(f"설정 저장 중 오류: {e}")


@config.command("get")
@click.option("--key", "key", required=True, help="설정 키 이름 (예: api-key)")
@click.option("--raw", is_flag=True, help="마스킹 없이 원문 출력")
def config_get(key: str, raw: bool):
    """설정 값을 조회합니다."""
    try:
        cm = ConfigManager()
        value = cm.get(key)
        if value is None:
            raise FriendlyException(f"키가 존재하지 않습니다: {key}")
        if raw:
            click.echo(value)
        else:
            click.echo(cm.mask(value))
    except FriendlyException:
        raise
    except Exception as e:
        raise FriendlyException(f"설정 조회 중 오류: {e}")


@config.command("list")
def config_list():
    """저장된 모든 설정 키를 나열합니다 (값은 마스킹)."""
    try:
        cm = ConfigManager()
        data = cm.all()
        if not data:
            click.echo("No config set yet.")
            return
        width = max(len(k) for k in data.keys())
        for k, v in sorted(data.items()):
            click.echo(f"{k.ljust(width)}  =  {cm.mask(str(v))}")
    except Exception as e:
        raise FriendlyException(f"설정 나열 중 오류: {e}")


# -----------------
# Project commands
# -----------------


@cli.command()
@click.argument("name")
@click.option("--dir", "directory", type=click.Path(path_type=Path), default=Path.cwd(), help="프로젝트를 생성할 경로")
@click.option("--force", is_flag=True, help="이미 존재해도 진행")
def init(name: str, directory: Path, force: bool):
    """새 프로젝트를 초기화합니다."""
    try:
        pm = ProjectManager(base_dir=directory)
        path = pm.create(name=name, force=force)
        click.echo(f"Created project at: {path}")
        click.echo("Standard layout: data/, outputs/, logs/, notes/")
    except FriendlyException:
        raise
    except Exception as e:
        raise FriendlyException(f"프로젝트 생성 중 오류: {e}")


# -----------------
# Run placeholder
# -----------------


@cli.command()
@click.option("--auto", is_flag=True, help="자동 루프 실행(향후 구현)")
def run(auto: bool):
    """연구 파이프라인 실행 (향후 확장)."""
    if auto:
        click.echo("'run --auto'는 추후 Phase 7에서 구현됩니다.")
    else:
        click.echo("'run'은 향후 연구 파이프라인 실행용 커맨드입니다.")


# -----------------
# Chat (Gemini)
# -----------------


@cli.command()
@click.option("--system", default=None, help="시스템 프롬프트(미지정 시 기본값)")
@click.option("--temperature", default=0.7, show_default=True, type=float, help="창의성 조절")
@click.option("--project-root", type=click.Path(path_type=Path), default=None, help="로그 저장용 프로젝트 루트")
def chat(system: str | None, temperature: float, project_root: Path | None):
    """제미나이 기반 대화형 REPL."""
    if system is None:
        system = (
            "너는 도시 연구를 지원하는 AI 조교야. 사용자의 자연어 요청을 명확히 이해하고, "
            "필요시 다음 액션을 제안하거나 후속 질문을 통해 문제를 구체화해. 답변은 간결하고 실행 가능하게 작성해."
        )
    # 모델은 고정: gemini-2.5-pro
    run_chat_repl(model="gemini-2.5-pro", system=system, temperature=temperature, project_root=project_root)


# -----------------
# Project group
# -----------------


@cli.group()
def project():
    """프로젝트 관련 유틸리티."""
    pass


@project.command("status")
@click.option("--dir", "directory", type=click.Path(path_type=Path), default=Path.cwd(), help="프로젝트 루트 경로")
def project_status(directory: Path):
    """프로젝트 상태를 점검합니다."""
    try:
        pm = ProjectManager(base_dir=directory)
        st = pm.status(directory)
        if not st["meta"]:
            raise FriendlyException("project.json을 찾을 수 없습니다. 프로젝트 루트에서 실행했는지 확인하세요.")
        click.echo(f"Project: {st['meta'].get('name')} ({st['meta'].get('id')})")
        click.echo(f"Root:    {st['root']}")
        for d, ok in st["dirs"].items():
            mark = "OK" if ok else "MISSING"
            click.echo(f" - {d.ljust(8)}: {mark}")
        if st["missing"]:
            missing = ", ".join(st["missing"])
            raise FriendlyException(f"누락된 디렉터리: {missing}")
    except FriendlyException:
        raise
    except Exception as e:
        raise FriendlyException(f"프로젝트 상태 점검 중 오류: {e}")


def main():
    try:
        cli(prog_name="urban-cli")
    except FriendlyException as e:
        # ClickException은 이미 예쁘게 출력되므로 그대로 전달
        raise click.ClickException(str(e))
    except Exception as e:
        logging.getLogger(__name__).exception("Unhandled error")
        raise click.ClickException(f"예상치 못한 오류가 발생했습니다: {e}")


if __name__ == "__main__":
    main()
