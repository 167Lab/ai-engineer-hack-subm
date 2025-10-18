from __future__ import annotations
import logging
import csv
from typing import Optional, Iterable
import pandas as pd

log = logging.getLogger("include.io")


def _try_read(
    path: str,
    *,
    engine: str = "python",
    sep=None,  # None => sniff
    encoding: Optional[str] = None,
    on_bad_lines: str = "warn",  # "error" | "warn" | "skip"
    extra_opts: Optional[dict] = None,
):
    opts = dict(
        engine=engine,
        sep=sep,
        encoding=encoding,
        on_bad_lines=on_bad_lines,
        skipinitialspace=True,
        dtype_backend="numpy_nullable",
    )
    if extra_opts:
        opts.update(extra_opts)
    return pd.read_csv(path, **opts), opts


def robust_read_csv(
    path: str,
    *,
    strict: bool = False,
    sample_for_sniff: int = 64_000,
    preferred_encodings: Iterable[str] = ("utf-8", "utf-8-sig", "cp1251", "latin-1"),
    extra_opts: Optional[dict] = None,
):
    """
    Надёжное чтение CSV:
      - Автоопределение разделителя/кавычек (engine='python', sep=None)
      - Перебор нескольких кодировок
      - Обработка "плохих" строк (warn/skip), чтобы DAG не падал
    """
    try:
        df, used = _try_read(
            path,
            sep=None,
            encoding=None,
            on_bad_lines=("error" if strict else "warn"),
            extra_opts=extra_opts,
        )
        log.info("CSV parsed with autodetect: %s", used)
        return df
    except Exception as e:
        log.warning("Autodetect UTF-8 failed: %s", e)

    # Попробуем определить разделитель на сэмпле
    try:
        with open(path, "rb") as f:
            sample = f.read(sample_for_sniff)
        dialect = csv.Sniffer().sniff(sample.decode("utf-8", "ignore"))
        sep = dialect.delimiter
        log.info("Sniffer chose delimiter=%r", sep)
    except Exception:
        sep = None

    last_err = None
    for enc in preferred_encodings:
        for bad in (("error" if strict else "warn"), ("error" if strict else "skip")):
            try:
                df, used = _try_read(
                    path,
                    sep=sep,
                    encoding=enc,
                    on_bad_lines=bad,
                    extra_opts=extra_opts,
                )
                log.info("CSV parsed with %s", used)
                return df
            except Exception as e:
                last_err = e
                log.warning("read_csv failed (enc=%s, on_bad_lines=%s): %s", enc, bad, e)

    log.error("All parsing attempts failed: %s", last_err)
    raise last_err


