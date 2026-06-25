import logging
import sys
import threading
import builtins
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "ruptura_temporal_qa"
_LOG_FILE_NAME = "erros_qa.log"
_logger = None
_installed = False
_prints_filtrados = False
_print_original = builtins.print
_TERMOS_ERRO = (
    "erro",
    "error",
    "exception",
    "excecao",
    "exceção",
    "traceback",
    "falha",
    "failed",
    "crash",
)


def _obter_pasta_logs():
    try:
        docs = Path.home() / "Documents"
        if not docs.exists():
            docs = Path.home() / "Documentos"
        base = docs if docs.exists() else Path.cwd()
        pasta = base / "Ruptura_Temporal_QA_Logs"
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta
    except Exception:
        pasta = Path.cwd() / "logs"
        pasta.mkdir(parents=True, exist_ok=True)
        return pasta


def caminho_log():
    return str(_obter_pasta_logs() / _LOG_FILE_NAME)


def obter_logger():
    global _logger
    if _logger is not None:
        return _logger

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.ERROR)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            caminho_log(),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setLevel(logging.ERROR)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        ))
        logger.addHandler(handler)

    _logger = logger
    return logger


def registrar_erro(contexto, erro=None, exc_info=None):
    logger = obter_logger()
    if exc_info is None and erro is not None:
        exc_info = (type(erro), erro, getattr(erro, "__traceback__", None))
    if exc_info:
        logger.error(contexto, exc_info=exc_info)
    else:
        logger.error(contexto)


def instalar_captura_global():
    global _installed
    if _installed:
        return
    _installed = True

    def excepthook(exc_type, exc_value, exc_traceback):
        registrar_erro("Excecao nao tratada", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = excepthook

    if hasattr(threading, "excepthook"):
        def threading_excepthook(args):
            registrar_erro(
                f"Excecao nao tratada em thread: {getattr(args.thread, 'name', 'desconhecida')}",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )

        threading.excepthook = threading_excepthook


def instalar_filtro_prints():
    global _prints_filtrados
    if _prints_filtrados:
        return
    _prints_filtrados = True

    def print_filtrado(*args, **kwargs):
        _print_original(*args, **kwargs)
        texto = " ".join(str(arg) for arg in args)
        if any(termo in texto.lower() for termo in _TERMOS_ERRO):
            registrar_erro(f"print filtrado: {texto}")

    builtins.print = print_filtrado
